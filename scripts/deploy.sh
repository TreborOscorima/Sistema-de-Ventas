#!/usr/bin/env bash
# =============================================================================
# scripts/deploy.sh — Deploy unificado para TUWAYKI Sistema de Ventas
#
# Uso:
#   bash scripts/deploy.sh              # Deploy COMPLETO (backend + frontend)
#   bash scripts/deploy.sh --prod       # Deploy producción (extra validaciones)
#   bash scripts/deploy.sh --rollback   # Rollback al commit anterior
#   bash scripts/deploy.sh --backend-only  # SOLO backend (API/WS). Usar
#                                          # únicamente cuando los cambios NO
#                                          # tocan páginas, componentes ni assets.
#                                          # Si hay cambios de UI, usar deploy
#                                          # completo (sin --backend-only).
#
# Variables de entorno opcionales:
#   APP_DIR       Directorio de la app (default: directorio del script/../)
#   BRANCH        Branch de git a desplegar (default: main)
#   BACKEND_PORT  Puerto del backend (default: 8000)
#   BACKEND_ONLY  Solo backend sin frontend (default: false, usar true con nginx)
#   SKIP_MIGRATE  Saltar migraciones (default: false)
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
BACKEND_ONLY="${BACKEND_ONLY:-false}"
SKIP_MIGRATE="${SKIP_MIGRATE:-false}"
IS_PROD=false
IS_ROLLBACK=false

for arg in "$@"; do
    case "$arg" in
        --prod)          IS_PROD=true ;;
        --rollback)      IS_ROLLBACK=true ;;
        --backend-only)  BACKEND_ONLY=true ;;
    esac
done

cd "$APP_DIR"
info "Deploy iniciado en: $APP_DIR"
info "Branch: $BRANCH | Puerto: $BACKEND_PORT | Prod: $IS_PROD | Solo backend: $BACKEND_ONLY"

# ─── 0. Verificar prerrequisitos ──────────────────────────────────────────────
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

    # Detectar si hay cambios en frontend (páginas/componentes) y avisar si --backend-only
    if [[ "$BACKEND_ONLY" == "true" && "$PREV_COMMIT" != "$NEW_COMMIT" ]]; then
        FRONTEND_CHANGES="$(git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" -- 'app/pages/' 'app/components/' 'assets/' 'rxconfig.py' | head -5)"
        if [[ -n "$FRONTEND_CHANGES" ]]; then
            echo ""
            warn "╔══════════════════════════════════════════════════════════╗"
            warn "║  HAY CAMBIOS EN FRONTEND pero estás usando --backend-only  ║"
            warn "║  Los cambios en páginas/componentes NO se verán hasta     ║"
            warn "║  que re-deploys SIN --backend-only (compila frontend).    ║"
            warn "╚══════════════════════════════════════════════════════════╝"
            echo "  Archivos cambiados:"
            echo "$FRONTEND_CHANGES" | sed 's/^/    /'
            echo ""
        fi
    fi

    # Auto-limpiar .web/ si hay cambios que afectan al frontend compilado
    # Esto fuerza a Reflex a recompilar en lugar de servir el build cacheado
    if [[ "$BACKEND_ONLY" != "true" && "$PREV_COMMIT" != "$NEW_COMMIT" ]]; then
        NEED_REBUILD="$(git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" -- 'app/pages/' 'app/components/' 'app/states/' 'app/state.py' 'app/app.py' 'app/enums.py' 'app/constants.py' 'assets/' 'rxconfig.py' '.env' | head -1)"
        if [[ -n "$NEED_REBUILD" ]]; then
            info "Cambios de frontend detectados — limpiando build cacheado (.web/)..."
            rm -rf .web
            ok "Build anterior limpiado. Reflex recompilará el frontend."
        fi
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

# ─── 6b. Sincronizar config de nginx (solo si ya está instalada) ────────────
NGINX_CONF_SRC="$APP_DIR/ops/nginx/tuwayki-test-server.conf"
NGINX_CONF_DST="/etc/nginx/sites-available/tuwayki"
if [[ -f "$NGINX_CONF_SRC" && -f "$NGINX_CONF_DST" ]]; then
    if ! diff -q "$NGINX_CONF_SRC" "$NGINX_CONF_DST" >/dev/null 2>&1; then
        info "Config nginx desactualizada — sincronizando desde repo..."
        sudo cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
        if sudo nginx -t >/dev/null 2>&1; then
            sudo systemctl reload nginx
            ok "Nginx config actualizada y recargada"
        else
            warn "nginx -t falló tras actualizar config — verificar manualmente"
        fi
    else
        ok "Nginx config sin cambios"
    fi
fi

# ─── 7. Matar procesos anteriores ───────────────────────────────────────────
info "Deteniendo procesos anteriores..."
fuser -k "$BACKEND_PORT/tcp" 2>/dev/null || true
pkill -f "reflex run" 2>/dev/null || true
pkill -f "granian" 2>/dev/null || true
# Siempre matar procesos bun/next zombie (evita frontend stale)
pkill -f "bun run prod" 2>/dev/null || true
pkill -f "bun run dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
fuser -k "3000/tcp" 2>/dev/null || true
sleep 2
# Verificar que el puerto está libre
if ss -ltnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
    fail "Puerto $BACKEND_PORT sigue ocupado después de kill"
fi
ok "Procesos anteriores detenidos"

# ─── 8. Levantar backend ────────────────────────────────────────────────────
mkdir -p logs

if [[ "$BACKEND_ONLY" == "true" ]]; then
    info "Iniciando solo backend (--backend-only) en puerto $BACKEND_PORT..."
    nohup $PYTHON -m reflex run \
        --env prod \
        --backend-only \
        --backend-host 0.0.0.0 \
        --backend-port "$BACKEND_PORT" \
        > logs/backend.out 2>&1 &
    MAX_WAIT=60
else
    # Reflex 0.9.x prod mode requiere .web/package.json antes de arrancar.
    # Si deploy.sh borró .web/ (cambios de frontend), hay que re-inicializar.
    info "Inicializando directorio web (reflex init)..."
    $PYTHON -m reflex init
    ok "Reflex web directory listo"

    # Instalar node_modules explícitamente ANTES de los vendor builds.
    # reflex init crea .web/package.json pero NO corre bun install —
    # eso ocurre dentro de reflex run, demasiado tarde para nuestros vendor builds.
    info "Instalando dependencias npm (.web/node_modules)..."
    if (cd .web && "$BUN_BIN" install --frozen-lockfile 2>/dev/null); then
        ok "node_modules instalados"
    else
        warn "frozen-lockfile falló — reintentando sin lock..."
        (cd .web && "$BUN_BIN" install) && ok "node_modules instalados"
    fi

    # ── Rolldown CJS circular-dep fixes (Vite 8 / Rolldown 1.x) ─────────────
    # Rolldown renombra lazy-getters CJS a letras simples (r,t,n,i) que quedan
    # shadowed dentro de closures factory → TypeError: r is not a function.
    # Librerías afectadas: @emotion (circular en CSS-in-JS), socket.io-client
    # (circular en engine.io), recharts (circular en lodash interno).
    #
    # Fix A — templates.py: genera vite.config.js con aliases ESM + minify esbuild.
    #          DEBE aplicarse ANTES de reflex run (que regenera vite.config.js).
    # Fix B — bun pre-bundle: convierte CJS problemáticos a ESM puro antes del build.
    BUN_BIN="$HOME/.local/share/reflex/bun/bin/bun"
    NM=".web/node_modules"
    TMPL=".venv/lib/python3.12/site-packages/reflex_base/compiler/templates.py"

    # Helper: bun build con logging de errores visible (sin 2>/dev/null que oculta fallos)
    bun_vendor() {
        local label="$1"; shift
        local log_file="/tmp/bun_vendor_${label//\//_}.log"
        if "$BUN_BIN" "$@" > "$log_file" 2>&1; then
            ok "$label ($(tail -1 "$log_file" | grep -oE '[0-9.]+ [KMG]B' || echo 'OK'))"
        else
            warn "$label FAIL — error:"
            tail -5 "$log_file"
        fi
    }

    # Fix A: patch templates.py (sobrevive reflex run porque ES el generador)
    if [[ -f "$TMPL" ]]; then
        $PYTHON "$TMPL" 2>/dev/null || true  # just test it exists and is parseable
        $PYTHON - "$TMPL" <<'TMPATCH'
import sys, re
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
            print(f'[WARN]  {label}: anchor not found')
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
TMPATCH
        ok "templates.py patches OK"
    else
        warn "templates.py no encontrado en $TMPL"
    fi

    # Fix B: vendor-emotion → @emotion/react + @emotion/cache como ESM puro
    # --target node: SSR-safe (evita ReferenceError: document is not defined en prerender)
    # Fuente: emotion-react.esm.js (v11.14+); antes era emotion-react.cjs.dev.js (obsoleto)
    if [[ ! -f ".web/vendor-emotion/react/dist/emotion-react.esm.js" ]]; then
        info "Pre-bundling @emotion → vendor-emotion/ ..."
        mkdir -p .web/vendor-emotion/react/dist .web/vendor-emotion/cache/dist
        bun_vendor "vendor-emotion/react" build --target node --format esm \
            --external react --external react-dom \
            "$NM/@emotion/react/dist/emotion-react.esm.js" \
            --outfile .web/vendor-emotion/react/dist/emotion-react.esm.js
        bun_vendor "vendor-emotion/cache" build --target node --format esm \
            "$NM/@emotion/cache/dist/emotion-cache.esm.js" \
            --outfile .web/vendor-emotion/cache/dist/emotion-cache.esm.js
    else
        ok "vendor-emotion ya existe"
    fi

    # Fix B: vendor-recharts → recharts (lodash CJS tiene circular dep con Rolldown)
    if [[ ! -f ".web/vendor-recharts/recharts.esm.js" ]]; then
        info "Pre-bundling recharts → vendor-recharts/ ..."
        mkdir -p .web/vendor-recharts
        bun_vendor "vendor-recharts" build --target browser --format esm \
            --external react --external react-dom \
            --external react-is --external "react/jsx-runtime" \
            "$NM/recharts/es6/index.js" \
            --outfile .web/vendor-recharts/recharts.esm.js
    else
        ok "vendor-recharts ya existe"
    fi
    # ─────────────────────────────────────────────────────────────────────────

    info "Iniciando backend + frontend en puerto $BACKEND_PORT..."
    nohup $PYTHON -m reflex run \
        --env prod \
        --backend-host 0.0.0.0 \
        --backend-port "$BACKEND_PORT" \
        > logs/backend.out 2>&1 &
    # El frontend tarda más en compilar
    MAX_WAIT=300
fi

BACKEND_PID=$!
info "Backend PID: $BACKEND_PID"

# ─── 9. Esperar a que levante ────────────────────────────────────────────────
info "Esperando a que el backend responda (máx ${MAX_WAIT}s)..."
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

# ─── 9b. Esperar al frontend (solo en modo completo) ────────────────────────
# Reflex 0.9.3 prod mode sirve frontend + API desde el mismo proceso (BACKEND_PORT).
# Ya no existe un servidor Next.js separado en puerto 3000.
if [[ "$BACKEND_ONLY" != "true" ]]; then
    FRONTEND_PORT=$BACKEND_PORT
    info "Esperando a que el frontend responda en puerto $FRONTEND_PORT (máx 300s)..."
    FE_WAITED=0
    FE_MAX=300
    while [[ $FE_WAITED -lt $FE_MAX ]]; do
        if curl -sf -o /dev/null "http://127.0.0.1:${FRONTEND_PORT}/"; then
            break
        fi
        sleep 3
        FE_WAITED=$((FE_WAITED + 3))
    done

    if [[ $FE_WAITED -ge $FE_MAX ]]; then
        warn "Frontend no respondió en ${FE_MAX}s — revisando logs..."
        tail -20 logs/backend.out
        fail "Frontend no levantó correctamente. Revisar logs/backend.out"
    fi
    ok "Frontend respondiendo en puerto $FRONTEND_PORT (tardó ~${FE_WAITED}s)"
fi

# ─── 10. Health check ───────────────────────────────────────────────────────
info "Ejecutando health check..."
HEALTH_RESPONSE="$(curl -sf "http://127.0.0.1:${BACKEND_PORT}/api/health" || echo '{}')"
echo "  $HEALTH_RESPONSE"

# ─── 11. Prueba rápida de funcionamiento ────────────────────────────────────
info "Prueba rápida de funcionamiento..."
HTTP_CODE="$(curl -sf -o /dev/null -w '%{http_code}' "http://127.0.0.1:${BACKEND_PORT}/api/ping" || echo '000')"
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "Ping OK (200)"
else
    warn "Ping devolvió código: $HTTP_CODE"
fi

# ─── 12. Resumen final ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DEPLOY COMPLETADO EXITOSAMENTE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Commit:    $(git rev-parse --short HEAD)"
echo "  Branch:    $BRANCH"
echo "  Backend:   http://127.0.0.1:${BACKEND_PORT}"
if [[ "$BACKEND_ONLY" != "true" ]]; then
echo "  Frontend:  http://127.0.0.1:${BACKEND_PORT}"
fi
echo "  Health:    http://127.0.0.1:${BACKEND_PORT}/api/health"
echo "  Logs:      $APP_DIR/logs/backend.out"
echo "  Rollback:  bash scripts/deploy.sh --rollback"
echo ""

if $IS_PROD; then
    echo -e "${YELLOW}  *** MODO PRODUCCIÓN ***${NC}"
    echo "  Verificar endpoints externos antes de confirmar."
    echo ""
fi
