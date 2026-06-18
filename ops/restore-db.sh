#!/usr/bin/env bash
# ops/restore-db.sh — Restaurar MySQL desde backup comprimido
#
# Uso:
#   ./ops/restore-db.sh <archivo.sql.gz>
#
# Variables de entorno (opcionales):
#   DB_NAME          Nombre de la base de datos               (default: sistema_ventas)
#   MYSQL_CONTAINER  Nombre del contenedor MySQL              (default: tuwayki_mysql)
#
# ADVERTENCIA: Sobreescribe la base de datos por completo.
# Detener el/los contenedores de la aplicación antes de restaurar:
#   docker compose stop landing sys admin

set -euo pipefail

FILE="${1:-}"
DB_NAME="${DB_NAME:-sistema_ventas}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-tuwayki_mysql}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

if [ -z "$FILE" ]; then
    echo "Uso: $0 <archivo.sql.gz>"
    echo ""
    echo "Backups disponibles en ./backups/:"
    find "./backups" -maxdepth 1 -name "${DB_NAME}_*.sql.gz" -printf "  %f\n" 2>/dev/null | sort || echo "  (directorio ./backups no encontrado)"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    log "ERROR: archivo no encontrado: $FILE"
    exit 1
fi

# Verificar que el archivo es un gzip válido
if ! gzip -t "$FILE" 2>/dev/null; then
    log "ERROR: el archivo no es un gzip válido: $FILE"
    exit 1
fi

if ! docker inspect --format='{{.State.Running}}' "$MYSQL_CONTAINER" 2>/dev/null | grep -q true; then
    log "ERROR: El contenedor '${MYSQL_CONTAINER}' no está corriendo."
    exit 1
fi

SIZE=$(du -h "$FILE" | cut -f1)
log "Archivo: $(basename "$FILE") (${SIZE})"
log "Destino: DB '${DB_NAME}' en contenedor '${MYSQL_CONTAINER}'"
echo ""
echo "ADVERTENCIA: Esto SOBREESCRIBIRÁ la base de datos '${DB_NAME}' por completo."
echo "Asegúrate de haber detenido los contenedores de la aplicación primero."
echo ""
printf "¿Continuar? [s/N]: "
read -r CONFIRM
if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
    echo "Cancelado."
    exit 0
fi

log "Restaurando ${DB_NAME}..."
zcat "$FILE" | docker exec -i "$MYSQL_CONTAINER" \
    sh -c 'MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysql -u root '"${DB_NAME}"

log "Restauración completada exitosamente."
log "Volver a iniciar la aplicación: docker compose start"
