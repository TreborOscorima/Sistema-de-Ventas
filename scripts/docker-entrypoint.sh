#!/usr/bin/env bash
# =============================================================================
# docker-entrypoint.sh — Pre-arranque del contenedor TUWAYKI
#
# 1. Espera a que MySQL y Redis estén disponibles.
# 2. Ejecuta migraciones Alembic (upgrade head).
# 3. Arranca Reflex con los argumentos pasados por CMD.
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

info "Esperando MySQL en ${DB_HOST}:${DB_PORT}..."
WAITED=0
while [[ $WAITED -lt $MAX_WAIT ]]; do
    if python3 -c "
import socket
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('${DB_HOST}', ${DB_PORT}))
    s.close()
    exit(0)
except:
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

# ─── 2. Esperar Redis (si REDIS_URL está configurada) ───────────────────────
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
        warn "Redis no respondió en 30s — continuando de todas formas"
    else
        ok "Redis disponible"
    fi
fi

# ─── 3. Migraciones Alembic ─────────────────────────────────────────────────
SKIP_MIGRATE="${SKIP_MIGRATE:-false}"
if [[ "$SKIP_MIGRATE" != "true" ]]; then
    info "Ejecutando migraciones Alembic..."
    if alembic upgrade head; then
        ok "Migraciones aplicadas correctamente"
    else
        warn "Migraciones fallaron — verificar manualmente"
    fi
else
    warn "Migraciones saltadas (SKIP_MIGRATE=true)"
fi

# ─── 4. Información de arranque ─────────────────────────────────────────────
SURFACE="${APP_SURFACE:-all}"
info "Superficie: ${SURFACE}"
info "Iniciando Reflex: $*"

# ─── 5. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
exec "$@"
