#!/usr/bin/env bash
# Entry point de produccion para el contenedor app.
# Objetivo:
# 1) Esperar infraestructura dependiente (MySQL y Redis)
# 2) Ejecutar migraciones de esquema
# 3) Arrancar proceso principal (Reflex)
set -euo pipefail

# Logger simple con prefijo para leer facil en docker logs
log() {
  printf '[entrypoint] %s\n' "$*"
}

# Espera activa de MySQL con reintentos controlados.
# Variables:
# - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
# - DB_WAIT_MAX_ATTEMPTS, DB_WAIT_SLEEP_SECONDS
wait_for_mysql() {
  local host="${DB_HOST:-localhost}"
  local port="${DB_PORT:-3306}"
  local user="${DB_USER:-root}"
  local max_attempts="${DB_WAIT_MAX_ATTEMPTS:-60}"
  local sleep_seconds="${DB_WAIT_SLEEP_SECONDS:-2}"

  log "Esperando MySQL en ${host}:${port}..."
  # Se usa Python para validar conexion real + SELECT 1.
  python - "$host" "$port" "$user" "$max_attempts" "$sleep_seconds" <<'PY'
import sys
import time
import pymysql

host = sys.argv[1]
port = int(sys.argv[2])
user = sys.argv[3]
max_attempts = int(sys.argv[4])
sleep_seconds = float(sys.argv[5])

password = __import__("os").environ.get("DB_PASSWORD", "")
db_name = __import__("os").environ.get("DB_NAME", "")

for attempt in range(1, max_attempts + 1):
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name or None,
            connect_timeout=3,
            read_timeout=3,
            write_timeout=3,
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        print(f"MySQL listo (attempt={attempt}).")
        raise SystemExit(0)
    except Exception as exc:
        if attempt == max_attempts:
            print(f"MySQL no disponible tras {max_attempts} intentos: {exc}")
            raise SystemExit(1)
        time.sleep(sleep_seconds)
PY
}

# Espera opcional de Redis.
# Si REDIS_URL no existe, se omite sin fallar.
# Variables:
# - REDIS_URL
# - REDIS_WAIT_MAX_ATTEMPTS, REDIS_WAIT_SLEEP_SECONDS
wait_for_redis() {
  local redis_url="${REDIS_URL:-}"
  if [[ -z "${redis_url}" ]]; then
    log "REDIS_URL no definido. Se omite espera de Redis."
    return 0
  fi

  local max_attempts="${REDIS_WAIT_MAX_ATTEMPTS:-40}"
  local sleep_seconds="${REDIS_WAIT_SLEEP_SECONDS:-2}"
  log "Esperando Redis (${redis_url})..."
  # Verificacion TCP para asegurar que el servicio acepta conexiones.
  python - "$redis_url" "$max_attempts" "$sleep_seconds" <<'PY'
import sys
import time
from urllib.parse import urlparse
import socket

redis_url = sys.argv[1]
max_attempts = int(sys.argv[2])
sleep_seconds = float(sys.argv[3])

parsed = urlparse(redis_url)
host = parsed.hostname or "localhost"
port = int(parsed.port or 6379)

for attempt in range(1, max_attempts + 1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3.0)
    try:
        sock.connect((host, port))
        sock.close()
        print(f"Redis listo (attempt={attempt}).")
        raise SystemExit(0)
    except Exception as exc:
        sock.close()
        if attempt == max_attempts:
            print(f"Redis no disponible tras {max_attempts} intentos: {exc}")
            raise SystemExit(1)
        time.sleep(sleep_seconds)
PY
}

# Ejecuta migraciones Alembic antes de iniciar la app.
# Puede deshabilitarse con SKIP_MIGRATIONS=1.
run_migrations() {
  if [[ "${SKIP_MIGRATIONS:-0}" == "1" ]]; then
    log "SKIP_MIGRATIONS=1, se omiten migraciones."
    return 0
  fi

  if [[ -f "alembic.ini" ]]; then
    log "Ejecutando migraciones: alembic upgrade head"
    alembic upgrade head
    return 0
  fi

  log "alembic.ini no encontrado, se omiten migraciones."
}

# Flujo principal de arranque del contenedor.
main() {
  # 1) Esperar dependencias
  wait_for_mysql
  wait_for_redis
  # 2) Alinear esquema
  run_migrations

  # 3) Delegar al comando final del contenedor (CMD)
  log "Iniciando aplicación: $*"
  exec "$@"
}

main "$@"
