#!/usr/bin/env bash
# =============================================================================
# scripts/deploy.sh — Deploy unificado para TUWAYKI Sistema de Ventas
#
# Uso:
#   bash scripts/deploy.sh              # Deploy estándar (test server)
#   bash scripts/deploy.sh --prod       # Deploy producción (extra validaciones)
#   bash scripts/deploy.sh --rollback   # Rollback al commit anterior
#
# Variables de entorno opcionales:
#   APP_DIR      Directorio de la app (default: directorio del script/../)
#   BRANCH       Branch de git a desplegar (default: main)
#   BACKEND_PORT Puerto del backend (default: 8000)
#   SKIP_MIGRATE Saltar migraciones (default: false)
# =============================================================================
set -euo pipefail

# ─── Colores ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ─── Defaults ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BRANCH="${BRANCH:-main}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
SKIP_MIGRATE="${SKIP_MIGRATE:-false}"
IS_PROD=false
IS_ROLLBACK=false

for arg in "$@"; do
    case "$arg" in
        --prod)     IS_PROD=true ;;
        --rollback) IS_ROLLBACK=true ;;
    esac
done

cd "$APP_DIR"
info "Deploy iniciado en: $APP_DIR"
info "Branch: $BRANCH | Puerto: $BACKEND_PORT | Prod: $IS_PROD"

# ─── 0. Verificar prerequisitos ──────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || fail "python3 no encontrado"
command -v git      >/dev/null 2>&1 || fail "git no encontrado"

if [[ ! -d ".venv" ]]; then
    fail "No existe .venv/ — ejecutar: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
fi

if [[ ! -f ".env" ]]; then
    fail "No existe .env — copiar .env.example y configurar"
fi

PYTHON=".venv/bin/python"
PIP=".venv/bin/pip"
ALEMBIC=".venv/bin/alembic"

if [[ ! -x "$PYTHON" ]]; then
    fail "Python del venv no encontrado en $PYTHON"
fi

# ─── 1. Cargar variables de entorno de forma segura ──────────────────────────
info "Cargando variables de entorno..."
eval "$($PYTHON scripts/load_env.py)"
ok "Variables cargadas (python-dotenv)"

# ─── 2. Guardar commit actual (para rollback) ───────────────────────────────
PREV_COMMIT="$(git rev-parse HEAD)"
info "Commit actual (pre-deploy): $PREV_COMMIT"

# ─── 3. Rollback? ───────────────────────────────────────────────────────────
if $IS_ROLLBACK; then
    if [[ -f ".deploy_prev_commit" ]]; then
        ROLLBACK_TO="$(cat .deploy_prev_commit)"
        warn "ROLLBACK a commit: $ROLLBACK_TO"
        git reset --hard "$ROLLBACK_TO"
    else
        fail "No se encontró .deploy_prev_commit — rollback manual necesario"
    fi
else
    # Guardar para posible rollback futuro
    echo "$PREV_COMMIT" > .deploy_prev_commit
fi

# ─── 4. Actualizar código ───────────────────────────────────────────────────
if ! $IS_ROLLBACK; then
    info "Actualizando código desde origin/$BRANCH..."
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
    NEW_COMMIT="$(git rev-parse HEAD)"
    ok "Código actualizado a: $NEW_COMMIT"

    if [[ "$PREV_COMMIT" == "$NEW_COMMIT" ]]; then
        warn "Sin cambios nuevos (mismo commit)"
    fi
fi

# ─── 5. Instalar/actualizar dependencias ────────────────────────────────────
info "Verificando dependencias..."
$PIP install -q -r requirements.txt 2>/dev/null || {
    warn "Error en pip install — intentando con --no-deps"
    $PIP install -q --no-deps -r requirements.txt
}
ok "Dependencias OK"

# ─── 6. Migraciones de base de datos ────────────────────────────────────────
if [[ "$SKIP_MIGRATE" != "true" ]]; then
    info "Ejecutando migraciones Alembic..."
    $ALEMBIC upgrade head || {
        fail "Migraciones fallaron. Revisar manualmente y re-ejecutar o usar --rollback"
    }
    CURRENT_REV="$($ALEMBIC current 2>/dev/null | head -1)"
    ok "Migraciones OK — revision: $CURRENT_REV"
else
    warn "Migraciones saltadas (SKIP_MIGRATE=true)"
fi

# ─── 7. Matar procesos anteriores ───────────────────────────────────────────
info "Deteniendo procesos anteriores..."
fuser -k "$BACKEND_PORT/tcp" 2>/dev/null || true
pkill -f "reflex run" 2>/dev/null || true
pkill -f "granian" 2>/dev/null || true
sleep 2
# Verificar que el puerto está libre
if ss -ltnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
    fail "Puerto $BACKEND_PORT sigue ocupado después de kill"
fi
ok "Procesos anteriores detenidos"

# ─── 8. Levantar backend ────────────────────────────────────────────────────
info "Iniciando backend en puerto $BACKEND_PORT..."
mkdir -p logs

nohup $PYTHON -m reflex run \
    --env prod \
    --backend-only \
    --backend-host 0.0.0.0 \
    --backend-port "$BACKEND_PORT" \
    > logs/backend.out 2>&1 &

BACKEND_PID=$!
info "Backend PID: $BACKEND_PID"

# ─── 9. Esperar a que levante ────────────────────────────────────────────────
info "Esperando a que el backend responda..."
MAX_WAIT=60
WAITED=0
while [[ $WAITED -lt $MAX_WAIT ]]; do
    if curl -sf "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [[ $WAITED -ge $MAX_WAIT ]]; then
    warn "Backend no respondió en ${MAX_WAIT}s — revisando logs..."
    tail -30 logs/backend.out
    fail "Backend no levantó correctamente"
fi

ok "Backend respondiendo en puerto $BACKEND_PORT"

# ─── 10. Health check ───────────────────────────────────────────────────────
info "Ejecutando health check..."
HEALTH_RESPONSE="$(curl -sf "http://127.0.0.1:${BACKEND_PORT}/api/health" || echo '{}')"
echo "  $HEALTH_RESPONSE"

# ─── 11. Smoke test básico ──────────────────────────────────────────────────
info "Smoke test..."
HTTP_CODE="$(curl -sf -o /dev/null -w '%{http_code}' "http://127.0.0.1:${BACKEND_PORT}/api/ping" || echo '000')"
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "Ping OK (200)"
else
    warn "Ping devolvió: $HTTP_CODE"
fi

# ─── 12. Resumen ────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DEPLOY COMPLETADO EXITOSAMENTE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Commit:    $(git rev-parse --short HEAD)"
echo "  Branch:    $BRANCH"
echo "  Puerto:    $BACKEND_PORT"
echo "  Health:    http://127.0.0.1:${BACKEND_PORT}/api/health"
echo "  Logs:      $APP_DIR/logs/backend.out"
echo "  Rollback:  bash scripts/deploy.sh --rollback"
echo ""

if $IS_PROD; then
    echo -e "${YELLOW}  *** MODO PRODUCCIÓN ***${NC}"
    echo "  Verificar endpoints externos antes de confirmar."
    echo ""
fi
