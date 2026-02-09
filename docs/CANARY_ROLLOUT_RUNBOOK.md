# Canary Rollout Runbook (10% -> 50% -> 100%)

Objetivo: pasar a producción de forma controlada, con criterios claros de avance y rollback.

## 1. Pre-Gate (obligatorio)

Ejecutar en servidor/entorno de release:

```powershell
.\.venv\Scripts\python scripts/ops_readiness_check.py --require-redis --backup-max-age-hours 24
.\.venv\Scripts\python scripts/smoke_live.py
```

Criterio de pase:
- `ops_readiness_check`: `FAIL=0`
- `smoke_live`: `6 PASS, 0 FAIL`

Si falla cualquier check: **NO liberar**.

## 2. Snapshot de rollback

Antes de publicar:

```powershell
$env:PATH='C:\Program Files\MySQL\MySQL Server 8.0\bin;' + $env:PATH
.\.venv\Scripts\python scripts/backup_db.py --compress --keep 10
```

Guardar:
- Nombre del artefacto/app version desplegada.
- Nombre del backup DB generado.
- Timestamp de inicio de ventana.

## 3. Fase Canary 10%

Acción:
- Enrutamiento 10% a versión nueva.
- 90% permanece en versión estable.

Duración mínima:
- 20 a 30 minutos.

SLO de avance:
- Error rate 5xx < 1%
- p95 latencia estable (sin degradación > 20% vs baseline)
- Sin errores críticos de negocio (login, venta, cobro reserva)

Rollback inmediato si:
- Error 5xx >= 2% por 5 minutos
- Incidente de datos/consistencia
- Bloqueo en login o ventas

## 4. Fase Canary 50%

Acción:
- Subir tráfico a 50%.

Duración mínima:
- 30 a 45 minutos.

SLO de avance:
- Mismos criterios de fase 10%.
- No crecimiento sostenido de errores en logs de app.

Rollback inmediato con los mismos gatillos.

## 5. Fase 100%

Acción:
- Subir tráfico a 100%.

Monitoreo reforzado:
- 60 minutos continuos.

Post-check:
- `scripts/ops_readiness_check.py --require-redis`
- Smoke funcional rápido (mínimo login + venta + cobro reserva).

## 6. Procedimiento de rollback

### 6.1 App rollback (primario, inmediato)

1. Enrutar 100% del tráfico a la versión previa estable.
2. Verificar recuperación de métricas (5-10 min).
3. Comunicar incidente y congelar despliegues.

### 6.2 DB rollback (solo si es imprescindible)

Regla:
- Preferir corrección forward-only.
- Restaurar DB solo ante corrupción severa.

Si se requiere restaurar:

```powershell
$env:PATH='C:\Program Files\MySQL\MySQL Server 8.0\bin;' + $env:PATH
.\.venv\Scripts\python scripts/backup_db.py --list
.\.venv\Scripts\python scripts/backup_db.py --restore <archivo_backup.sql.gz>
```

Nota:
- Restaurar sobrescribe datos; validar ventana de pérdida aceptable (RPO).

## 7. Checklist de cierre GO

- [ ] `ops_readiness_check` estricto en verde.
- [ ] Smoke funcional en verde.
- [ ] Backup reciente validado.
- [ ] Canary 10% y 50% sin incidentes.
- [ ] Monitoreo 100% estable durante 60 min.
- [ ] Runbook de rollback comunicado al equipo.
