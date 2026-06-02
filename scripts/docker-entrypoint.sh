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

# ─── 4b. Pre-init + patch vite.config.js (Rolldown CJS fix) ─────────────────
# react-router.config.js tiene unstable_optimizeDeps:true → optimizeDeps aplica
# en producción. Añadimos recharts a include para que esbuild lo pre-bundle como
# ESM puro y evitar el TypeError del rolldown-runtime CJS interop.
# Este patch se aplica SIEMPRE después de reflex init (que regenera vite.config.js).
info "Pre-inicializando frontend (reflex init)..."
reflex init 2>&1 | tail -3 && ok "reflex init OK" || warn "reflex init con error — continuando"

if [[ -f ".web/vite.config.js" ]]; then
    python3 - <<'PYEOF'
import shutil, os
try:
    with open('.web/vite.config.js', 'r') as f:
        content = f.read()
    patched = False

    # Plugin: intercepta es-toolkit/compat/X y devuelve shim ESM
    # recharts importa es-toolkit/compat/sortBy etc. — CJS sin exports.import.
    # El plugin redirige a virtual module que re-exporta desde el barrel ESM
    # (dist/compat/index.mjs), evitando el rolldown-runtime CJS interop.
    if 'es-toolkit-esm' not in content:
        plugin = (
            '{\n'
            '    name: "es-toolkit-esm",\n'
            '    resolveId(id) {\n'
            '      if (id.startsWith("es-toolkit/compat/") && !id.endsWith("/")) {\n'
            '        return "\\0" + id + ".esm";\n'
            '      }\n'
            '    },\n'
            '    load(id) {\n'
            '      if (id.startsWith("\\0es-toolkit/compat/") && id.endsWith(".esm")) {\n'
            '        var name = id.slice("\\0es-toolkit/compat/".length, -4);\n'
            '        return "export { " + name + " as default } from \\"es-toolkit/compat\\"";\n'
            '      }\n'
            '    }\n'
            '  }'
        )
        content = content.replace('.concat([])', '.concat([' + plugin + '])')
        patched = True

    if patched:
        with open('.web/vite.config.js', 'w') as f:
            f.write(content)
        print('vite.config.js parcheado: plugin es-toolkit-esm')
        for d in ['.web/build', '.web/.vite']:
            if os.path.exists(d):
                shutil.rmtree(d)
                print(d + ' limpiado')
    else:
        print('vite.config.js ya tiene plugin es-toolkit-esm')
except Exception as e:
    print('Patch fallo: ' + str(e))
PYEOF
    ok "vite.config.js patch aplicado"
fi
# ─────────────────────────────────────────────────────────────────────────────

# ─── 5. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
exec "$@"
