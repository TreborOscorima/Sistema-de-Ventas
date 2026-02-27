# =============================================================================
# Dockerfile — TUWAYKI Sistema de Ventas (Reflex + MySQL)
#
# Imagen multi-propósito: se usa para las 3 superficies (landing, app, owner)
# diferenciadas por la variable de entorno APP_SURFACE.
#
# Build: docker compose -f docker-compose.prod.yml build
# =============================================================================
FROM python:3.13-slim

# Optimizaciones de Python para contenedores:
# - no generar .pyc (imagen más liviana)
# - logs sin buffer (stdout inmediato)
# - pip sin cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema:
# - gcc/pkg-config: compilación de paquetes Python nativos
# - default-libmysqlclient-dev: conector MySQL
# - curl/unzip: build del frontend Reflex (descarga de bun/node)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python (cache de Docker: solo reinstala si cambia requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Entrypoint: espera MySQL/Redis → migraciones → arranca Reflex
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Reflex expone:
# - 3000: frontend (Next.js compilado)
# - 8000: backend (Starlette/Granian API + WebSocket)
EXPOSE 3000 8000

ENTRYPOINT ["/docker-entrypoint.sh"]

# CMD por defecto: Reflex en modo producción
# --env prod: desactiva HMR/dev mode
# --backend-host 0.0.0.0: acepta conexiones externas
CMD ["reflex", "run", "--env", "prod", "--loglevel", "warning", "--backend-host", "0.0.0.0"]
