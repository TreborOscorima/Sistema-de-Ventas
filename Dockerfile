# Sistema de Ventas (Reflex + MySQL) - Imagen para produccion
# Build multi-stage: el builder compila wheels; el runtime solo recibe el site-packages
# resultante, sin gcc/pkg-config/libmysqlclient-dev — reduce tamaño (~200MB) y superficie.

# =============================================================================
# Stage 1: builder — instala deps Python (compila wheels si es necesario)
# =============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build tools + headers MySQL SOLO para compilar wheels (no llegan a runtime).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
# --prefix=/install para que las deps queden en un árbol relocatable que copiamos al runtime.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Fix Rolldown 1.x CJS circular-dep bug (Vite 8):
# Rolldown renombra lazy-getters CJS a letras simples que quedan shadowed
# dentro de closures factory → TypeError: r is not a function en prod.
# Fix A: parchear templates.py (genera vite.config.js) con:
#   - minify: esbuild (en lugar de Rolldown)
#   - conditions: ["module","browser","import"] (preferir ESM)
#   - aliases ESM para @emotion, socket.io-client y recharts
# Fix B (vendor files): se aplica en docker-entrypoint.sh al arrancar,
#   ya que .web/ es un volumen nombrado que no existe en la imagen.
RUN python3 << 'PATCH_EOF'
import glob, sys
files = glob.glob('/install/lib/python*/site-packages/reflex_base/compiler/templates.py')
if not files:
    print('WARNING: reflex_base/compiler/templates.py not found — skipping patch')
    sys.exit(0)
path = files[0]
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
    print(f'[OK] templates.py patched: {path}')
else:
    print('[OK] templates.py already up to date')
PATCH_EOF


# =============================================================================
# Stage 2: runtime — imagen final liviana
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/app

# Runtime deps:
# - curl/unzip: Reflex descarga bun en primer arranque
# - tini: reaping PID 1 (evita zombies de background tasks)
# - sin gcc ni libmysqlclient-dev: aiomysql/PyMySQL son pure-Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copia site-packages + scripts instalados (alembic, reflex, granian, etc.).
COPY --from=builder /install /usr/local

WORKDIR /app

# Usuario no-root para runtime: cualquier RCE queda contenido a UID 1000.
# /app/.web se chownea antes de montar el volumen nombrado para heredar ownership.
RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-create-home --shell /sbin/nologin app \
    && mkdir -p /app/.web \
    && chown -R app:app /app

# Copiar codigo de la aplicacion con ownership correcto.
COPY --chown=app:app . .

# Script de entrada:
# - espera MySQL/Redis (fail-fast)
# - aplica migraciones Alembic (fail-fast)
# - luego arranca Reflex
COPY --chown=app:app scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

# Reflex prod mode: frontend Next.js en :3000, backend Granian (API/WS) en :8000.
# Ambos puertos activos cuando se corre sin --backend-only.
EXPOSE 3000 8000

# Liveness: /api/ping en el backend (puerto 8000), sin tocar DB/Redis.
# Readiness con dependencias (DB + Redis) se mide con /api/health desde NPM.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/ping || exit 1

USER app

# tini como init: limpia procesos zombie del fiscal_retry_loop + propaga SIGTERM.
ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
# CMD final en produccion:
# - --env prod desactiva modo desarrollo/HMR
# - --backend-host 0.0.0.0 permite recibir trafico externo via nginx
CMD ["reflex", "run", "--env", "prod", "--loglevel", "warning", "--backend-host", "0.0.0.0"]
