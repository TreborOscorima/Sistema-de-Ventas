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

# ─── 4b. Pre-init + patch es-toolkit (Rolldown CJS fix) ──────────────────────
# Reflex 0.9.3 genera vite.config.js con estoolkitAlias() que resuelve
# 'es-toolkit/compat/X' → './es-toolkit-shims/X.js'. Esos archivos se crean
# arriba (sección "Crear es-toolkit-shims"), DESPUÉS de reflex init que borra .web/.
#
# El patch de node_modules es un segundo nivel de defensa: además de los shims,
# parchea es-toolkit/package.json añadiendo "import" condition para que Rolldown
# resuelva vía ESM cuando los shims no están disponibles.
#
# Causa raíz: recharts importa es-toolkit/compat/sortBy (y ~10 subpaths más).
# El export map sólo tiene "default" → ./compat/*.js (CJS). Rolldown envuelve
# cada CJS con __commonJS factory; la naming collision en el factory
# (var t=n((e=>{var t=t()...)) causa TypeError: t is not a function.
info "Pre-inicializando frontend (reflex init)..."
reflex init 2>&1 | tail -3 && ok "reflex init OK" || warn "reflex init con error — continuando"

# ── Crear es-toolkit-shims DESPUÉS de reflex init ────────────────────────────
# reflex init llama a copy_tree() que borra todo .web/ y copia la plantilla.
# La plantilla de Reflex 0.9.3 genera un vite.config.js con estoolkitAlias()
# que resuelve 'es-toolkit/compat/X' → './es-toolkit-shims/X.js'. Si esos
# archivos no existen, Vite falla y los chunks quedan rotos (→ loop infinito).
# Los creamos aquí, después de reflex init (que borra .web/), para que
# sobrevivan hasta que vite build los consuma.
info "Creando es-toolkit-shims para Vite..."
mkdir -p /app/.web/es-toolkit-shims
cat > /app/.web/es-toolkit-shims/get.js          << 'EOF'
export { get as default } from '../node_modules/es-toolkit/dist/compat/object/get.mjs';
EOF
cat > /app/.web/es-toolkit-shims/sortBy.js       << 'EOF'
export { sortBy as default } from '../node_modules/es-toolkit/dist/compat/array/sortBy.mjs';
EOF
cat > /app/.web/es-toolkit-shims/omit.js         << 'EOF'
export { omit as default } from '../node_modules/es-toolkit/dist/compat/object/omit.mjs';
EOF
cat > /app/.web/es-toolkit-shims/range.js        << 'EOF'
export { range as default } from '../node_modules/es-toolkit/dist/compat/math/range.mjs';
EOF
cat > /app/.web/es-toolkit-shims/throttle.js     << 'EOF'
export { throttle as default } from '../node_modules/es-toolkit/dist/compat/function/throttle.mjs';
EOF
cat > /app/.web/es-toolkit-shims/maxBy.js        << 'EOF'
export { maxBy as default } from '../node_modules/es-toolkit/dist/compat/math/maxBy.mjs';
EOF
cat > /app/.web/es-toolkit-shims/sumBy.js        << 'EOF'
export { sumBy as default } from '../node_modules/es-toolkit/dist/compat/math/sumBy.mjs';
EOF
cat > /app/.web/es-toolkit-shims/isPlainObject.js << 'EOF'
export { isPlainObject as default } from '../node_modules/es-toolkit/dist/compat/predicate/isPlainObject.mjs';
EOF
cat > /app/.web/es-toolkit-shims/minBy.js        << 'EOF'
export { minBy as default } from '../node_modules/es-toolkit/dist/compat/math/minBy.mjs';
EOF
cat > /app/.web/es-toolkit-shims/last.js         << 'EOF'
export { last as default } from '../node_modules/es-toolkit/dist/compat/array/last.mjs';
EOF
cat > /app/.web/es-toolkit-shims/uniqBy.js       << 'EOF'
export { uniqBy as default } from '../node_modules/es-toolkit/dist/compat/array/uniqBy.mjs';
EOF
ok "es-toolkit-shims creados (11 archivos)"

# ── Escribir patch script al volumen .web/ (persiste entre reinicios) ─────────
# reflex run instala node_modules DESPUÉS de arrancar (bun install interno).
# El patch debe correr en background mientras reflex init+compile se ejecutan,
# ANTES de que el Vite production build empiece (~60-90s de ventana).
cat > /app/.web/.patch_estoolkit.py << 'PATCHEOF'
import os, json, shutil, time, sys

pkg_dir  = '/app/.web/node_modules/es-toolkit'
pkg_path = pkg_dir + '/package.json'
shim_dir = pkg_dir + '/compat-esm'
mjs_barrel = pkg_dir + '/dist/compat/index.mjs'

# Esperar hasta 120s a que node_modules esté completamente disponible.
# Verificamos pkg_dir + package.json + mjs_barrel para evitar race condition
# con bun install (el dir puede existir antes que todos los archivos estén escritos).
for i in range(60):
    if (os.path.isdir(pkg_dir) and
            os.path.exists(pkg_path) and
            os.path.exists(mjs_barrel)):
        # Grace period: esperar 3s más para que bun termine de escribir
        time.sleep(3)
        break
    sys.stdout.write('[PATCH-BG] Esperando es-toolkit... ' + str(i*2) + 's\n')
    sys.stdout.flush()
    time.sleep(2)

if not os.path.exists(pkg_path):
    print('[PATCH-BG] SKIP: es-toolkit package.json no disponible tras 120s')
    sys.exit(0)
if not os.path.exists(mjs_barrel):
    print('[PATCH-BG] SKIP: dist/compat/index.mjs no existe')
    sys.exit(0)

try:
    with open(pkg_path) as f:
        pkg = json.load(f)

    compat_exp = pkg.get('exports', {}).get('./compat/*', {})
    if isinstance(compat_exp, dict) and compat_exp.get('import', '').startswith('./compat-esm/'):
        print('[PATCH-BG] es-toolkit ya parcheado — OK')
        sys.exit(0)

    os.makedirs(shim_dir, exist_ok=True)
    compat_dir = pkg_dir + '/compat'
    shim_count = 0
    if os.path.exists(compat_dir):
        for fname in sorted(os.listdir(compat_dir)):
            if fname.endswith('.js') and fname != 'index.js':
                func = fname[:-3]
                with open(shim_dir + '/' + func + '.mjs', 'w') as f:
                    f.write('export { ' + func + ' as default } from "../dist/compat/index.mjs";\n')
                shim_count += 1

    pkg['exports']['./compat/*'] = {
        'import':  './compat-esm/*.mjs',
        'default': './compat/*.js'
    }
    with open(pkg_path, 'w') as f:
        json.dump(pkg, f, indent=2)

    print('[PATCH-BG] es-toolkit parcheado: ' + str(shim_count) + ' shims ESM')

    for d in ['/app/.web/.vite', '/app/.web/node_modules/.vite']:
        if os.path.exists(d):
            shutil.rmtree(d)
            print('[PATCH-BG] cache limpiado: ' + d)

except Exception as e:
    print('[PATCH-BG] Patch fallo: ' + str(e))
    import traceback; traceback.print_exc()
PATCHEOF
chmod +x /app/.web/.patch_estoolkit.py

# Lanzar watcher en background — corre mientras reflex run instala paquetes.
# La ventana disponible: bun install (~20s) + Python compile (~60s) = ~80s
# antes de que Vite production build empiece.
python3 /app/.web/.patch_estoolkit.py &
PATCH_PID=$!
ok "es-toolkit patch watcher lanzado (PID $PATCH_PID)"
# ─────────────────────────────────────────────────────────────────────────────

# ─── 5. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
exec "$@"
