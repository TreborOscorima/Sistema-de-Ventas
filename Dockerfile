# Sistema de Ventas (Reflex + MySQL) - Imagen para produccion
# Esta imagen esta orientada a despliegue cloud con runtime de Reflex en modo prod.
FROM python:3.11-slim

# Variables recomendadas para contenedores Python:
# - no generar .pyc
# - logs en stdout sin buffer
# - pip sin cache para imagen mas liviana
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Dependencias del sistema necesarias para:
# - conectores MySQL/PyMySQL
# - compilacion de paquetes Python (gcc/pkg-config)
# - build frontend de Reflex (curl/unzip)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos primero requirements para aprovechar cache de Docker
# (solo reinstala dependencias si requirements cambia)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo de la aplicacion
COPY . .

# Script de entrada:
# - espera MySQL/Redis
# - aplica migraciones Alembic
# - luego arranca Reflex
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puertos de Reflex (frontend 3000 + backend 8000)
EXPOSE 3000 8000

# ENTRYPOINT mantiene el pre-arranque obligatorio del sistema
ENTRYPOINT ["/docker-entrypoint.sh"]
# CMD final en produccion:
# - --env prod desactiva modo desarrollo/HMR
# - --backend-host 0.0.0.0 permite recibir trafico externo via nginx
CMD ["reflex", "run", "--env", "prod", "--loglevel", "warning", "--backend-host", "0.0.0.0"]
