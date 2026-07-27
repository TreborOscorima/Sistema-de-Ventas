# Plan de Performance y Escalabilidad — TUWAYKISHOP

> Complementa `docs/QA_E2E_PLAN.md` (que cubre **corrección funcional**). Este documento
> cubre **capacidad, carga y escalado** — lo que define "operar con más fuerza y volumen".
> Estado inicial: **redactado 2026-07-27, pruebas NO ejecutadas todavía**.

---

## 0. Aclaración clave: el límite no es "cantidad de empresas"

TUWAYKISHOP es una app **Reflex (websocket, con estado por cliente)**. Por eso el cuello de
botella real es **usuarios ACTIVOS simultáneos** (sesiones abiertas operando), no cuántas
empresas están registradas. Hay que separar dos métricas:

- **Empresas registradas / onboarded**: limitado por tamaño de BD y performance de queries.
  Con el aislamiento multi-tenant ya verificado, escalar a **cientos–miles de empresas**
  registradas es sano *si las queries están bien indexadas* (a validar en §2).
- **Usuarios activos concurrentes (pico)**: la métrica que realmente satura el app-tier.

Una empresa retail típica tiene **1–5 cajeros activos** en simultáneo en hora pico.

---

## 1. Snapshot de la infraestructura actual (2026-07-27)

| Componente | Estado actual | Implicancia para escala |
|---|---|---|
| App backend | **1 proceso** (`reflex run --env prod`; event loop async single-process) | Cuello de botella principal hoy. El límite es el event loop, no threads: no se escala con `--workers` (WSGI clásico) sino con **N réplicas del contenedor** (ver §5) |
| Estado Reflex | **Redis** (`REDIS_URL`) | ✅ Permite escalar horizontal (backend casi stateless) |
| Rate limit | Redis, fail-closed | ✅ Compartible entre instancias |
| Pool MySQL | `pool_size=15` + `max_overflow=10` = **25 conx máx/proceso** (env-tunable) | Suficiente si queries son rápidas |
| Deploy | Docker Compose, 1 contenedor por superficie (`tuwayki_sys`) | Falta réplicas + balanceador |
| MySQL | 1 instancia | Falta tuning + réplica de lectura para reportes |
| Backups / Monitoreo / Alertas | **No verificados** | Bloqueante para producción a escala |

---

## 2. Estimación de capacidad (HIPÓTESIS a validar — NO son garantías)

> Números aproximados, orden de magnitud, **pendientes de confirmar con las pruebas de §3–§5**.
> Se dan como punto de partida, no como promesa.

### Configuración actual (1 contenedor, 1 proceso backend)
- **Empresas registradas**: cómodo hasta **~cientos** (500–1.000+) si §3 confirma índices OK.
  El volumen de datos por empresa (productos, ventas históricas) pesa más que el número de empresas.
- **Usuarios activos concurrentes (pico)**: estimado **~50–150** sesiones operando a la vez
  antes de que la latencia de eventos empiece a degradar (1 proceso async Python, handlers
  atados a BD). **Muy sensible al costo de cada handler y a la latencia de las queries.**
- Traducido a empresas operando **al mismo tiempo**: con ~2–3 cajeros activos por empresa en
  pico → **~20–50 empresas operando en simultáneo** en esta config. Registradas: muchas más.

### Con escalado horizontal (varias instancias backend + balanceador, Redis ya compartido)
- El estado ya está en Redis → agregar instancias escala usuarios concurrentes **casi lineal**.
  4 instancias ≈ **~200–600 concurrentes**; el nuevo límite pasa a ser **MySQL** (conexiones,
  CPU, I/O) → ahí entra réplica de lectura + tuning (§5).

### Resumen honesto
- **Hoy, tal cual**: sólido para una operación **pequeña/mediana** — decenas de empresas
  operando en pico, cientos registradas.
- **Para "mayor fuerza" real (cientos concurrentes / miles de empresas)**: requiere el trabajo
  de §4 (horizontal) + §5 (BD/infra). La arquitectura **lo permite** (Redis state), no hay que
  reescribir.

---

## 3. Fase P1 — Auditoría de performance de BD (la más importante)

Objetivo: que las queries calientes no degraden con tablas grandes.

> **Estado real de la indexación (verificado 2026-07-27):** NO se parte de cero. El repo ya
> tiene una capa de índices madura, con ~10 migraciones dedicadas — entre ellas
> `l2m3n4o5p6q7_layer2_performance_indexes` (covering `(company_id, branch_id, status, timestamp)`
> en `sale`, el hot path de POS, + drop de 8 índices redundantes),
> `cfa77546ed70_add_missing_composite_indexes`, `f3e4a5b6c7d8_add_composite_indexes`,
> `g7h8i9j0k1_add_analytics_indexes`, `h1i2j3k4l5_add_saleitem_indexes`,
> `i8j9k0l1m2n3_add_product_search_index`, `f2d3c4b5a6b7_add_credit_and_reservation_indexes`.
> Por eso P1 es **VALIDAR con volumen real que estos índices se usan (que el planner los elige) y
> cazar los pocos huecos que queden**, NO diseñar índices desde cero. Esto baja el esfuerzo de P1
> de semanas a días.

- [ ] **Sembrar dataset grande** en una BD de staging: p. ej. 500 empresas × (2.000 productos,
      50.000 ventas, 200.000 saleitems, 100.000 stockmovements). Script de seed idempotente.
- [ ] **`EXPLAIN`** de las queries calientes con ese volumen:
  - POS: resolución de precio (`resolve_price_list_price`, `resolve_price_tier_price`,
    `find_applicable_promotion`), búsqueda de producto por barcode/nombre.
  - Dashboard: KPIs, top productos, stock bajo, `_refresh_financial_cache`.
  - Reportes/Historial: ventas por rango, export Excel.
  - Caja: reconciliación, cierre.
- [ ] **Revisar índices**: confirmar índice en `(company_id, branch_id, ...)` de las tablas
      calientes (`product.barcode`, `sale.timestamp`, `saleitem.sale_id`, `stockmovement`,
      `promotion` por scope/fecha, FKs). Documentar los faltantes.
- [ ] **N+1 queries**: detectar bucles que emiten 1 query por ítem (candidatos: explosión de
      kits, reportes, listas). Medir con echo de SQL / logging de queries.
- [ ] Verificar que `_refresh_financial_cache()` y agregados no re-escaneen tablas completas.

**Entregable**: lista priorizada de índices a agregar (vía migración Alembic) + queries a optimizar.

### Hallazgos medidos — corrida P1 (2026-07-27, staging)

Set-up: `sistema_staging` (Docker MySQL 8.0) migrado a head + `seed_volume.py` + `ANALYZE TABLE`.
Se corrió con dos distribuciones para descartar artefactos: (a) 13 empresas / 130k ventas (100%
completed, uniforme) y (b) **150 empresas / 225k ventas / 788k items, mix realista de `status`
(90% completed) y timestamps sesgados a reciente**. EXPLAIN vía `explain_hot_queries.py` +
`EXPLAIN ANALYZE` para tiempos reales.

- ✅ **Sin full table scans.** Las 10 queries calientes tocan índice.

- 🔴 **HALLAZGO CONFIRMADO — el optimizador usa `index_merge intersect` de índices single-column
  en vez del compuesto covering, ignorando el filtro de fecha y forzando `filesort`.** Se sostiene
  con datos realistas (150 tenants). Query del POS/Historial (ventas por rango + estado, `EXPLAIN
  ANALYZE` real):

  | Plan | Filas escaneadas | Filesort | **Tiempo real** |
  |---|---|---|---|
  | Optimizador (`intersect(ix_sale_company_id, ix_sale_branch_id)`) | 1500 + 1500 | Sí | **105 ms** |
  | Compuesto `ix_sale_tenant_status_timestamp` | 50 | No | **0.22 ms** |

  El `index_merge` escanea **todo** el histórico del tenant (las 1500 ventas), lo intersecta e
  ignora el `timestamp BETWEEN` → **escala linealmente con el histórico** (un local con 50k ventas
  escanearía 50k en cada listado del POS). La estimación `rows` de EXPLAIN es engañosa (mostraba
  10); sólo `EXPLAIN ANALYZE` reveló las 1500 filas reales. Mismo patrón en `product` y `saleitem`.

  - **Causa raíz**: los índices single-column de `TenantMixin` (`company_id`/`branch_id` con
    `index=True`) habilitan el `index_merge` que el cost-model prefiere, bypasseando el compuesto.
    Continúa el trabajo de la migración `l2m3n4o5p6q7`.

- ✅ **Remediación PROBADA en staging**: `DROP INDEX ix_sale_company_id` (redundante: la FK de
  `company_id` ya está cubierta por los compuestos que lideran con esa columna) → el optimizador
  pasa a `ix_sale_tenant_status_timestamp`: **105 ms → 0.22 ms (~480x), sin filesort**.

**Remediación a aplicar (migración Alembic, NO aplicada aún — pendiente de OK):**
1. **Drop de single-column `ix_*_company_id` redundantes** en `sale`, `saleitem`, `product` (y
   revisar demás tablas `TenantMixin`) donde un compuesto ya lidera con `company_id` y cubre la FK.
   **Precaución**: verificar por tabla que la FK de `company_id` quede cubierta por otro índice
   antes de dropear; `branch_id` single suele ser obligatorio (ningún compuesto lidera con él).
2. Confirmar con `EXPLAIN ANALYZE` post-drop en las 3 tablas + revisar que ninguna otra query
   dependiera del índice single-column.
3. Alternativas si (1) es riesgosa: `optimizer_switch='index_merge_intersection=off'` en la
   conexión de la app, o `FORCE INDEX` en las queries ORM calientes.

---

## 4. Fase P2 — Prueba de carga / concurrencia

Objetivo: medir el punto real de degradación de latencia.

- [ ] **Definir escenarios** representativos: "cajero" (escanear N productos + cobrar),
      "supervisor" (dashboard + reportes), "alta de producto".
- [ ] **Herramienta**: para el tráfico HTTP/API, **k6** o **Locust**. Para el websocket de
      Reflex (event handlers), un script que abra N websockets y dispare eventos
      (`hydrate` + eventos de estado) — ojo: Reflex no se testea con un simple `ab`.
- [ ] **Métricas objetivo (SLO propuestos)**:
  - Latencia de evento POS (p95) **< 400 ms** con carga objetivo.
  - Confirmar venta (p95) **< 1 s**.
  - 0 errores 5xx / desconexiones de websocket bajo carga sostenida 10 min.
- [ ] **Rampa**: 10 → 50 → 100 → 200 usuarios concurrentes; anotar dónde p95 supera el SLO.
- [ ] Repetir **con y sin** las optimizaciones de §3 para cuantificar la mejora.

**Entregable**: curva usuarios-concurrentes vs latencia → número real de "concurrentes seguros".

---

## 5. Fase P3 — Escalado horizontal + infraestructura

- [ ] **Multi-worker / multi-instancia**: correr el backend con varias réplicas detrás de
      **nginx** (o el NPM ya presente). Validar que el estado en Redis permite que un cliente
      sea atendido por cualquier instancia (sticky sessions vs stateless).
- [ ] **MySQL**: subir `pool_size`/`max_overflow` acorde a réplicas; tuning
      (`innodb_buffer_pool_size`, `max_connections`); evaluar **réplica de lectura** para
      reportes/dashboard.
- [ ] **Redis**: dimensionar memoria para N sesiones; política de expiración de estado.
- [ ] **Backups automáticos** de MySQL (dump programado + retención) — **bloqueante**.
- [ ] **Monitoreo/alertas**: métricas de CPU/mem/latencia/conexiones (Prometheus+Grafana o
      similar); alerta de caída de `/api/ping`, de saturación de pool, de errores.
- [ ] **Límites y protección**: revisar el pico de latencia ~8 s del websocket visto en QA §5
      bajo carga real (¿era entorno o un handler lento?).

---

## 6. Quick wins (bajo esfuerzo, alto impacto) — hacer primero

1. **Huecos de índices** que salgan de §3 (una migración Alembic; efecto inmediato). Ojo: la base
   de índices ya es amplia (ver nota de §3) → se espera que sean pocos y puntuales, no una tanda grande.
2. Agregar **réplicas del contenedor backend** detrás de nginx/NPM (NO `--workers`: Reflex es
   single-process async) — el estado ya está en Redis, así que es mayormente configuración + balanceador.
3. **Backups automáticos** de MySQL (no es performance, pero es requisito para escalar en serio).
4. Tunear `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` por env según réplicas.

> **Estado del tooling (2026-07-27):**
> - ✅ **Seed de volumen** — `scripts/seed_volume.py` (creado y validado). Perfiles
>   `smoke/small/medium/full`, bulk-insert por core, guard de BD-segura, prefijo `SEEDVOL-`.
> - ✅ **EXPLAIN de queries calientes** — `scripts/explain_hot_queries.py` (creado y validado).
> - ✅ **Concurrencia (corrección)** — `scripts/stress_concurrency.py` (preexistente).
> - ⏳ **Falta**: harness de **latencia bajo carga** de websockets Reflex (§4).

---

## 7. Cómo se ejecuta (por fases)

1. **P1 (BD)**: seed grande en staging + `EXPLAIN` + índices. *Mayor ROI, empezar acá.*
2. **P2 (carga)**: medir concurrencia real y fijar el número seguro.
3. **P3 (infra)**: horizontal + backups + monitoreo cuando el volumen lo justifique.

Cada fase actualiza la §2 con **números medidos** (reemplazando las hipótesis actuales).

---

## 8. Runbook de ejecución P1 (staging) — reproducible

BD de staging = **schema dedicado y descartable** en el Docker MySQL 8.0 (`tuwayki_mysql`,
puerto 33306), NUNCA el schema `sistema_ventas` de datos reales. El schema se llama
`sistema_staging` y se construye vía **migraciones Alembic** (no `create_all`: falla por las
columnas generadas MySQL 8 + orden de FKs — ver [[stack_gotchas]]).

```bash
# 1. Crear el schema descartable + permisos (dentro del contenedor; sin exponer passwords)
docker exec -i tuwayki_mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot' <<'SQL'
DROP DATABASE IF EXISTS sistema_staging;
CREATE DATABASE sistema_staging CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON sistema_staging.* TO 'app'@'%';
FLUSH PRIVILEGES;
SQL

# 2. Construir el schema fiel a prod con las migraciones (override de DB por env vars;
#    la password de 'app' la toma de .env vía load_dotenv)
ENV=dev DB_USER=app DB_HOST=127.0.0.1 DB_PORT=33306 DB_NAME=sistema_staging \
  ./.venv/Scripts/python.exe -m alembic upgrade head

# 3. Sembrar volumen (empezar chico; escalar a medium/full según haga falta)
SEED_DB_URL="mysql+aiomysql://app:PASS@127.0.0.1:33306/sistema_staging" \
  ./.venv/Scripts/python.exe scripts/seed_volume.py --profile medium --skip-schema

# 4. EXPLAIN de las queries calientes (elige la empresa con más ventas)
SEED_DB_URL="mysql+aiomysql://app:PASS@127.0.0.1:33306/sistema_staging" \
  ./.venv/Scripts/python.exe scripts/explain_hot_queries.py

# 5. Limpiar staging al terminar
docker exec -i tuwayki_mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "DROP DATABASE sistema_staging;"'
```

> Nota Windows: la password se lee de `.env` en memoria (nunca se imprime). Escalas de volumen:
> `full` (§3) ≈ **175M filas** — sólo en un host dedicado con disco; para validar índices,
> `medium` (~3,5M filas, ~10k ventas/empresa) ya es representativo del plan por-tenant.
