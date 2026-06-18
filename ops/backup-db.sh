#!/usr/bin/env bash
# ops/backup-db.sh — Backup MySQL via Docker exec
#
# Uso:
#   ./ops/backup-db.sh [directorio_destino]
#
# Variables de entorno (todas opcionales — se leen desde .env si está disponible):
#   BACKUP_DIR       Directorio donde se guardan los dumps    (default: ./backups)
#   DB_NAME          Nombre de la base de datos               (default: sistema_ventas)
#   MYSQL_CONTAINER  Nombre del contenedor MySQL              (default: tuwayki_mysql)
#   KEEP_DAYS        Días de retención antes de rotar         (default: 30)
#
# Instalar en cron (como root o el usuario que ejecuta Docker):
#   0 2 * * * /opt/tuwayki/ops/backup-db.sh /opt/tuwayki/backups >> /var/log/tuwayki-backup.log 2>&1

set -euo pipefail

# Cargar variables del .env si existe en el directorio padre del script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "${PROJECT_DIR}/.env" ]; then
    # Exportar solo las vars de DB (no sobreescribir las ya definidas en entorno)
    set -o allexport
    # shellcheck source=/dev/null
    source "${PROJECT_DIR}/.env"
    set +o allexport
fi

BACKUP_DIR="${1:-${BACKUP_DIR:-${PROJECT_DIR}/backups}}"
DB_NAME="${DB_NAME:-sistema_ventas}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-tuwayki_mysql}"
KEEP_DAYS="${KEEP_DAYS:-30}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "Iniciando backup de '${DB_NAME}' desde contenedor '${MYSQL_CONTAINER}'..."

# Verify container is running
if ! docker inspect --format='{{.State.Running}}' "$MYSQL_CONTAINER" 2>/dev/null | grep -q true; then
    log "ERROR: El contenedor '${MYSQL_CONTAINER}' no está corriendo."
    exit 1
fi

# Dump con --single-transaction (non-blocking para InnoDB) y --routines/triggers
docker exec "$MYSQL_CONTAINER" \
    sh -c 'MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysqldump -u root \
        --single-transaction \
        --routines \
        --triggers \
        --add-drop-table \
        --default-character-set=utf8mb4 \
        '"${DB_NAME}" \
    | gzip -9 > "$OUTFILE"

SIZE=$(du -h "$OUTFILE" | cut -f1)
log "Backup completado: $(basename "$OUTFILE") (${SIZE})"

# Rotación: eliminar archivos más antiguos que KEEP_DAYS días
DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}_*.sql.gz" -mtime +"${KEEP_DAYS}" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Rotación: ${DELETED} backup(s) eliminado(s) (>$KEEP_DAYS días)"
fi

# Mostrar backups actuales
TOTAL=$(find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}_*.sql.gz" | wc -l)
log "Total backups almacenados: ${TOTAL}"
