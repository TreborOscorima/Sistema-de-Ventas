#!/usr/bin/env bash
# =============================================================================
# scripts/deploy-prod.sh — Deploy Docker producción (stack 3 superficies tuwayki.app)
#
# Uso:
#   bash scripts/deploy-prod.sh                    # Deploy completo
#   bash scripts/deploy-prod.sh --skip-backup      # Sin backup de MySQL
#   bash scripts/deploy-prod.sh --skip-build       # Solo recreate (sin rebuild)
#   bash scripts/deploy-prod.sh --skip-npm         # Sin reiniciar NPM al final
#
# CI/CD: push a main/docker-deploy-prod dispara .github/workflows/deploy-prod.yml
#        (tras tests exitosos) o ejecución manual en GitHub Actions.
#
# Variables de entorno opcionales:
#   APP_DIR              Directorio del proyecto (default: padre de scripts/)
#   BRANCH               Rama a desplegar (default: docker-deploy-prod)
#   TUWAYKI_CORE_SHA     Commit fijo de tuwayki-core (sync con .github/workflows/tests.yml)
#   HEALTH_WAIT_MAX      Iteraciones de espera × 15s (default: 80 → 20 min)
#   BACKUP_KEEP          Backups .sql.gz a conservar (default: 5)
#
# Requisitos en el servidor:
#   - .env con DB_PASSWORD, MYSQL_ROOT_PASSWORD, REDIS_PASSWORD, AUTH_SECRET_KEY
#   - NO definir REDIS_URL ni DB_HOST=localhost (compose inyecta tuwayki_redis / tuwayki_mysql)
#   - Red externa nginx-proxy-manager_default (NPM)
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BRANCH="${BRANCH:-docker-deploy-prod}"
TUWAYKI_CORE_SHA="${TUWAYKI_CORE_SHA:-ef1c30e33ac9aed6c1a8507de2a31382dedd69ec}"
TUWAYKI_CORE_REPO="${TUWAYKI_CORE_REPO:-https://github.com/TreborOscorima/tuwayki-core.git}"
HEALTH_WAIT_MAX="${HEALTH_WAIT_MAX:-80}"
BACKUP_KEEP="${BACKUP_KEEP:-5}"
NPM_NETWORK="${NPM_NETWORK:-nginx-proxy-manager_default}"

SKIP_BACKUP=false
SKIP_BUILD=false
SKIP_NPM=false

for arg in "$@"; do
    case "$arg" in
        --skip-backup) SKIP_BACKUP=true ;;
        --skip-build)  SKIP_BUILD=true ;;
        --skip-npm)    SKIP_NPM=true ;;
        -h|--help)
            sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            fail "Argumento desconocido: $arg (usa --help)"
            ;;
    esac
done

cd "$APP_DIR"
info "Deploy Docker prod en: $APP_DIR"
info "Branch: $BRANCH | tuwayki-core: ${TUWAYKI_CORE_SHA:0:12}"

# ─── Prerrequisitos ───────────────────────────────────────────────────────────
command -v git    >/dev/null 2>&1 || fail "git no encontrado"
command -v docker >/dev/null 2>&1 || fail "docker no encontrado"
docker compose version >/dev/null 2>&1 || fail "docker compose no disponible"
[[ -f "$APP_DIR/.env" ]] || fail "No existe .env — copiar desde .env.example"
[[ -f "$APP_DIR/docker-compose.yml" ]] || fail "No existe docker-compose.yml"

# ─── Validar .env (evita fallos silenciosos en Redis/MySQL) ───────────────────
validate_env() {
    local env_file="$APP_DIR/.env"
    local missing=()

    for var in DB_PASSWORD MYSQL_ROOT_PASSWORD REDIS_PASSWORD AUTH_SECRET_KEY; do
        if ! grep -qE "^${var}=.+" "$env_file" 2>/dev/null; then
            missing+=("$var")
        fi
    done
    [[ ${#missing[@]} -eq 0 ]] || fail "Variables faltantes en .env: ${missing[*]}"

    if grep -qE '^REDIS_URL=.*localhost' "$env_file" 2>/dev/null; then
        fail "REDIS_URL apunta a localhost en .env — comentar esa línea (compose usa REDIS_HOST=tuwayki_redis)"
    fi
    if grep -qE '^DB_HOST=localhost' "$env_file" 2>/dev/null; then
        fail "DB_HOST=localhost en .env rompe Docker — comentar esa línea"
    fi
    local secret_len
    secret_len="$(grep -E '^AUTH_SECRET_KEY=' "$env_file" | cut -d= -f2- | tr -d '[:space:]' | wc -c)"
    [[ "$secret_len" -ge 32 ]] || fail "AUTH_SECRET_KEY debe tener mínimo 32 caracteres"
}
validate_env
ok "Validación .env OK"

# ─── Sync .env con .env.example (agrega variables nuevas, nunca pisa existentes)
sync_env_example() {
    local example="$APP_DIR/.env.example"
    local env_file="$APP_DIR/.env"
    [[ -f "$example" ]] || { warn ".env.example no encontrado — sync omitido"; return; }

    local added=0
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        local key="${line%%=*}"
        [[ -z "$key" ]] && continue
        if ! grep -qE "^${key}=" "$env_file" 2>/dev/null; then
            echo "$line" >> "$env_file"
            info "  + $key (agregado desde .env.example)"
            added=$((added + 1))
        fi
    done < "$example"

    if [[ $added -gt 0 ]]; then
        warn "$added variable(s) nueva(s) agregada(s) al .env desde .env.example — revisar valores sensibles"
    else
        ok "Sync .env ↔ .env.example: todo al día"
    fi
}
sync_env_example

# ─── Inyectar GitHub Secrets al .env (si las env vars llegan del workflow) ────
inject_secret() {
    local var_name="$1"
    local var_value="${2:-}"
    local env_file="$APP_DIR/.env"
    [[ -z "$var_value" ]] && return
    if grep -qE "^${var_name}=" "$env_file" 2>/dev/null; then
        local current
        current="$(grep -E "^${var_name}=" "$env_file" | cut -d= -f2-)"
        if [[ "$current" != "$var_value" ]]; then
            sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$env_file"
            info "  ↻ $var_name actualizado desde GitHub Secret"
        fi
    else
        echo "${var_name}=${var_value}" >> "$env_file"
        info "  + $var_name inyectado desde GitHub Secret"
    fi
}
inject_secret "OWNER_TOTP_SECRET" "${OWNER_TOTP_SECRET:-}"

# ─── Red NPM ──────────────────────────────────────────────────────────────────
if ! docker network inspect "$NPM_NETWORK" >/dev/null 2>&1; then
    warn "Red $NPM_NETWORK no existe — creando..."
    docker network create "$NPM_NETWORK"
fi

# ─── 1. Backup BD ─────────────────────────────────────────────────────────────
if $SKIP_BACKUP; then
    warn "Backup omitido (--skip-backup)"
else
    if docker inspect tuwayki_mysql >/dev/null 2>&1; then
        BACKUP_DIR="$APP_DIR/backups"
        mkdir -p "$BACKUP_DIR"
        BACKUP="$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz"
        info "Backup MySQL → $BACKUP"
        docker exec tuwayki_mysql sh -c \
            'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" --single-transaction --routines --triggers --no-tablespaces' \
            | gzip > "$BACKUP"
        [[ -s "$BACKUP" ]] || { rm -f "$BACKUP"; fail "Backup vacío — abortado"; }
        ok "Backup OK ($(du -h "$BACKUP" | cut -f1))"
        ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | tail -n +$((BACKUP_KEEP + 1)) | xargs -r rm -f

        # Offsite S3 (si S3_BUCKET está configurado en .env)
        S3_BUCKET="$(grep -E '^S3_BUCKET=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
        S3_PREFIX="$(grep -E '^S3_PREFIX=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
        S3_PREFIX="${S3_PREFIX:-backups/}"
        if [[ -n "$S3_BUCKET" ]] && command -v aws >/dev/null 2>&1; then
            info "Subiendo backup offsite → s3://${S3_BUCKET}/${S3_PREFIX}..."
            if aws s3 cp "$BACKUP" "s3://${S3_BUCKET}/${S3_PREFIX}$(basename "$BACKUP")" --quiet; then
                ok "Copia offsite S3 OK"
            else
                warn "Falló la copia offsite S3 (el backup local se conserva)"
            fi
        fi
    else
        warn "tuwayki_mysql no corre — backup omitido (primer deploy?)"
    fi
fi

# ─── 2. Código ────────────────────────────────────────────────────────────────
# reset --hard: el servidor no debe tener edits locales; evita fallo en CD/Actions.
info "Actualizando código: origin/$BRANCH"
git fetch origin "$BRANCH"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout -f "$BRANCH"
else
    git checkout -B "$BRANCH" "origin/$BRANCH"
fi
git reset --hard "origin/$BRANCH"
ok "Commit: $(git log --oneline -1)"

# ─── 3. Vendor tuwayki-core (no está en git) ──────────────────────────────────
VENDOR_DIR="$APP_DIR/_vendor/tuwayki-core"
ensure_vendor() {
    if [[ -d "$VENDOR_DIR/.git" ]]; then
        info "Actualizando _vendor/tuwayki-core..."
        git -C "$VENDOR_DIR" fetch origin --tags --quiet
        git -C "$VENDOR_DIR" checkout --detach "$TUWAYKI_CORE_SHA" --quiet
    else
        info "Clonando tuwayki-core en _vendor/..."
        mkdir -p "$APP_DIR/_vendor"
        git clone "$TUWAYKI_CORE_REPO" "$VENDOR_DIR"
        git -C "$VENDOR_DIR" checkout --detach "$TUWAYKI_CORE_SHA" --quiet
    fi
    [[ -f "$VENDOR_DIR/pyproject.toml" ]] || fail "_vendor/tuwayki-core incompleto (falta pyproject.toml)"
}
ensure_vendor
ok "tuwayki-core @ ${TUWAYKI_CORE_SHA:0:12}"

# ─── 4. Build + deploy ────────────────────────────────────────────────────────
SERVICES=(tuwayki_landing tuwayki_sys tuwayki_admin)

if $SKIP_BUILD; then
    warn "Build omitido (--skip-build)"
else
    info "Building imágenes Docker..."
    docker compose build "${SERVICES[@]}"
fi

info "Levantando stack..."
docker compose up -d --remove-orphans

# ─── 5. Esperar healthy (landing → sys/admin en cadena) ───────────────────────
info "Esperando healthy (máx $((HEALTH_WAIT_MAX * 15 / 60)) min)..."
all_healthy=false
for i in $(seq 1 "$HEALTH_WAIT_MAX"); do
    ready=true
    for c in "${SERVICES[@]}"; do
        h="$(docker inspect --format='{{.State.Health.Status}}' "$c" 2>/dev/null || echo "missing")"
        if [[ "$h" != "healthy" ]]; then
            ready=false
            break
        fi
    done
    if $ready; then
        all_healthy=true
        ok "Todos healthy (iteración $i)"
        break
    fi
    if (( i % 4 == 0 )); then
        info "  ...${i}/${HEALTH_WAIT_MAX} landing=$(docker inspect --format='{{.State.Health.Status}}' tuwayki_landing 2>/dev/null || echo '?') sys=$(docker inspect --format='{{.State.Health.Status}}' tuwayki_sys 2>/dev/null || echo '?') admin=$(docker inspect --format='{{.State.Health.Status}}' tuwayki_admin 2>/dev/null || echo '?')"
    fi
    sleep 15
done

docker compose ps

if ! $all_healthy; then
    warn "Timeout de health — últimos logs de landing:"
    docker compose logs tuwayki_landing --tail=40
    fail "No todos los servicios llegaron a healthy"
fi

# ─── 6. Verificación interna (/api/ping) ────────────────────────────────────
info "Verificando /api/ping dentro de los contenedores..."
for c in "${SERVICES[@]}"; do
    docker exec "$c" curl -sf http://localhost:3000/api/ping >/dev/null \
        || fail "Ping falló en $c"
    ok "Ping OK: $c"
done

# ─── 7. NPM + health externo ──────────────────────────────────────────────────
if ! $SKIP_NPM; then
    NPM_CONTAINER="$(docker ps --format '{{.Names}}' | grep -iE 'nginx-proxy-manager|npm' | head -1 || true)"
    if [[ -n "$NPM_CONTAINER" ]]; then
        info "Reiniciando proxy: $NPM_CONTAINER"
        docker restart "$NPM_CONTAINER" >/dev/null
        sleep 15
        ok "NPM reiniciado"
    else
        warn "Contenedor NPM no encontrado — omitiendo restart"
    fi
fi

info "Verificando endpoints públicos..."
check_public_health() {
    local url="$1"
    local label="$2"
    local surface
    surface="$(curl -sf --max-time 15 "$url" | grep -o '"surface":"[^"]*"' || true)"
    [[ -n "$surface" ]] || fail "Health externo falló: $label ($url)"
    ok "$label → $surface"
}

check_public_health "https://tuwayki.app/api/health" "landing"
check_public_health "https://sys.tuwayki.app/api/health" "sys"
check_public_health "https://admin.tuwayki.app/api/health" "admin"

# ─── 8. Cron de backup (auto-install idempotente) ──────────────────────────────
CRON_CMD="0 2 * * * ${APP_DIR}/ops/backup-db.sh ${APP_DIR}/backups >> /var/log/tuwayki-backup.log 2>&1"
if crontab -l 2>/dev/null | grep -qF "backup-db.sh"; then
    ok "Cron de backup ya instalado"
else
    info "Instalando cron de backup diario (02:00 AM)..."
    ( crontab -l 2>/dev/null; echo "$CRON_CMD" ) | crontab -
    ok "Cron instalado: $CRON_CMD"
fi

# ─── 9. Backup health-check ──────────────────────────────────────────────────
if [[ -x "$APP_DIR/ops/backup-healthcheck.sh" ]]; then
    info "Ejecutando backup health-check..."
    S3_BUCKET="${S3_BUCKET:-$(grep -E '^S3_BUCKET=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')}" \
    DB_NAME="${DB_NAME:-sistema_ventas}" \
    bash "$APP_DIR/ops/backup-healthcheck.sh" "$APP_DIR/backups" || warn "Backup health-check reportó problemas (no bloquea el deploy)"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DEPLOY DOCKER PROD COMPLETADO${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo "  Commit:  $(git rev-parse --short HEAD)"
echo "  Branch:  $BRANCH"
echo "  Landing: https://tuwayki.app"
echo "  Sys:     https://sys.tuwayki.app"
echo "  Admin:   https://admin.tuwayki.app"
echo ""
