# Sistema de Ventas (Reflex + MySQL) - Imagen para producción
FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema: PyMySQL, compilación y Reflex (Bun/unzip para frontend)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Script de entrada (espera MySQL/Redis y migraciones)
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puerto por defecto de Reflex (frontend 3000 + backend 8000)
EXPOSE 3000 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
# Modo producción: build optimizado del frontend, sin HMR ni dev server
CMD ["reflex", "run", "--env", "prod", "--loglevel", "warning", "--backend-host", "0.0.0.0"]
