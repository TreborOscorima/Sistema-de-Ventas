# P3 — Paso 3: réplicas del POS + NPM sticky (runbook)

> Ejecuta la Fase P3 §3.1/§3.2 (`docs/P3_HORIZONTAL_SCALING_DESIGN.md`). Levanta una **2ª réplica** de
> `tuwayki_sys` y balancea entre ambas con **sticky sessions** en Nginx Proxy Manager.
>
> **Reparto**: el override de compose (`docker-compose.scale.yml`) y este runbook están en el repo. La
> config de **NPM es manual** (UI de NPM, en el server) — NPM no está versionado.

## 0. Topología

Prod usa **Nginx Proxy Manager** (no los `ops/nginx/*.conf`, que son referencia). NPM alcanza los
contenedores por hostname en la red `nginx-proxy-manager_default`. Hoy el Proxy Host de `sys.tuwayki.app`
apunta a un solo upstream (`tuwayki_sys:3000`). Con este paso pasan a ser **dos** (`tuwayki_sys` +
`tuwayki_sys_2`) detrás de un `upstream` con `ip_hash`.

**Por qué sticky (`ip_hash`)**: la conexión socket.io/engine.io vive en una instancia; el hash por IP
evita que el handshake (GET → upgrade websocket) se parta entre réplicas. Reflex comparte estado por
Redis (`StateManagerRedis` + pub/sub lost-and-found), así que la correctitud no lo exige, pero el
transporte se estabiliza. Nota: NAT (varios cajeros misma IP pública) caen en la misma instancia; si
molesta, cambiar a hash por cookie del token.

## 1. Levantar la 2ª réplica

### Opción A — automatizada vía GitHub Actions (recomendada)
El deploy soporta un **toggle**: la variable de repo **`SCALE_SYS`** (GitHub → Settings → *Secrets and
variables* → *Actions* → **Variables** → New variable `SCALE_SYS = 1`). Con eso, `deploy-prod.sh`
exporta `COMPOSE_FILE=docker-compose.yml:docker-compose.scale.yml`, buildea y espera healthy a
`tuwayki_sys_2`, y `--remove-orphans` **ya no la borra** (es parte del proyecto). Default (variable
ausente o vacía) = **1 sola réplica**, sin cambios.

Pasos:
1. Crear la variable de repo `SCALE_SYS = 1`.
2. Disparar un deploy (push a `main`, o Actions → deploy-prod → Run workflow). El deploy levanta y
   healthchequea `tuwayki_sys_2` solo.
3. Aplicar la config de NPM (§2). **Orden seguro**: la réplica puede correr *antes* de NPM (queda
   idle, sin tráfico); recién cuando NPM apunta al pool empieza a recibir.

### Opción B — manual en el server (one-off / prueba)
```bash
docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d
docker exec tuwayki_sys_2 curl -fsS http://localhost:3000/api/ping   # verificar healthy
```
> Si activás por esta vía SIN poner `SCALE_SYS=1`, el próximo deploy automático borra `sys_2`
> (`--remove-orphans`). Para persistir, usá la Opción A.

⚠️ **Capacidad**: `tuwayki_sys_2` consume hasta **1G RAM / 1 CPU** (mismo límite que `sys`). Confirmar
que el host de prod tiene margen antes de activar (con MySQL 1G + sys + admin + landing + Redis + NPM).

> ### ✅ `--remove-orphans` — resuelto por el toggle `SCALE_SYS`
> `deploy-prod.sh` corre `docker compose up -d --remove-orphans`. Con `SCALE_SYS=1`, el script exporta
> `COMPOSE_FILE` con el override → `tuwayki_sys_2` es parte del proyecto y **no se borra**. Con
> `SCALE_SYS=0` (default) el deploy usa solo el base (1 réplica). Ya no hay que parchear nada a mano.

## 2. NPM: upstream con sticky (manual, en la UI)

En Nginx Proxy Manager → Proxy Host de `sys.tuwayki.app` → pestaña **Advanced** → *Custom Nginx
Configuration*, definir el upstream y usarlo:

```nginx
# Pool de réplicas del POS con sticky por IP.
upstream tuwayki_sys_pool {
    ip_hash;
    server tuwayki_sys:3000;
    server tuwayki_sys_2:3000;
    keepalive 32;
}
```

Y en el forwarding del Proxy Host, apuntar a ese pool en vez del contenedor único. Si NPM no permite
cambiar el `proxy_pass` del bloque principal desde la UI, usar el location custom con los headers de
websocket (ya presentes en el forwarding de NPM: `Upgrade`/`Connection`), p.ej.:

```nginx
location / {
    proxy_pass http://tuwayki_sys_pool;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 3600s;   # websockets largos
    proxy_send_timeout 3600s;
}
```

> `$connection_upgrade` viene del `map $http_upgrade $connection_upgrade` que NPM ya define en su http
> context. Si no existiera, agregarlo en la config global de NPM.

Guardar → NPM recarga nginx. **El contenedor `nginx_sys` de NPM debe poder resolver `tuwayki_sys_2`**
(ambas réplicas en `nginx-proxy-manager_default`; el override ya las pone ahí).

## 3. Validación (en prod, tras aplicar 1 y 2)

- Salud: `curl -sf https://sys.tuwayki.app/api/health` → `status:ok, db:ok, redis:ok`.
- **Reparto de carga**: hacer varias sesiones desde IPs distintas y ver logs de ambas réplicas
  recibiendo tráfico:
  ```bash
  docker logs --since 5m tuwayki_sys   | grep -c "Inicio de venta"
  docker logs --since 5m tuwayki_sys_2 | grep -c "Inicio de venta"
  ```
- **Latencia bajo carga** (si hay infra prod-like separada): `scripts/ws_load.py` apuntando al **LB**
  (`https://sys.tuwayki.app`) con el escenario `cajero` — comparar la curva vs 1 réplica. (En infra
  co-locada los absolutos no son representativos; ver P2 §4.)
- **Consistencia**: una sesión de cajero completa (login → venta) debe funcionar sin errores de estado.

## 4. Rollback

Volver a una sola réplica es inmediato y sin riesgo de datos:
1. En NPM: quitar `tuwayki_sys_2` del `upstream` (o restaurar el `proxy_pass` al contenedor único) → recargar.
2. `docker compose -f docker-compose.yml -f docker-compose.scale.yml stop tuwayki_sys_2` (o `down` solo esa).
El estado vive en Redis + MySQL (compartidos); apagar una réplica no pierde datos.

## 5. Aritmética de conexiones (recordatorio)

Con 2 réplicas de sys: `(landing + admin + sys + sys_2) = 4 × 25 conns = 100 < max_connections=200`.
Margen para hasta ~6 réplicas de sys antes de tener que subir `max_connections` / bajar el pool por
instancia (ver §3.3 del diseño). El tuning de MySQL (O_DIRECT, redo, io) ya está aplicado (paso 2).
