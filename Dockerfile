# Sistema de Ventas (Reflex + MySQL) - Imagen para producción
FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para PyMySQL y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Script de entrada (espera MySQL/Redis y migraciones)
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Puerto por defecto de Reflex (frontend + backend)
EXPOSE 3000 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["reflex", "run", "--loglevel", "warning", "--backend-host", "0.0.0.0"]
