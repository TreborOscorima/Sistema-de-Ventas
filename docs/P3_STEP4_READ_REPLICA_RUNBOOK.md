# P3 — Paso 4: réplica de lectura para reportes (runbook)

> Fase P3 §3.4 (`docs/P3_HORIZONTAL_SCALING_DESIGN.md`). Descarga los **reportes pesados** del MySQL
> primario del POS enviándolos a una **réplica de solo-lectura**.

## Estado (2026-07-27)

- **Ruteo de lectura en la app: HECHO** (repo, host-agnóstico). `app/utils/db_read.py` expone
  `read_session()`; el generador de reportes (`app/states/report_state.py::_run_report_sync`) ya la usa.
  **Default = primario** → sin réplica configurada, comportamiento idéntico al actual (0 overhead).
  El aislamiento multi-tenant se preserva (listeners de `tuwayki_core` sobre la clase `Session`).
- **Provisión de la réplica: infra** (tu configurador) — pendiente. Ver abajo.

## ⚠️ Contexto: servidor COMPARTIDO

El host de prod corre varios sistemas (Ventas + Food + Clínicas + otros). Los **datos** están aislados
(cada uno su contenedor MySQL) pero la **RAM/CPU/IO** se comparten. Por eso, **una réplica de lectura
co-locada NO es lo recomendado**: otro contenedor MySQL (~400 MB–1 GB) le roba recursos a los demás
sistemas. **Recomendado: réplica FUERA de la caja.**

## Opciones de provisión (de mejor a peor para tu caso)

### A. AWS RDS read replica (recomendada) 🥇
Migrar (o replicar) el MySQL de Ventas a **RDS** y crear una **read replica** gestionada. Vive fuera del
host compartido → **0 RAM local**, replicación y failover gestionados por AWS.
- Configurar en la app: `DB_READ_URL=mysql+pymysql://user:pass@<rds-read-endpoint>:3306/sistema_ventas?charset=utf8mb4`
- Costo: instancia RDS (primario + réplica).

### B. Réplica en una instancia EC2 aparte 🥈
Un 2º MySQL en otra instancia chica, con **replicación nativa** (binlog/GTID) desde el primario.
Aislado del host compartido, pero lo administrás vos.
- App: `DB_READ_HOST=<ip-instancia-replica>` (usa DB_USER/DB_PASSWORD/DB_NAME del primario).

### C. Réplica co-locada (solo si sobra RAM) 🥉
Un 2º contenedor MySQL en el mismo host con replicación. **Desaconsejada en host compartido** (compite
con Food/Clínicas). Si igual se hiciera, sumarla al `docker-compose` con `--server-id` distinto,
`read_only=ON`, y `DB_READ_HOST=<contenedor-replica>`.

## Activar (una vez que exista la réplica)

1. Confirmar que la réplica **replica** desde el primario (lag bajo) y es `read_only`.
2. En `.env`: setear `DB_READ_URL` (opción A) **o** `DB_READ_HOST` (opción B/C).
3. Redeploy (el ruteo toma la réplica automáticamente; no hay cambio de código).
4. Verificar: generar un reporte grande y ver en la réplica que llega la query (o en el primario que
   **ya no** llega). Con el monitoreo (paso 5), comparar carga del primario antes/después.

**Rollback**: vaciar `DB_READ_URL`/`DB_READ_HOST` en `.env` + redeploy → los reportes vuelven al primario.

## Consideraciones

- **Lag de replicación**: los reportes toleran datos con segundos de atraso (no son transaccionales en
  vivo). Si algún reporte necesita datos al instante, dejarlo en el primario (no rutearlo).
- **Sólo lectura**: `read_session()` es exclusivamente para SELECTs de reportes. Las escrituras siguen
  por `rx.session()` (primario). Una réplica es `read_only` → un intento de escritura fallaría.
- **Ampliar el ruteo**: hoy sólo `_run_report_sync` usa `read_session()`. Otros paths de solo-lectura
  pesados (dashboard, exportaciones) pueden migrarse igual (`with read_session() as session:`), siempre
  que NO escriban.
