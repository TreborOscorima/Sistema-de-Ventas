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

# ─── 4b. Pre-init + patch es-toolkit node_modules (Rolldown CJS fix) ─────────
# DIAGNÓSTICO: reflex run regenera vite.config.js durante compile_app(), por lo
# que parchear ese archivo en el entrypoint no sirve (se sobreescribe antes del
# build Vite). La solución correcta es parchear es-toolkit/package.json en
# node_modules añadiendo una "import" condition para ./compat/* que apunte a
# shims ESM. Esto opera a nivel de resolución de módulos Node.js/Rolldown y
# sobrevive cualquier regeneración de vite.config.js.
#
# Causa raíz: recharts importa es-toolkit/compat/sortBy (y ~10 subpaths más).
# El export map sólo tiene "default" → ./compat/*.js (CJS). Rolldown envuelve
# cada CJS con __commonJS factory; la naming collision en el factory
# (var t=n((e=>{var t=t()...)) causa TypeError: t is not a function.
#
# Fix: compat-esm/X.mjs re-exporta X desde dist/compat/index.mjs (ESM barrel
# confirmado). Rolldown resuelve con "import" condition → ESM puro → sin wrapper.
info "Pre-inicializando frontend (reflex init)..."
reflex init 2>&1 | tail -3 && ok "reflex init OK" || warn "reflex init con error — continuando"

info "Parcheando es-toolkit compat → ESM shims (Rolldown CJS fix)..."
python3 - <<'PYEOF'
import os, json, shutil

pkg_dir  = '/app/.web/node_modules/es-toolkit'
pkg_path = pkg_dir + '/package.json'
shim_dir = pkg_dir + '/compat-esm'
mjs_barrel = pkg_dir + '/dist/compat/index.mjs'

try:
    if not os.path.isdir(pkg_dir):
        print('SKIP: es-toolkit no encontrado en node_modules')
        raise SystemExit(0)
    if not os.path.exists(mjs_barrel):
        print('SKIP: dist/compat/index.mjs no existe — versión incompatible')
        raise SystemExit(0)

    with open(pkg_path) as f:
        pkg = json.load(f)

    exports    = pkg.get('exports', {})
    compat_exp = exports.get('./compat/*', {})

    # Idempotente: skip si ya parcheado
    if isinstance(compat_exp, dict) and compat_exp.get('import', '').startswith('./compat-esm/'):
        print('es-toolkit ya parcheado — OK')
        raise SystemExit(0)

    # Crear directorio de shims ESM
    os.makedirs(shim_dir, exist_ok=True)

    # Generar shim para cada compat/X.js
    compat_dir = pkg_dir + '/compat'
    shim_count = 0
    if os.path.exists(compat_dir):
        for fname in sorted(os.listdir(compat_dir)):
            if fname.endswith('.js') and fname != 'index.js':
                func = fname[:-3]
                shim_path = shim_dir + '/' + func + '.mjs'
                with open(shim_path, 'w') as f:
                    # Re-exporta como default desde el barrel ESM confirmado
                    f.write('export { ' + func + ' as default } from "../dist/compat/index.mjs";\n')
                shim_count += 1

    # Añadir "import" condition al exports map (preserva el "default" existente)
    exports['./compat/*'] = {
        'import':  './compat-esm/*.mjs',
        'default': './compat/*.js'
    }
    pkg['exports'] = exports

    with open(pkg_path, 'w') as f:
        json.dump(pkg, f, indent=2)

    print('es-toolkit parcheado: ' + str(shim_count) + ' shims ESM en compat-esm/')

    # Limpiar caché de resolución Vite para forzar re-resolución
    for d in ['/app/.web/.vite', '/app/.web/node_modules/.vite']:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(d + ' cache limpiado')

except SystemExit:
    pass
except Exception as e:
    print('Patch fallo: ' + str(e))
    import traceback; traceback.print_exc()
PYEOF
ok "es-toolkit ESM patch OK"
# ─────────────────────────────────────────────────────────────────────────────

# ─── 5. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
exec "$@"
