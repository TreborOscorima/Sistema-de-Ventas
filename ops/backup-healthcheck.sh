#!/usr/bin/env bash
# ops/backup-healthcheck.sh — Verificar salud del sistema de backups
#
# Checks:
#   1. Existe al menos un backup reciente (< MAX_AGE_HOURS)
#   2. El último backup tiene tamaño razonable (> MIN_SIZE_KB)
#   3. El cron de backup está instalado
#   4. El contenedor MySQL está corriendo
#
# Uso:
#   ./ops/backup-healthcheck.sh [directorio_backups]
#
# Exit codes:
#   0 = todo OK
#   1 = al menos un check falló
#
# Variables de entorno (opcionales):
#   MAX_AGE_HOURS    Antigüedad máxima aceptable del último backup (default: 26)
#   MIN_SIZE_KB      Tamaño mínimo aceptable en KB                (default: 10)
#   MYSQL_CONTAINER  Nombre del contenedor MySQL                   (default: tuwayki_mysql)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_DIR="${1:-${PROJECT_DIR}/backups}"
DB_NAME="${DB_NAME:-sistema_ventas}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-tuwayki_mysql}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"
MIN_SIZE_KB="${MIN_SIZE_KB:-10}"

CHECKS_PASSED=0
CHECKS_FAILED=0

pass() { echo "  ✓ $*"; CHECKS_PASSED=$((CHECKS_PASSED + 1)); }
fail() { echo "  ✗ $*"; CHECKS_FAILED=$((CHECKS_FAILED + 1)); }
info() { echo "  → $*"; }

echo "== Backup Health Check =="
echo ""

# 1. Verificar que existe al menos un backup
LATEST=$(find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}*.sql*" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)

if [ -z "$LATEST" ]; then
    fail "No se encontraron backups en ${BACKUP_DIR}"
else
    LATEST_FILE=$(echo "$LATEST" | cut -d' ' -f2-)
    LATEST_NAME=$(basename "$LATEST_FILE")

    # Edad del backup
    LATEST_EPOCH=$(echo "$LATEST" | cut -d'.' -f1)
    NOW_EPOCH=$(date +%s)
    AGE_HOURS=$(( (NOW_EPOCH - LATEST_EPOCH) / 3600 ))

    if [ "$AGE_HOURS" -le "$MAX_AGE_HOURS" ]; then
        pass "Último backup: ${LATEST_NAME} (hace ${AGE_HOURS}h)"
    else
        fail "Último backup tiene ${AGE_HOURS}h de antigüedad (máx: ${MAX_AGE_HOURS}h): ${LATEST_NAME}"
    fi

    # Tamaño del backup
    SIZE_KB=$(( $(stat -c%s "$LATEST_FILE" 2>/dev/null || stat -f%z "$LATEST_FILE" 2>/dev/null) / 1024 ))
    if [ "$SIZE_KB" -ge "$MIN_SIZE_KB" ]; then
        pass "Tamaño del último backup: ${SIZE_KB} KB"
    else
        fail "Backup sospechosamente pequeño: ${SIZE_KB} KB (mín: ${MIN_SIZE_KB} KB)"
    fi

    # Total de backups
    TOTAL=$(find "$BACKUP_DIR" -maxdepth 1 -name "${DB_NAME}*.sql*" | wc -l)
    info "Total backups almacenados: ${TOTAL}"
fi

# 2. Verificar cron
echo ""
if crontab -l 2>/dev/null | grep -q "backup-db.sh"; then
    CRON_LINE=$(crontab -l 2>/dev/null | grep "backup-db.sh" | head -1)
    pass "Cron de backup activo: ${CRON_LINE}"
else
    fail "No se encontró cron para backup-db.sh (verificar: crontab -l)"
fi

# 3. Verificar contenedor MySQL
echo ""
if docker inspect --format='{{.State.Running}}' "$MYSQL_CONTAINER" 2>/dev/null | grep -q true; then
    pass "Contenedor MySQL '${MYSQL_CONTAINER}' corriendo"
else
    fail "Contenedor MySQL '${MYSQL_CONTAINER}' NO está corriendo"
fi

# 4. Verificar S3 offsite (si está configurado)
if [ -n "${S3_BUCKET:-}" ]; then
    echo ""
    if command -v aws >/dev/null 2>&1; then
        S3_COUNT=$(aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}" 2>/dev/null | grep -c "${DB_NAME}" || true)
        if [ "$S3_COUNT" -gt 0 ]; then
            pass "Backups offsite en S3: ${S3_COUNT} archivo(s)"
        else
            fail "S3_BUCKET configurado pero sin backups en s3://${S3_BUCKET}/${S3_PREFIX:-backups/}"
        fi
    else
        fail "S3_BUCKET configurado pero aws CLI no está instalado"
    fi
fi

# Resumen
echo ""
echo "== Resumen =="
echo "  Pasaron: ${CHECKS_PASSED}"
echo "  Fallaron: ${CHECKS_FAILED}"

if [ "$CHECKS_FAILED" -gt 0 ]; then
    echo ""
    echo "RESULTADO: FAIL"
    exit 1
else
    echo ""
    echo "RESULTADO: PASS"
    exit 0
fi
