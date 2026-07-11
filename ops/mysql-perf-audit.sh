#!/usr/bin/env bash
# ops/mysql-perf-audit.sh — Auditoría de rendimiento MySQL (Docker)
#
# Ejecuta desde el host contra el contenedor tuwayki_mysql.
# Reporta: slow queries, índices sugeridos, estado del buffer pool,
# tablas sin índice en columnas de filtro frecuente, y métricas clave.
#
# Uso:
#   ./ops/mysql-perf-audit.sh
#   ./ops/mysql-perf-audit.sh --container tuwayki_mysql
#
# Agregar al cron mensual:
#   0 6 1 * * /opt/tuwayki/ops/mysql-perf-audit.sh >> /var/log/tuwayki-perf-audit.log 2>&1

set -euo pipefail

MYSQL_CONTAINER="${1:-tuwayki_mysql}"

mysql_exec() {
    docker exec "$MYSQL_CONTAINER" \
        sh -c 'MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysql -u root -N -e "'"$1"'"' 2>/dev/null
}

mysql_exec_db() {
    docker exec "$MYSQL_CONTAINER" \
        sh -c 'MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" mysql -u root -N "$MYSQL_DATABASE" -e "'"$1"'"' 2>/dev/null
}

echo "═══════════════════════════════════════════════════════════"
echo "  MySQL Performance Audit — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "═══════════════════════════════════════════════════════════"

# Verificar contenedor
if ! docker inspect --format='{{.State.Running}}' "$MYSQL_CONTAINER" 2>/dev/null | grep -q true; then
    echo "ERROR: contenedor '$MYSQL_CONTAINER' no está corriendo."
    exit 1
fi

echo ""
echo "── 1. InnoDB Buffer Pool ──────────────────────────────────"
echo ""
BP_SIZE=$(mysql_exec "SELECT @@innodb_buffer_pool_size / 1024 / 1024;")
BP_PAGES_DATA=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Innodb_buffer_pool_pages_data';" 2>/dev/null || echo "N/A")
BP_PAGES_FREE=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Innodb_buffer_pool_pages_free';" 2>/dev/null || echo "N/A")
BP_READ_REQUESTS=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Innodb_buffer_pool_read_requests';" 2>/dev/null || echo "N/A")
BP_READS=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Innodb_buffer_pool_reads';" 2>/dev/null || echo "N/A")

echo "  Buffer pool size:   ${BP_SIZE} MB"
echo "  Pages data/free:    ${BP_PAGES_DATA} / ${BP_PAGES_FREE}"
if [ "$BP_READ_REQUESTS" != "N/A" ] && [ "$BP_READS" != "N/A" ] && [ "$BP_READ_REQUESTS" -gt 0 ] 2>/dev/null; then
    HIT_RATE=$(echo "scale=2; (1 - $BP_READS / $BP_READ_REQUESTS) * 100" | bc 2>/dev/null || echo "N/A")
    echo "  Hit rate:           ${HIT_RATE}%"
    if [ "$BP_PAGES_FREE" != "N/A" ] && [ "$BP_PAGES_FREE" -lt 100 ] 2>/dev/null; then
        echo "  ⚠ Pocas páginas libres — considerar aumentar innodb_buffer_pool_size"
    fi
fi

echo ""
echo "── 2. Slow Query Log ──────────────────────────────────────"
echo ""
SLOW_ON=$(mysql_exec "SELECT @@slow_query_log;")
LONG_QT=$(mysql_exec "SELECT @@long_query_time;")
echo "  Slow query log:     $([ "$SLOW_ON" = "1" ] && echo "ON" || echo "OFF")"
echo "  Long query time:    ${LONG_QT}s"

SLOW_COUNT=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Slow_queries';" 2>/dev/null || echo "0")
echo "  Slow queries total: ${SLOW_COUNT}"

echo ""
echo "── 3. Tablas más grandes ──────────────────────────────────"
echo ""
mysql_exec_db "
SELECT
    TABLE_NAME AS tbl,
    TABLE_ROWS AS rows_est,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_mb,
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS idx_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY DATA_LENGTH DESC
LIMIT 15;
" | while IFS=$'\t' read -r tbl rows data idx; do
    printf "  %-30s %8s rows  %6s MB data  %6s MB idx\n" "$tbl" "$rows" "$data" "$idx"
done

echo ""
echo "── 4. Tablas sin índice en company_id (multi-tenant) ──────"
echo ""
mysql_exec_db "
SELECT t.TABLE_NAME
FROM information_schema.TABLES t
JOIN information_schema.COLUMNS c
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_SCHEMA = DATABASE()
  AND t.TABLE_TYPE = 'BASE TABLE'
  AND c.COLUMN_NAME = 'company_id'
  AND NOT EXISTS (
    SELECT 1 FROM information_schema.STATISTICS s
    WHERE s.TABLE_SCHEMA = t.TABLE_SCHEMA
      AND s.TABLE_NAME = t.TABLE_NAME
      AND s.COLUMN_NAME = 'company_id'
      AND s.SEQ_IN_INDEX = 1
  )
ORDER BY t.TABLE_NAME;
" | while read -r tbl; do
    echo "  ⚠ $tbl — company_id sin índice como primer campo"
done
MISSING=$(mysql_exec_db "
SELECT COUNT(*) FROM (
SELECT t.TABLE_NAME
FROM information_schema.TABLES t
JOIN information_schema.COLUMNS c
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_SCHEMA = DATABASE()
  AND t.TABLE_TYPE = 'BASE TABLE'
  AND c.COLUMN_NAME = 'company_id'
  AND NOT EXISTS (
    SELECT 1 FROM information_schema.STATISTICS s
    WHERE s.TABLE_SCHEMA = t.TABLE_SCHEMA
      AND s.TABLE_NAME = t.TABLE_NAME
      AND s.COLUMN_NAME = 'company_id'
      AND s.SEQ_IN_INDEX = 1
  )
) sub;
")
[ "$MISSING" = "0" ] && echo "  ✓ Todas las tablas con company_id tienen índice"

echo ""
echo "── 5. Índices redundantes / duplicados ────────────────────"
echo ""
mysql_exec_db "
SELECT
    s1.TABLE_NAME,
    s1.INDEX_NAME AS idx_redundante,
    s2.INDEX_NAME AS cubierto_por
FROM information_schema.STATISTICS s1
JOIN information_schema.STATISTICS s2
  ON s1.TABLE_SCHEMA = s2.TABLE_SCHEMA
  AND s1.TABLE_NAME = s2.TABLE_NAME
  AND s1.COLUMN_NAME = s2.COLUMN_NAME
  AND s1.SEQ_IN_INDEX = s2.SEQ_IN_INDEX
  AND s1.INDEX_NAME != s2.INDEX_NAME
  AND s1.SEQ_IN_INDEX = 1
WHERE s1.TABLE_SCHEMA = DATABASE()
  AND s1.NON_UNIQUE = 1
  AND s2.NON_UNIQUE = 0
ORDER BY s1.TABLE_NAME, s1.INDEX_NAME
LIMIT 20;
" | while IFS=$'\t' read -r tbl idx covered; do
    printf "  %-25s %-30s cubierto por %s\n" "$tbl" "$idx" "$covered"
done 2>/dev/null || echo "  ✓ No se detectaron índices redundantes"

echo ""
echo "── 6. Conexiones y threads ────────────────────────────────"
echo ""
MAX_CONN=$(mysql_exec "SELECT @@max_connections;")
CURR_CONN=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Threads_connected';" 2>/dev/null || echo "N/A")
MAX_USED=$(mysql_exec "SELECT variable_value FROM performance_schema.global_status WHERE variable_name = 'Max_used_connections';" 2>/dev/null || echo "N/A")
echo "  max_connections:    ${MAX_CONN}"
echo "  Threads connected:  ${CURR_CONN}"
echo "  Max used (peak):    ${MAX_USED}"

echo ""
echo "── 7. Recomendaciones ─────────────────────────────────────"
echo ""
if [ "$BP_PAGES_FREE" != "N/A" ] && [ "$BP_PAGES_FREE" -lt 100 ] 2>/dev/null; then
    echo "  → Aumentar innodb_buffer_pool_size (actual: ${BP_SIZE}MB)"
    echo "    En docker-compose.yml: --innodb_buffer_pool_size=512M"
fi
if [ "$SLOW_ON" != "1" ]; then
    echo "  → Activar slow query log: --slow_query_log=1"
fi
if [ "$(echo "$LONG_QT > 1" | bc 2>/dev/null)" = "1" ]; then
    echo "  → Bajar long_query_time a 1s para capturar más queries"
fi
if [ "$MISSING" != "0" ] 2>/dev/null; then
    echo "  → Agregar índices en company_id para las tablas reportadas arriba"
fi
echo "  → Ejecutar mensualmente: bash ops/mysql-perf-audit.sh"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Auditoría completada"
echo "═══════════════════════════════════════════════════════════"
