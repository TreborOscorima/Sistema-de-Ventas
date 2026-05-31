#!/usr/bin/env bash
# =============================================================================
# docker-entrypoint.sh — Pre-arranque del contenedor TUWAYKI
#
# 1. Espera a que MySQL y Redis estén disponibles.
# 2. Ejecuta migraciones Alembic (upgrade head).
# 3. Arranca Reflex con los argumentos pasados por CMD (init/install/build los
#    gestiona reflex run sobre el volumen .web/).
# =============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}[ENTRYPOINT]${NC} $*"; }
ok()    { echo -e "${GREEN}[ENTRYPOINT]${NC} $*"; }
warn()  { echo -e "${YELLOW}[ENTRYPOINT]${NC} $*"; }
fail()  { echo -e "${RED}[ENTRYPOINT]${NC} $*"; exit 1; }

# ─── 1. Esperar MySQL ───────────────────────────────────────────────────────
# En el stack de 3 superficies el servicio MySQL tiene alias tuwayki_mysql; compose inyecta DB_HOST.
DB_HOST="${DB_HOST:-mysql}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-app}"
MAX_WAIT=120
SOCKET_TIMEOUT=5

# Breve pausa para que la red del contenedor esté lista (evita fallos DNS en arranque)
sleep 3

info "Esperando MySQL en ${DB_HOST}:${DB_PORT}..."
WAITED=0
while [[ $WAITED -lt $MAX_WAIT ]]; do
    if python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(${SOCKET_TIMEOUT})
try:
    s.connect(('${DB_HOST}', ${DB_PORT}))
    s.close()
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [[ $WAITED -ge $MAX_WAIT ]]; then
    fail "MySQL no disponible después de ${MAX_WAIT}s"
fi
ok "MySQL disponible"

# ─── 2. Esperar Redis (obligatorio en prod: rate limiting + sesiones + caché L2) ─
REDIS_URL="${REDIS_URL:-}"
if [[ -n "$REDIS_URL" ]]; then
    info "Verificando Redis..."
    WAITED=0
    while [[ $WAITED -lt 30 ]]; do
        if python3 -c "
import redis, os
r = redis.from_url(os.environ['REDIS_URL'])
r.ping()
" 2>/dev/null; then
            break
        fi
        sleep 2
        WAITED=$((WAITED + 2))
    done
    if [[ $WAITED -ge 30 ]]; then
        # Fail-fast: arrancar Reflex sin Redis implica rate-limit/sesiones rotos al primer request.
        fail "Redis no disponible después de 30s (REDIS_URL=${REDIS_URL})"
    fi
    ok "Redis disponible"
fi

# ─── 3. Migraciones Alembic ─────────────────────────────────────────────────
SKIP_MIGRATE="${SKIP_MIGRATE:-false}"
if [[ "$SKIP_MIGRATE" != "true" ]]; then
    info "Ejecutando migraciones Alembic..."
    # Fail-fast: arrancar con schema incompatible corrompe datos (FKs/constraints rotos).
    if ! alembic upgrade head; then
        fail "Migraciones fallaron — abortando arranque"
    fi
    ok "Migraciones aplicadas correctamente"
else
    warn "Migraciones saltadas (SKIP_MIGRATE=true)"
fi

# ─── 4. Información de arranque ─────────────────────────────────────────────
SURFACE="${APP_SURFACE:-all}"
info "Superficie: ${SURFACE}"
info "Iniciando Reflex: $*"

# ─── 4b. Pre-init + vendor pre-builds (Rolldown CJS fix) ────────────────────
# vite.config.js puede tener aliases vendor-emotion/vendor-recharts si
# templates.py fue parcheado. Si los archivos no existen el build falla con
# [UNLOADABLE_DEPENDENCY]. Crearlos antes de lanzar reflex run.
info "Pre-inicializando frontend (reflex init)..."
reflex init 2>&1 | tail -3 && ok "reflex init OK" || warn "reflex init con error — continuando"

BUN_BIN=""
for _c in \
    "$HOME/.local/share/reflex/bun/bin/bun" \
    "/app/.local/share/reflex/bun/bin/bun" \
    "/root/.local/share/reflex/bun/bin/bun" \
    "$(command -v bun 2>/dev/null || true)"; do
    [[ -n "$_c" && -x "$_c" ]] && { BUN_BIN="$_c"; break; }
done

if [[ -n "$BUN_BIN" && -f ".web/package.json" ]]; then
    info "Instalando node_modules (.web/)..."
    (cd .web && "$BUN_BIN" install 2>/dev/null) \
        && ok "node_modules OK" || warn "bun install falló — continuando"
    NM=".web/node_modules"

    if [[ ! -f ".web/vendor-emotion/react/dist/emotion-react.esm.js" \
          && -f "$NM/@emotion/react/dist/emotion-react.esm.js" ]]; then
        info "Creando vendor-emotion..."
        mkdir -p .web/vendor-emotion/react/dist .web/vendor-emotion/cache/dist
        "$BUN_BIN" build --target node --format esm \
            --external react --external react-dom \
            "$NM/@emotion/react/dist/emotion-react.esm.js" \
            --outfile .web/vendor-emotion/react/dist/emotion-react.esm.js \
            2>/dev/null && ok "vendor-emotion/react OK" || warn "vendor-emotion/react FAIL"
        "$BUN_BIN" build --target node --format esm \
            "$NM/@emotion/cache/dist/emotion-cache.esm.js" \
            --outfile .web/vendor-emotion/cache/dist/emotion-cache.esm.js \
            2>/dev/null && ok "vendor-emotion/cache OK" || warn "vendor-emotion/cache FAIL"
    else
        ok "vendor-emotion ya existe"
    fi

    if [[ ! -f ".web/vendor-recharts/recharts.esm.js" \
          && -f "$NM/recharts/es6/index.js" ]]; then
        info "Creando vendor-recharts..."
        mkdir -p .web/vendor-recharts
        "$BUN_BIN" build --target browser --format esm \
            --external react --external react-dom \
            --external react-is --external "react/jsx-runtime" \
            "$NM/recharts/es6/index.js" \
            --outfile .web/vendor-recharts/recharts.esm.js \
            2>/dev/null && ok "vendor-recharts OK" || warn "vendor-recharts FAIL"
    else
        ok "vendor-recharts ya existe"
    fi
else
    warn "bun no encontrado o .web/package.json ausente — vendor pre-builds omitidos"
fi
# ─────────────────────────────────────────────────────────────────────────────

# ─── 5. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
exec "$@"
