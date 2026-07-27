# P3 — Diseño de escalado horizontal + infraestructura

> Fase P3 del `docs/PERF_SCALABILITY_PLAN.md` §5. Documento de **diseño** (para revisar antes de
> ejecutar). Anclado en el stack real (no genérico). Fecha: 2026-07-27.

## 0. Por qué P3 (evidencia de P1/P2)

- **P1** cerró el problema de índices (`index_merge` → covering; barrido de `company_id` redundantes;
  covering faltante de `cashboxsession`). Las queries calientes del POS ya no son el cuello.
- **P2** midió el transporte y el pipeline:
  - `ping` (Fase A): el event-loop del backend **aguanta bien** — p95 ≤ 33 ms hasta 200 conexiones.
  - `cajero` autenticado: bajo carga concurrente el techo es el **costo por-handler atado a BD +
    saturación del proceso único** (Reflex es 1 proceso async). Los absolutos locales son pesimistas
    (todo co-locado en una máquina), pero la **forma** es clara.
- **Conclusión**: lo que mueve la aguja no es más tuning del proceso único, sino **más procesos
  (réplicas horizontales) + descargar lecturas pesadas de MySQL**. Eso es P3.

## 1. Estado actual (lo que YA existe — no reinventar)

| Pieza | Estado |
|---|---|
| Superficies | 3 servicios **distintos** (`tuwayki_landing`/`sys`/`admin`), **single-instance** c/u, `container_name` fijo. |
| Estado Reflex | `StateManagerRedis` + `RedisTokenManager` + tarea **lost-and-found** (`emit_update` por pub/sub Redis) → **multi-instancia CAPAZ** (estado compartido; updates cross-instancia se propagan). |
| Pool MySQL | `POOL_SIZE=15` + `MAX_OVERFLOW=10` = **25 conexiones/instancia** (rxconfig). |
| Reverse proxy | nginx **websocket-aware** (`map $http_upgrade`, `upstream`, headers Upgrade/Connection, `keepalive 64`). Rate-limit `login_zone`/`api_zone` por IP + rate-limit de app por **Redis** (consistente entre réplicas). |
| Backups | `ops/backup-db.sh` (cron diario 02:00 + retención + **S3 offsite**), `ops/backup-healthcheck.sh`, `ops/restore-db.sh`. Además backup on-deploy en `deploy-prod.sh`. |
| Perf/infra | `ops/mysql-perf-audit.sh` (cron mensual), `ops/systemd/*.service`, `ops/nginx/*.conf`. |
| Health | `/api/health` (db+redis) y `/api/ping` (healthcheck del contenedor). |

## 2. La pregunta crítica: ¿sticky sessions?

Reflex mantiene el **estado en Redis** y propaga updates cross-instancia (lost-and-found), así que la
**correctitud NO exige** que un cliente vuelva siempre a la misma instancia. PERO la conexión
**socket.io/engine.io** es por-instancia (la sesión de transporte vive en un backend). Para evitar que
el handshake (GET polling → upgrade a websocket) se parta entre instancias, la práctica estándar es
**sticky sessions**.

**Decisión**: `ip_hash` en el `upstream` (sticky por IP) como default seguro. Riesgo conocido: NAT
corporativo (varios cajeros misma IP pública) → caen en la misma instancia. Alternativa si molesta:
hash por cookie del token Reflex (`hash $cookie_...`), que reparte mejor. Empezar con `ip_hash`.

## 3. Cambios concretos

### 3.1 Réplicas del POS (`tuwayki_sys`)
El `container_name: tuwayki_sys` fijo **impide** escalar (`docker compose` no puede correr 2 contenedores
con el mismo nombre). Opciones:

- **A (recomendada, simple)**: definir servicios explícitos `tuwayki_sys_1`, `tuwayki_sys_2`, … cada uno
  con su puerto host (`3200`, `3201`, …), mismo `.env`/red/imagen. Determinístico y fácil de mapear en
  nginx. Empezar con **2 réplicas**.
- **B**: quitar `container_name` y usar `docker compose up --scale tuwayki_sys=N` (puertos efímeros →
  nginx tendría que descubrirlos; más fricción sin Swarm).

> No usar `--workers`: Reflex es single-process async; el paralelismo se logra con **procesos/contenedores
> separados**, no con workers dentro del proceso.

### 3.2 nginx: upstream con N servers + sticky
```nginx
upstream tuwayki_app {
    ip_hash;                    # sticky: el handshake socket.io va siempre a la misma instancia
    server 127.0.0.1:3200;
    server 127.0.0.1:3201;
    keepalive 64;
}
```
El resto del `location` (Upgrade/Connection, timeouts largos para websocket) ya está en
`ops/nginx/tuwayki-domain-split.conf`.

### 3.3 MySQL: aritmética de conexiones + tuning
- **Límite duro**: `N_réplicas × 25 < max_connections`. Con `max_connections=151` (default) → **N ≤ 5**.
  Antes de escalar: subir `max_connections` (p.ej. **300**) y/o **bajar `DB_POOL_SIZE`** por instancia
  (p.ej. 10+5=15) según cuántas réplicas.
- `innodb_buffer_pool_size` = **50–70 % de la RAM** del host de BD (que el working set entre en memoria).
- **Réplica de lectura**: las queries pesadas (dashboard/reportes de `owner`/`report_state`) a una
  **réplica de solo-lectura**; el POS (escritura) sigue en el primario. Requiere: replicación MySQL +
  un segundo engine/URL de solo-lectura y ruteo de lectura en el código de reportes (cambio acotado,
  no en el hot-path del POS).

### 3.4 Redis: sizing + expiración
- Dimensionar memoria para **N sesiones de estado** concurrentes (cada token = un blob de estado).
- Política de **expiración/TTL** del estado de sesiones muertas + `maxmemory-policy` (p.ej.
  `volatile-lru`) para no crecer sin techo.

### 3.5 Monitoreo + alertas (el gap real)
Existe health interno, **falta observabilidad externa**. Mínimo viable:
- **Uptime externo** sobre `/api/health` de las 3 superficies (alerta si `status!=ok` o `db/redis` caen).
- **Métricas**: CPU/mem por contenedor, **saturación del pool** (conexiones activas vs 25), latencia,
  5xx, conexiones MySQL. `node_exporter` + `mysqld_exporter` + Prometheus/Grafana, o un stack liviano.
- **Alertas**: caída de `/api/ping`, pool saturado, errores 5xx sostenidos, backup viejo
  (`backup-healthcheck.sh` ya lo evalúa → exponerlo como alerta).

## 4. Plan por pasos (de menor a mayor riesgo)

1. **Backups programados — verificar en prod** (bloqueante): correr `ops/backup-healthcheck.sh` en el
   server; si el cron no está instalado, instalarlo (`0 2 * * * .../backup-db.sh`). Sin cambio de topología.
2. **MySQL tuning** (`max_connections`, `innodb_buffer_pool_size`) — sin cambiar topología.
3. **2 réplicas de `sys` + nginx `ip_hash`** — validar con `scripts/ws_load.py` **a través del LB** que
   (a) el estado se mantiene entre eventos y (b) la latencia baja vs 1 instancia bajo la misma carga.
4. **Réplica de lectura MySQL** + ruteo de lectura en reportes.
5. **Monitoreo + alertas**.

## 5. Validación

- Con `ws_load.py` apuntando al **LB** (no a una instancia): escenario `cajero`, comparar la curva con
  1 vs 2 réplicas → debe subir el punto de degradación. Confirmar 0 errores de estado (que la propagación
  cross-instancia funcione: un evento en la instancia A refleja estado escrito en B).
- Repetir la Fase B (absolutos) recién cuando haya infra prod-like separada (pendiente de P2; el AWS
  free-tier no sirve).

## 6. Fuera de alcance de P3 (anotado)

- Autoscaling dinámico (K8s / Swarm) — sobredimensionado para el volumen actual; N fijo de réplicas
  alcanza. Reconsiderar si el volumen lo justifica.
- Sharding de MySQL — muy prematuro; primero read-replica + tuning.
