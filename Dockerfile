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


# =============================================================================
# Stage 2: runtime — imagen final liviana
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

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
RUN chmod +x /docker-entrypoint.sh

# Puertos de Reflex (frontend 3000 + backend 8000). >1024 = no requiere root.
EXPOSE 3000 8000

# Liveness check: /api/ping responde sin tocar DB/Redis → ideal para Docker.
# Readiness con dependencias se mide en /api/health desde el reverse proxy (NPM).
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/ping || exit 1

USER app

# tini como init: limpia procesos zombie del fiscal_retry_loop + propaga SIGTERM.
ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
# CMD final en produccion:
# - --env prod desactiva modo desarrollo/HMR
# - --backend-host 0.0.0.0 permite recibir trafico externo via nginx
CMD ["reflex", "run", "--env", "prod", "--loglevel", "warning", "--backend-host", "0.0.0.0"]
