#!/usr/bin/env bash
set -e

# Esperar a que MySQL esté listo
echo "Esperando a MySQL en ${DB_HOST:-mysql}:${DB_PORT:-3306}..."
until python -c "
import os, sys
import pymysql
host = os.environ.get('DB_HOST', 'mysql')
port = int(os.environ.get('DB_PORT', 3306))
user = os.environ.get('DB_USER', 'app')
password = os.environ.get('DB_PASSWORD', '')
try:
    pymysql.connect(host=host, port=port, user=user, password=password, connect_timeout=5)
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
  echo "MySQL no disponible, reintentando en 3s..."
  sleep 3
done
echo "MySQL listo."

# Esperar a que Redis esté listo (solo si REDIS_URL está definido)
if [ -n "${REDIS_URL}" ]; then
  echo "Esperando a Redis..."
  until python -c "
import os, sys
import redis
url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
try:
    r = redis.from_url(url)
    r.ping()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    echo "Redis no disponible, reintentando en 2s..."
    sleep 2
  done
  echo "Redis listo."
fi

# Ejecutar migraciones
echo "Ejecutando migraciones Alembic..."
alembic upgrade head
echo "Migraciones aplicadas."

# Arrancar la aplicación
exec "$@"
