# Handoff a infraestructura — tareas para el configurador de AWS (P3)

> Resumen ejecutivo de lo que quedó **listo en el código** y lo que falta **hacer en el servidor / AWS**
> para completar la Fase P3 (escalado + infraestructura). Fecha: 2026-07-27.
> Sistema: **TUWAYKISHOP / Sistema de Ventas** (`sys.tuwayki.app`, `admin.tuwayki.app`, `tuwayki.app`).

## Contexto en 30 segundos

- El servidor de prod es **compartido** (corre Ventas + Food + Clínicas + otros). Datos aislados (cada
  sistema su MySQL) pero **RAM/CPU/IO compartidos**.
- Ya se optimizó el sistema **sin agregar recursos**: índices de BD (Fase P1, en prod) y tuning de
  MySQL (Fase P2/paso 2, en prod). Eso mejora sin competir con los otros sistemas.
- Todo lo que sigue es **infra**: decide/ejecuta el configurador. Nada rompe si no se hace (el sistema
  funciona hoy); son mejoras de **resiliencia y capacidad**.

---

## ⓪ DATO QUE NECESITAMOS PRIMERO (gatilla varias decisiones)

**Specs de la instancia EC2 donde corre Ventas:**
```bash
# tipo de instancia y RAM total:
curl -s http://169.254.169.254/latest/meta-data/instance-type    # ej: t3.medium
free -h                                                            # RAM total y libre
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'
```
Con eso definimos si hay margen para réplicas locales o si conviene ir a servicios gestionados (RDS).
Umbral: agregar una 2ª réplica de Ventas pide **~1 GB libre**; una read-replica local, otro tanto.

---

## ① Backups automáticos — VERIFICAR (prioridad alta, riesgo si falta)

El tooling existe (`ops/backup-db.sh`: dump diario + retención + copia a S3). Falta **confirmar que el
cron está instalado** en el server:
```bash
cd <APP_DIR>            # ej: /home/ubuntu/sist-ventas-trebor
./ops/backup-healthcheck.sh        # 0 = OK; 1 = falta algo (lo dice)
crontab -l | grep backup-db.sh     # ¿está el cron?
```
Si **no** está el cron, instalarlo (dump diario 02:00):
```bash
( crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/ops/backup-db.sh $(pwd)/backups >> /var/log/tuwayki-backup.log 2>&1" ) | crontab -
```
> Requiere que el `.env` tenga `S3_BUCKET`/`S3_PREFIX` si se quiere copia offsite (recomendado).

---

## ② Monitoreo Tier 1 — uptime externo (prioridad alta, costo RAM = 0)

Alta señal, cero costo en el server. Crear en un servicio **hosted** (UptimeRobot / healthchecks.io /
Better Uptime) **3 monitores HTTP**, uno por superficie:
- `https://sys.tuwayki.app/api/health`
- `https://admin.tuwayki.app/api/health`
- `https://tuwayki.app/api/health`

Config de cada monitor: intervalo 1–5 min, y **condición de OK = el body contiene** `"status":"ok"` **y**
`"db":{"ok":true`. Así una caída de BD (aunque el HTTP dé 200) también alerta. Notificación a
email/Telegram/Slack. **Esto solo ya cubre "¿está arriba? ¿la BD responde?".**

---

## ③ Réplicas del POS + balanceo sticky — SOLO si hay RAM (mejora de capacidad)

Ya está **automatizado en el código**; activarlo es una variable + config de NPM.

1. **Confirmar RAM** (dato ⓪): hace falta ~1 GB libre para `tuwayki_sys_2` (límite 1 GB / 1 CPU). Si la
   instancia es de 2 GB (t3.small), **NO activar** — subir la instancia primero.
2. **Activar el toggle** (lo hace el dueño del repo en GitHub, no en el server): *Settings → Secrets and
   variables → Actions → Variables →* `SCALE_SYS = 1`. Luego disparar un deploy. Sube `tuwayki_sys_2`.
3. **NPM — balanceo sticky** (configurador, en la UI de Nginx Proxy Manager): en el Proxy Host de
   `sys.tuwayki.app` → *Advanced → Custom Nginx Configuration*:
   ```nginx
   upstream tuwayki_sys_pool {
       ip_hash;                    # sticky por IP: cada cliente siempre a la misma réplica (socket.io)
       server tuwayki_sys:3000;
       server tuwayki_sys_2:3000;
       keepalive 32;
   }
   ```
   y apuntar el forwarding del Proxy Host a `http://tuwayki_sys_pool` (mantener los headers
   `Upgrade`/`Connection` de websocket que NPM ya setea). Guardar → NPM recarga.
   > Ambas réplicas deben estar en la red `nginx-proxy-manager_default` (ya lo están por config).

**Rollback**: `SCALE_SYS` a vacío + quitar `tuwayki_sys_2` del upstream en NPM. Detalle:
`docs/P3_STEP3_REPLICAS_RUNBOOK.md`.

---

## ④ Réplica de LECTURA para reportes — recomendado FUERA de la caja (mejora de carga)

El código ya rutea los reportes pesados a una réplica de lectura **si se configura** (`DB_READ_URL`);
default = primario (sin cambios). Falta **provisionar la réplica**. En host compartido, **NO co-locarla**
(le roba RAM a los otros sistemas). Opciones, mejor primero:

- **A. AWS RDS read replica** (recomendada): migrar/replicar el MySQL de Ventas a RDS y crear una read
  replica gestionada (vive fuera de la caja → 0 RAM local). Luego en el `.env`:
  ```
  DB_READ_URL=mysql+pymysql://<user>:<pass>@<rds-read-endpoint>:3306/sistema_ventas?charset=utf8mb4
  ```
  y redeploy. Los reportes pasan a leer de la réplica automáticamente.
- **B. MySQL en una instancia aparte** con replicación nativa (binlog/GTID), `read_only=ON`. En el
  `.env`: `DB_READ_HOST=<ip-replica>`.
- **C. Co-locada** — desaconsejada en host compartido.

**Verificar** tras activar: generar un reporte grande y ver que la carga cae en el primario (con el
monitoreo del paso ⑤). Detalle: `docs/P3_STEP4_READ_REPLICA_RUNBOOK.md`.

---

## ⑤ Monitoreo Tier 2 — métricas Prometheus/Grafana (opcional, si hay RAM ~500–800 MB)

Stack como código, opt-in. Da métricas históricas de host/contenedores/MySQL + 7 alertas (incl. RAM
del host, contenedor cerca de OOM, conexiones MySQL). **En host chico, NO** (usar solo Tier 1) o
correrlo en un host de monitoreo aparte.

Pasos (server):
1. Usuario MySQL para el exporter (una vez):
   ```sql
   CREATE USER 'exporter'@'%' IDENTIFIED BY '<pass>' WITH MAX_USER_CONNECTIONS 3;
   GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'%';
   FLUSH PRIVILEGES;
   ```
2. `.env`: `GRAFANA_ADMIN_PASSWORD=...`, `MYSQL_EXPORTER_PASSWORD=<el de arriba>`.
3. Levantar:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d \
     prometheus grafana node_exporter cadvisor mysqld_exporter blackbox_exporter
   ```
4. Grafana en `127.0.0.1:3009` (túnel SSH o Proxy Host en NPM con auth). Importar dashboards por ID:
   **1860** (node), **14282** (cAdvisor), **7362** (MySQL). Detalle: `docs/P3_STEP5_MONITORING_RUNBOOK.md`.

---

## Orden recomendado

1. **⓪ Specs** (5 min) → nos dice qué es viable.
2. **① Backups** (verificar/instalar cron) — resiliencia, sin costo.
3. **② Uptime Tier 1** — alerta básica, sin costo.
4. **④ Read-replica RDS** — la mejora de mayor impacto para reportes **sin robar RAM local**.
5. **③ Réplicas del POS** — solo si la RAM alcanza (o tras subir la instancia).
6. **⑤ Monitoreo Tier 2** — cuando haya margen o host aparte.

> **Todo lo del código ya está mergeado en `main`.** Cada activación de acá es reversible y opcional; el
> sistema opera hoy sin ninguna de ellas. Dudas técnicas puntuales: los runbooks `docs/P3_STEP*.md`.
