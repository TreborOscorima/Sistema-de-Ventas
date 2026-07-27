# P3 — Paso 5: monitoreo + alertas (runbook)

> Fase P3 §3.5 (`docs/P3_HORIZONTAL_SCALING_DESIGN.md`). El sistema ya tiene health interno
> (`/api/health` con db+redis, `/api/ping`) y `ops/backup-healthcheck.sh`. Falta **observabilidad
> externa + alertas**. Se ofrece en **2 tiers** para respetar la RAM del host.

## Tier 1 — Uptime externo (hacer YA, costo de RAM = 0)

Lo más importante y barato: un monitor **hosted** que pinguea las URLs públicas y alerta si algo cae.
No consume RAM del server. Servicios gratuitos: UptimeRobot, Better Uptime, healthchecks.io.

Configurar 3 monitores HTTP(s), cada uno con:
- URL: `https://sys.tuwayki.app/api/health` (y `admin.tuwayki.app`, `tuwayki.app`).
- Intervalo: 1–5 min.
- **Keyword/condición de OK**: que el body contenga `"status":"ok"` **y** `"db":{"ok":true`. Así una
  caída de BD (aunque el HTTP responda 200) dispara alerta.
- Notificación: email / Telegram / Slack.

Esto cubre el 80% del valor (¿está prod arriba? ¿la BD responde?) sin tocar el server.

## Tier 2 — Métricas + alertas con Prometheus (opt-in, si hay RAM)

Stack como código: `docker-compose.monitoring.yml` + `ops/monitoring/`. Da métricas históricas de
host, contenedores y MySQL, con reglas de alerta. **Cuesta ~500–800 MB de RAM** → sólo si el host
tiene margen (o correrlo en un host de monitoreo aparte).

### Componentes
| Servicio | Qué mide | Límite |
|---|---|---|
| `prometheus` | scrape + storage (retención 7d / 1GB) | 400M |
| `grafana` | dashboards (localhost:3009) | 200M |
| `node_exporter` | CPU/RAM/disco del host | 64M |
| `cadvisor` | CPU/RAM por contenedor (headroom, OOM) | 128M |
| `mysqld_exporter` | conexiones, buffer pool, InnoDB, slow | 64M |
| `blackbox_exporter` | probe HTTP a las 3 `/api/health` | 64M |

### Pasos (en el server)

1. **Crear el usuario `exporter` en MySQL** (una sola vez):
   ```sql
   CREATE USER 'exporter'@'%' IDENTIFIED BY '<MYSQL_EXPORTER_PASSWORD>' WITH MAX_USER_CONNECTIONS 3;
   GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'%';
   FLUSH PRIVILEGES;
   ```
2. **Agregar a `.env`**: `GRAFANA_ADMIN_PASSWORD=...` y `MYSQL_EXPORTER_PASSWORD=...` (el mismo del paso 1).
3. **Levantar el stack** (junto al principal, para compartir `internal_net`):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d \
     prometheus grafana node_exporter cadvisor mysqld_exporter blackbox_exporter
   ```
4. **Ver targets**: Prometheus en `http://localhost:9090/targets` (vía túnel SSH:
   `ssh -L 9090:localhost:9090 ...` — Prometheus no se expone públicamente).
5. **Grafana** en `http://localhost:3009` (login `admin` / `GRAFANA_ADMIN_PASSWORD`). El datasource
   Prometheus se provisiona solo. Importar dashboards de la comunidad por ID:
   - **1860** Node Exporter Full · **14282** cAdvisor · **7362** MySQL Overview (mysqld_exporter).

### Alertas
`ops/monitoring/alerts.yml` ya define: target caído, superficie sin 2xx, RAM del host < 10%,
contenedor > 90% de su límite (riesgo OOM — relevante para réplicas), disco < 10%, MySQL caído,
conexiones MySQL > 80% de `max_connections`. Para **notificar** hace falta Alertmanager o usar el
alerting de Grafana apuntando a estas métricas (configurable en la UI).

### Exponer Grafana (opcional)
Por seguridad Grafana escucha en `127.0.0.1:3009`. Para acceso remoto: túnel SSH (recomendado) o un
Proxy Host en NPM con auth (`grafana.tuwayki.app` → `tuwayki_grafana:3000`).

## Recomendación

**Tier 1 ahora** (gratis, alta señal). **Tier 2 cuando el host tenga RAM** (o en un host aparte);
es lo que te va a mostrar de forma continua el **headroom de RAM** para decidir el escalado de réplicas
(paso 3) y validar el efecto del tuning (paso 2) y de la read-replica (paso 4).

## Integración con el deploy
Este stack NO se levanta en el deploy automático (`deploy-prod.sh` sólo maneja el compose base). Es un
`docker compose up` manual (o se puede agregar un toggle `MONITORING=1` análogo a `SCALE_SYS` si se
quiere automatizar; hoy queda manual a propósito, por el costo de RAM).
