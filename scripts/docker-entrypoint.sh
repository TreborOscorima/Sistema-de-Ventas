#!/usr/bin/env bash
# =============================================================================
# docker-entrypoint.sh — Pre-arranque del contenedor TUWAYKI
#
# 1. Espera a que MySQL y Redis estén disponibles.
# 2. Ejecuta migraciones Alembic (upgrade head).
# 3. Aplica Rolldown CJS circular-dep fixes (Vite 8 / Rolldown 1.x).
# 4. Arranca Reflex con los argumentos pasados por CMD.
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

# ─── 4b. Pre-init + Rolldown CJS circular-dep fixes (Vite 8 / Rolldown 1.x) ─
# Rolldown renombra lazy-getters CJS a letras simples (r,t,n,i) que quedan
# shadowed dentro de closures factory → TypeError: r is not a function.
# Fix A: parchear templates.py (genera vite.config.js con aliases ESM).
# Fix B: pre-bundlear librerías afectadas con bun como ESM puro.
# NOTA: templates.py puede estar pre-parcheado desde el Dockerfile (minify+aliases).
#       Este paso aplica lo que falte y crea los vendor files (que van en .web/,
#       que es un volumen nombrado y no existe en la imagen).
info "Pre-inicializando frontend (reflex init)..."
if reflex init 2>&1 | tail -3; then
    ok "reflex init OK"
else
    warn "reflex init terminó con error — continuando de todos modos"
fi

info "Aplicando Rolldown CJS fixes..."

# Localizar bun (descargado por reflex init en $HOME/.local/share/reflex/bun/bin/)
BUN_BIN=""
for candidate in \
    "$HOME/.local/share/reflex/bun/bin/bun" \
    "/app/.local/share/reflex/bun/bin/bun" \
    "/root/.local/share/reflex/bun/bin/bun" \
    "$(command -v bun 2>/dev/null || true)"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
        BUN_BIN="$candidate"
        break
    fi
done

if [[ -z "$BUN_BIN" ]]; then
    warn "bun no encontrado — vendor pre-bundles omitidos (Rolldown fixes pueden fallar en build)"
else
    ok "bun: $BUN_BIN"
    NM=".web/node_modules"

    # Fix A: patch templates.py (el Dockerfile ya aplica minify+aliases en build stage;
    #         este patch verifica y completa cualquier alias que falte).
    TMPL=""
    for tmpl_path in \
        "/usr/local/lib/python3.11/site-packages/reflex_base/compiler/templates.py" \
        "/usr/local/lib/python3.12/site-packages/reflex_base/compiler/templates.py" \
        "/usr/local/lib/python3.13/site-packages/reflex_base/compiler/templates.py"; do
        if [[ -f "$tmpl_path" ]]; then TMPL="$tmpl_path"; break; fi
    done

    if [[ -n "$TMPL" ]]; then
        python3 - "$TMPL" <<'TMPATCH'
import sys
path = sys.argv[1]
c = open(path).read()
changed = False
def p(label, check, old, new):
    global c, changed
    if check not in c:
        if old in c:
            c = c.replace(old, new, 1); changed = True
            print(f'[PATCH] {label}')
        else:
            print(f'[WARN]  {label}: anchor not found — puede que templates.py cambió')
    else:
        print(f'[SKIP]  {label}')
p('minify:esbuild', 'minify: "esbuild"',
  'sourcemap: false,', 'sourcemap: false,\n    minify: "esbuild",')
p('conditions', '"module", "browser", "import"',
  'resolve: {{', 'resolve: {{\n    conditions: ["module", "browser", "import", "default"],\n    mainFields: ["browser", "module", "jsnext"],')
p('@emotion alias', 'vendor-emotion',
  'find: "@",',
  'find: "@emotion/react",\n        replacement: fileURLToPath(new URL("./vendor-emotion/react/dist/emotion-react.esm.js", import.meta.url)),\n      }},\n      {{\n        find: "@emotion/cache",\n        replacement: fileURLToPath(new URL("./vendor-emotion/cache/dist/emotion-cache.esm.js", import.meta.url)),\n      }},\n      {{\n        find: "@",')
p('socket.io alias', 'socket.io-client',
  'find: "@",',
  'find: "socket.io-client",\n        replacement: fileURLToPath(new URL("./node_modules/socket.io-client/dist/socket.io.esm.min.js", import.meta.url)),\n      }},\n      {{\n        find: "@",')
p('recharts alias', 'recharts',
  'find: "@",',
  'find: "recharts",\n        replacement: fileURLToPath(new URL("./vendor-recharts/recharts.esm.js", import.meta.url)),\n      }},\n      {{\n        find: "@",')
if changed:
    open(path, 'w').write(c)
    print('[OK] templates.py actualizado')
else:
    print('[OK] templates.py ya estaba al día')
TMPATCH
        ok "templates.py verificado"
    else
        warn "templates.py no encontrado — Rolldown aliases omitidos"
    fi

    # Fix B: vendor-emotion → @emotion/react + @emotion/cache como ESM puro
    if [[ ! -f ".web/vendor-emotion/react/dist/emotion-react.esm.js" ]]; then
        info "Pre-bundling @emotion → vendor-emotion/ ..."
        mkdir -p .web/vendor-emotion/react/dist .web/vendor-emotion/cache/dist
        "$BUN_BIN" build --target node --format esm \
            "$NM/@emotion/react/dist/emotion-react.cjs.dev.js" \
            --outfile .web/vendor-emotion/react/dist/emotion-react.esm.js 2>/dev/null \
            && ok "vendor-emotion/react" || warn "vendor-emotion/react FAIL"
        "$BUN_BIN" build --target node --format esm \
            "$NM/@emotion/cache/dist/emotion-cache.cjs.dev.js" \
            --outfile .web/vendor-emotion/cache/dist/emotion-cache.esm.js 2>/dev/null \
            && ok "vendor-emotion/cache" || warn "vendor-emotion/cache FAIL"
    else
        ok "vendor-emotion ya existe"
    fi

    # Fix B: vendor-recharts → recharts/es6 como ESM puro
    # CRÍTICO: --external react/react-dom evita 2 instancias de React en el browser
    # (sin esto: TypeError: Cannot read properties of null (reading 'useContext'))
    if [[ ! -f ".web/vendor-recharts/recharts.esm.js" ]]; then
        info "Pre-bundling recharts → vendor-recharts/ ..."
        mkdir -p .web/vendor-recharts
        "$BUN_BIN" build --target browser --format esm \
            --external react \
            --external react-dom \
            --external react-is \
            --external "react/jsx-runtime" \
            "$NM/recharts/es6/index.js" \
            --outfile .web/vendor-recharts/recharts.esm.js 2>/dev/null \
            && ok "vendor-recharts" || warn "vendor-recharts FAIL"
    else
        ok "vendor-recharts ya existe"
    fi
fi
# ─────────────────────────────────────────────────────────────────────────────

# ─── 5. Ejecutar CMD (reflex run ...) ───────────────────────────────────────
exec "$@"
