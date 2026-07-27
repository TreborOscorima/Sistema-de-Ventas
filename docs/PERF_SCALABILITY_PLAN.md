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
| App backend | **1 proceso** (`reflex run --env prod`, sin `--workers`) | Cuello de botella principal hoy |
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

1. **Índices faltantes** que salgan de §3 (una migración Alembic; efecto inmediato).
2. Subir **workers del backend** (`reflex run ... ` con varios workers / réplicas) — el estado
   ya está en Redis, así que es mayormente configuración.
3. **Backups automáticos** de MySQL (no es performance, pero es requisito para escalar en serio).
4. Tunear `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` por env según réplicas.

---

## 7. Cómo se ejecuta (por fases)

1. **P1 (BD)**: seed grande en staging + `EXPLAIN` + índices. *Mayor ROI, empezar acá.*
2. **P2 (carga)**: medir concurrencia real y fijar el número seguro.
3. **P3 (infra)**: horizontal + backups + monitoreo cuando el volumen lo justifique.

Cada fase actualiza la §2 con **números medidos** (reemplazando las hipótesis actuales).
