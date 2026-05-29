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

# Workaround: Rolldown (Vite 6) tiene un bug en su minificador que genera
# código inválido en @emotion/styled (usada por recharts Tooltip) →
# TypeError: t is not a function en producción. Fix: parchear el template
# Python de reflex_base que genera vite.config.js para forzar esbuild como
# minificador. Se hace aquí (build stage) para que el runtime lo herede.
RUN python3 -c "
import glob, sys
files = glob.glob('/install/lib/python*/site-packages/reflex_base/compiler/templates.py')
if not files:
    print('WARNING: reflex_base/compiler/templates.py not found — skipping patch')
    sys.exit(0)
tmpl = files[0]
content = open(tmpl).read()
OLD = '    sourcemap: {\"true\" if sourcemap is True else \"false\" if sourcemap is False else repr(sourcemap)},'
NEW = OLD + '\n    minify: \"esbuild\",'
if 'minify: \"esbuild\"' in content:
    print('[SKIP]  templates.py already patched')
elif OLD in content:
    open(tmpl, 'w').write(content.replace(OLD, NEW, 1))
    print('[PATCH] reflex_base/compiler/templates.py: minify → esbuild')
else:
    print('ERROR: pattern not found in templates.py', file=sys.stderr)
    sys.exit(1)
"


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
