# AUDITORÍA INTEGRAL — TUWAYKIAPP (Sistema de Ventas SaaS)

> **Fecha:** 2026-07-05 · **HEAD auditado:** `c530a7c` (rama `main`)
> **Propósito de este documento:** ser el punto de entrada único para cualquier IA o desarrollador que deba continuar el proyecto. Contiene: mapa del sistema, veredicto por área (frontend, backend, seguridad, rendimiento, offline, facturación electrónica), hallazgos priorizados y guía operativa de continuidad.

---

## 1. Resumen ejecutivo

TUWAYKIAPP es un **ERP/POS SaaS multi-tenant** construido 100% en Python con **Reflex 0.9.4** (frontend React generado + backend ASGI en un solo framework), MySQL 8, Redis y Docker. Se despliega como **3 superficies independientes** del mismo código, controladas por la env var `APP_SURFACE`:

| Superficie | Dominio | Contenedor | Rol |
|---|---|---|---|
| `landing` | tuwayki.app | `tuwayki_landing` | Marketing público (home selector, /ventas, /food) — único que ejecuta migraciones |
| `app` | sys.tuwayki.app | `tuwayki_sys` | El sistema de ventas (POS/ERP) para tenants |
| `owner` | admin.tuwayki.app | `tuwayki_admin` | Backoffice de plataforma (gestión de empresas, billing, auditoría) |

Existe un producto hermano **TUWAYKIFOOD** (restaurantes/restobares) en un **repo separado e independiente** que comparte el paquete privado `tuwayki-core` (vendorizado en `_vendor/tuwayki-core/`). Regla del proyecto: **cambios en un repo nunca afectan al otro; no duplicar código entre repos** — lo compartible va a `tuwayki-core`.

**Veredicto general:** el sistema está en estado **maduro y production-ready** para su alcance actual. Tres rondas de auditoría previas (148+ hallazgos) fueron corregidas y cerradas; hay ~1.023 tests. Las áreas con mayor brecha real hoy son: (a) **operación offline** (arquitectónicamente no soportada, ver §7), (b) **endurecimiento del panel Owner** (sin MFA, cuenta única), y (c) **completar la certificación/homologación de facturación electrónica** en ambos países (el código está, falta el ciclo formal + representaciones impresas con QR).

---

## 2. Mapa del código (para orientarse rápido)

```
Sistema-de-Ventas/
├── app/
│   ├── app.py            # Bootstrap: migraciones al arranque, registro de rutas por superficie
│   ├── api.py            # /api/health (readiness), /api/ping (liveness), lifespan + fiscal retry worker
│   ├── state.py + states/  # State único por composición de mixins (Auth, Venta, Inventory, Cash, Owner…)
│   ├── models/           # SQLModel: auth, company, sales, inventory, billing (fiscal), owner, promos…
│   ├── services/         # Lógica de negocio: sale_service, billing_service (SUNAT/AFIP), afip_wsaa/wsfe,
│   │                     #   credit_service, report_service, receipt_service, owner_service, food_api_client…
│   ├── pages/            # UI por módulo: venta/, caja/, inventario/, compras/, marketing/ (landing), owner/…
│   ├── tasks/            # fiscal_retry_worker.py (reintentos automáticos de docs fiscales)
│   ├── utils/            # Re-exports de tuwayki_core + helpers locales (db, tenant, crypto, rate_limit…)
│   └── i18n/messages.py  # Textos (español latino neutro — regla del proyecto)
├── _vendor/tuwayki-core/ # Paquete privado compartido con TUWAYKIFOOD: auth JWT, tenant isolation,
│                         #   crypto Fernet, rate limit Redis, validators fiscales, exports, timezone
├── alembic/              # Migraciones (auto-aplicadas al boot por la superficie landing)
├── assets/               # sw.js (service worker), manifest*.json, js/twk-*.js, css, imágenes webp
├── docker-compose.yml    # Stack prod: mysql + redis + 3 superficies detrás de Nginx Proxy Manager
├── Dockerfile            # Multi-stage, runtime non-root (uid 1000), tini
├── scripts/              # deploy.sh, deploy-prod.sh, backups, smoke tests, stress, make_owner.py
├── ops/                  # nginx, systemd, backup/restore
├── tests/                # ~1.023 tests (pytest)
└── docs/                 # Runbooks: DEPLOYMENT_SECURITY, CANARY_ROLLOUT, DOMAIN_SPLIT, NGINX_PROXY_MANAGER,
                          #   SYSTEM_FULL_DOCUMENTATION, PERFORMANCE_OPTIMIZATION_REPORT, RESPONSIVE_AUDIT
```

**Módulos funcionales del sistema (superficie `app`):** Dashboard, Venta (POS), Caja, Inventario (con variantes y lotes), Ingreso/Compras, Órdenes de Compra (reposición), Historial, Reportes, Servicios/Reservas (canchas), Clientes, Cuentas Corrientes (crédito), Presupuestos, Promociones, Listas de Precios, Etiquetas (códigos de barra), Documentos Fiscales, Configuración (incl. multi-sucursal y billing fiscal).

---

## 3. Frontend — Landing (ventas + restobares)

**Estado: BUENO.** `app/pages/marketing/` contiene:
- `/` → home selector de producto (TUWAYKIAPP vs TUWAYKIFOOD), `_home.py`
- `/ventas` → landing del sistema de ventas (`_page.py` + `_sections.py`, ~1.038 líneas de secciones)
- `/food` → landing de restobares (`_food_page.py` + `_food_sections.py`)
- `/home` → alias con `noindex` para compatibilidad SEO

Lo que ya está bien: canonical + OG + Twitter cards por ruta, `robots.txt` y `sitemap.xml` en assets, imágenes en WebP, preconnect a Google Fonts con `display=swap`, GA4 y Meta Pixel opcionales por env var, service worker **excluido de la landing a propósito** (evita HTML stale post-deploy), CSS/JS estáticos cacheables.

Mejoras recomendadas (orden de impacto):
1. **JSON-LD structured data** (`Organization`, `SoftwareApplication`, `FAQPage`) — hoy no hay datos estructurados; es SEO barato.
2. **Landing estática a futuro:** servir la landing desde Reflex implica cargar el runtime React completo para una página de marketing. Si el tráfico crece, evaluar pre-render estático o Astro/HTML plano detrás de NPM (la landing casi no tiene estado; `_state.py` es de 304 líneas, principalmente formulario de contacto/CTA).
3. Auditoría Lighthouse periódica (LCP de la imagen hero, CLS de fuentes) y un test E2E de humo para las 3 rutas públicas.

---

## 4. Backend y arquitectura

**Estado: SÓLIDO.** Puntos verificados:

- **Multi-tenant enforced en la capa ORM** (`tuwayki_core/utils/tenant.py`): listeners `do_orm_execute` + `before_flush` que (1) inyectan `company_id`/`branch_id` en todo SELECT vía `with_loader_criteria`, (2) autocompletan tenant en INSERT, (3) **bloquean** cualquier UPDATE que intente mover una fila de tenant, (4) modo estricto por defecto (`TENANT_STRICT=1`) que lanza excepción si falta contexto. Bypass explícito solo vía `tenant_bypass()` (jobs/owner). Este es el mecanismo de seguridad más importante del sistema — **cualquier código nuevo debe usar `set_tenant_context()`/`tenant_context()` y jamás desactivar los listeners.**
- **Migraciones automáticas al boot** (solo superficie landing; `sys`/`admin` usan `SKIP_MIGRATE=true`) — idempotente, con lock de Alembic.
- **Health checks correctos:** `/api/ping` (liveness barato) vs `/api/health` (readiness con DB+Redis, devuelve 503).
- **Worker fiscal en background** con jitter anti-thundering-herd, limitado a superficies `app|all`.
- **Estado Reflex por composición de mixins** sobre un `State` raíz único (`app/state.py`). Es el patrón correcto en Reflex pero implica que el tamaño total del estado afecta a cada delta — ver §6.
- **Docker endurecido:** multi-stage, runtime non-root, tini como PID 1, MySQL/Redis solo en red interna (sin puertos al host), contraseñas root/app separadas, límites de memoria/CPU, `restart: on-failure:10`, logging con rotación.
- **Backups:** `ops/backup-db.sh` (dump + rotación + offsite S3 opcional), `ops/restore-db.sh` (restore Docker), `scripts/backup_restore_verify.py` (crea DB temporal, restaura, compara row counts de TODAS las tablas, limpia al terminar; soporta modo `--docker`). Health-check: `ops/backup-healthcheck.sh` (frescura, tamaño, cron, contenedor, S3). Offsite configurado vía `S3_BUCKET` en `.env`.

Deudas menores detectadas:
- ~~`default.conf` (nginx por IP, sin dominio) referencia `app:8000`~~ — **borrado** en `79c4d1b`.
- ~~`dev.err`, `.coverage`, `e2e_screenshots/`, `testing_session_log.md` sin trackear~~ — **agregados a `.gitignore`** en `79c4d1b`.

---

## 5. Seguridad

**Estado: FUERTE en el core, con brechas puntuales en Owner y capas de defensa en profundidad.**

### Lo que ya está bien (verificado en código)
| Control | Implementación |
|---|---|
| Passwords | bcrypt con salt (`auth_state.py`, `register_state.py`, `owner_service.py`) |
| Sesiones | JWT HS256 con expiración + refresh token + **token versioning** (`ver`) para revocación; validación de `AUTH_SECRET_KEY` ≥32 chars en prod (falla el boot si es débil) |
| Credenciales fiscales | Fernet (AES-128-CBC+HMAC) con clave derivada PBKDF2-SHA256 600k iteraciones, salt aleatorio por valor; nunca texto plano en DB |
| Rate limiting login | Redis con ventana + lockout por usuario+IP; en prod **fail-closed** si Redis cae (a menos que se permita fallback explícito) |
| Aislamiento tenant | Capa ORM (ver §4) + tests dedicados (`test_auth_roles_tenant_scope.py`) |
| XXE | `defusedxml` para parsear respuestas SOAP de AFIP |
| Sanitización de errores fiscales | Regex que borra tokens/Bearer antes de persistir en `FiscalDocument.fiscal_errors` |
| Headers | X-Frame-Options, nosniff, Referrer-Policy en nginx; `noindex` en todas las páginas privadas |
| Contenedores | non-root, DB/Redis sin exposición al host, secrets vía `.env` requeridos (`:?` en compose) |
| Owner | Password solo por hash bcrypt en env (`OWNER_ADMIN_PASSWORD_HASH`), timeout de sesión 30 min, rate limit de acciones, sección de auditoría |

### Brechas y recomendaciones (priorizadas)

**P1 — Panel Owner sin MFA y con cuenta única.** No existe TOTP/2FA en ninguna superficie (verificado por grep: cero ocurrencias). El Owner puede suspender empresas y ver billing de toda la plataforma; su login es email+password. Recomendado: (a) TOTP (pyotp) para Owner como mínimo, (b) allowlist de IP en Nginx Proxy Manager para admin.tuwayki.app, (c) múltiples cuentas owner con roles en DB en lugar del par email/hash por env var (hoy `_load_owner_password_hash()` tiene fallback embebido con warning — el log `dev.err` muestra que en dev corre con fallback).

**P2 — Rate limit de acciones Owner es in-memory por proceso** (`_owner_action_timestamps` en `owner_state.py`) — con más de un worker no protege. Moverlo al helper Redis existente.

~~**P2 — Sin Content-Security-Policy.**~~ ✅ CSP report-only agregado en NPM custom configs, `domain-split.conf`, `single-surface.conf` y docs. HSTS confirmado activo (checkbox NPM + header explícito). `X-XSS-Protection` eliminado de docs. Pendiente: migrar a CSP enforcing tras 1-2 semanas sin violaciones en DevTools.

**P3 — 2FA opcional para usuarios tenant** (admins de empresa), y política de contraseñas configurable por empresa.

**P3 — Gestión de secretos:** `.env` plano en el servidor. A futuro: SOPS/age o secretos de Docker; y rotación documentada de `AUTH_SECRET_KEY` (ojo: rotar la clave invalida credenciales fiscales encriptadas — es fail-secure por diseño; requiere re-carga de certificados).

---

## 6. Rendimiento y fluidez

**Estado: BUENO, con trabajo previo documentado** (`docs/PERFORMANCE_OPTIMIZATION_REPORT.md`). Lo ya hecho: skeletons de contenido para eliminar parpadeo de navegación (~3-4s → instantáneo), sidebar/toasts fuera del ciclo de hidratación, JS/CSS servidos como estáticos cacheables (no inline), granian como servidor ASGI, `lookup_cache` para catálogos, monitoreo de queries lentas (`query_timer`, umbrales 1s/5s), slow query log de MySQL activado, gzip, imágenes WebP.

Riesgos y mejoras:
1. **Tamaño del State raíz.** El patrón "un State con todos los mixins" hace que cada evento serialice/deserialice el estado del cliente. Vigilar el tamaño (payload de hidratación y deltas WebSocket). Mitigación Reflex-idiomática: mover datos pesados a computed vars con `@rx.var(cache=True)`, paginar toda lista (ventas, historial, inventario) y evitar listas completas en estado.
2. **Redis como state manager de Reflex** en prod (multi-worker/multi-instancia): confirmar `REDIS_URL` visible para Reflex (no solo para rate limit) para habilitar sticky-session-free scaling.
3. **Índices DB:** existe slow query log — establecer rutina mensual: revisar log → `EXPLAIN` → índice compuesto (`company_id`, columna de filtro) ya que *todas* las queries llevan `company_id`.
4. **`innodb_buffer_pool_size=256M`** es conservador; si el servidor tiene RAM, subirlo mejora todo el sistema de golpe.
5. Latencia percibida del POS: el flujo de venta es lo más sensible — mantener el carrito 100% en estado del cliente y tocar DB solo al cobrar (verificar que siga así al agregar features).

---

## 7. Online / Offline — análisis honesto

**Hoy:** hay PWA instalable (manifest + banner de instalación + `sw.js` v2) **solo en la superficie app**. El SW hace: network-first para HTML, cache-first para `/_next/static/*` (assets con hash), bypass total de `/api/*`, precache de íconos. Eso da arranque rápido y tolerancia a micro-cortes, **pero NO operación offline real**.

**Limitación arquitectónica:** Reflex mantiene todo el estado en el servidor y cada interacción viaja por WebSocket. Sin conexión, la app no puede ni agregar un producto al carrito. **No hay forma de hacer el POS actual offline sin salirse del modelo de Reflex.** Cualquier promesa de "funciona offline" con la arquitectura actual sería falsa.

Opciones reales, de menor a mayor esfuerzo:

| Opción | Esfuerzo | Qué da |
|---|---|---|
| **A. Página offline de cortesía** (SW sirve un fallback "sin conexión, reintentando…" con auto-retry) | Días | UX digna ante cortes; cero venta offline |
| **B. Modo servidor local (on-premises)**: el stack Docker ya corre completo en una PC del local; internet solo para el acceso remoto | Días (es empaquetado + licenciamiento) | Offline total *dentro del local* (la red LAN sigue viva aunque caiga internet). Es la vía más corta a "vender sin internet" |
| **C. POS offline-first satélite**: mini-app JS pura (PWA con IndexedDB) SOLO para el flujo de venta rápida — catálogo cacheado, cola de ventas local, endpoint REST de sincronización/reconciliación (numeración provisoria → definitiva al reconectar) | Semanas/meses | Venta offline real con sync. Requiere resolver conflictos de stock y numeración fiscal (los comprobantes fiscales NO pueden emitirse offline; quedan en cola como en el retry worker actual) |

**Recomendación:** implementar A ya (trivial), ofrecer B como SKU "local/híbrido" para clientes con mala conectividad, y solo encarar C si el mercado lo exige. Nota fiscal: tanto SUNAT como ARCA contemplan emisión diferida/contingencia — la cola de reintentos existente (`fiscal_retry_worker`) ya modela ese patrón, lo cual facilita C.

---

## 8. Facturación electrónica (Perú y Argentina)

**Estado: IMPLEMENTADA en código (Fase 1), pendiente de certificación formal y representaciones impresas completas.**

### Arquitectura (`app/services/billing_service.py` — patrón Strategy)
```
BillingStrategy (ABC)
├── NoOpBillingStrategy   → países sin billing (default, cero overhead)
├── SUNATBillingStrategy  → Perú vía Nubefact REST (OSE/PSE intermediario)
└── AFIPBillingStrategy   → Argentina vía WSAA + WSFEv1 SOAP directo
```
- Emisión **post-commit** de la venta (fail-safe: si la autoridad falla, la venta ya está persistida y el `FiscalDocument` queda en `error` para reintento).
- **Numeración atómica** con `SELECT … FOR UPDATE`; idempotencia (Nubefact rechaza duplicados; AFIP devuelve el mismo CAE); sync de secuencia AFIP.
- **Cuota mensual por plan:** trial=0, standard=500, professional=1000, enterprise=2000.
- Credenciales encriptadas (Fernet), worker de reintentos cada 30 min con jitter, sanitización de tokens en errores, `defusedxml`, validación de CUIT/RUC (`fiscal_validators.py`), UI de gestión en Configuración + página Documentos Fiscales + sección fiscal en Venta.
- **Perú:** mapeo IGV (gravado/exonerado/inafecto/gratuito), factura/boleta/NC/ND vía Nubefact.
- **Argentina:** WSAA completo (TRA→CMS/PKCS#7→LoginCms, token 12h cacheado, clave privada solo en memoria), WSFEv1 con letras A/B/C según condición fiscal (RI/monotributo).

### Lo que falta para producción fiscal real (backlog concreto)
**Perú (SUNAT vía Nubefact):**
1. Cuenta Nubefact de producción por tenant + pruebas en su sandbox con RUC real.
2. **Representación impresa**: el ticket debe incluir hash/QR y leyendas SUNAT — verificar que `receipt_service.py` imprima los campos que Nubefact devuelve (enlace PDF/XML/CDR o QR propio).
3. **Resumen diario de boletas y comunicaciones de baja**: Nubefact lo maneja, pero hay que exponer anulaciones desde la UI (hoy existe NC automática — validar el flujo de baja).
4. Plan B documentado si se quiere independencia de Nubefact: emisión directa a SUNAT exige XML UBL 2.1 + firma XAdES + manejo de CDR — es un proyecto grande; mantener OSE/PSE es la decisión correcta hoy.

**Argentina (ARCA — ex AFIP):**
1. **QR obligatorio (RG 4892/2020)** en toda representación impresa de comprobantes electrónicos: URL `https://www.afip.gob.ar/fe/qr/?p=<base64>` con JSON (ver, fecha, CUIT, ptoVta, tipoCmp, nroCmp, importe, moneda, ctz, tipoDocRec, nroDocRec, tipoCodAut, codAut). Verificar si `receipt_service.py` ya lo genera; si no, es el gap #1 de AR.
2. Ciclo de **homologación**: certificado X.509 en homo, alta de punto de venta WSFE, pruebas de cada CbteTipo (1,2,3,6,7,8,11,12,13) y luego cert de producción.
3. Tener en el radar: **FCE MiPyME** (WSFECRED) si algún tenant B2B lo pide, condición IVA del receptor (RG 5616, campo `CondicionIVAReceptorId` vigente desde 2025) — verificar que el payload WSFE la incluya.
4. Renombrar referencias de UI "AFIP" → "ARCA" (el organismo cambió de nombre a fines de 2024; los endpoints siguen siendo afip.gov.ar).

**Común:** monitoreo de vencimiento de certificados implementado — `get_cert_expiry_alerts()` en `alert_service.py` genera alertas WARNING/ERROR/CRITICAL visibles en el Dashboard al login cuando `cert_not_after` ≤30 días (`f90c0d9`).

---

## 9. Panel Owner (admin plataforma)

Funcional y completo para su alcance: gestión de empresas (suspender, extender trial, resetear password con generación segura), sección billing de plataforma, auditoría de acciones, modal de acciones con confirmación. Sirve también de puente al backoffice de TUWAYKIFOOD (`food_owner_client.py` vía `FOOD_ADMIN_API_SECRET`).

Mejoras: ver §5 (MFA, cuentas múltiples, rate limit Redis). Además: métricas de negocio (MRR, churn, empresas activas/7d) en el dashboard owner — hoy el owner ve empresas pero no tendencias.

---

## 10. Calidad, tests y CI/CD

- ~1.023 tests pytest (unit + integración + e2e ligero). Convención: MySQL local para dev en `:3306`, Docker MySQL en `:33306` — **son DBs distintas, no confundir**.
- CI/CD: workflow `deploy-prod` con script SSH (`scripts/deploy-prod.sh`), smoke tests (`smoke_deploy.sh`, `smoke_live.py`), canary runbook, rollback compose (`docker-compose.rollback.yml`), auto-sync de env vars nuevas desde `.env.example` (⚠️ variables sensibles deben ir comentadas en `.env.example` para no auto-sincarse — lección aprendida en `c530a7c`).
- Servidor de prueba AWS: `ubuntu@52.15.161.245` (repos `~/sist-ventas-trebor` y `~/sist-food`; deploy de a uno por vez).

Mejoras: (1) job de CI que corra pytest en PR (si no existe ya — verificar `.github/workflows/`), (2) coverage gate (~existe `.coverage` local), (3) test de carga periódico con `scripts/stress_concurrency.py` antes de releases grandes.

---

## 11. Hallazgos priorizados (plan de acción)

| # | Prioridad | Área | Acción |
|---|---|---|---|
| 1 | **P1** | Seguridad | MFA/TOTP en Owner + allowlist IP en NPM para admin.tuwayki.app |
| 2 | **P1** | Fiscal AR | QR RG 4892 en representación impresa + campo condición IVA receptor (RG 5616); luego homologación ARCA completa |
| 3 | **P1** | Fiscal PE | Validar representación impresa Nubefact (QR/hash/leyendas) + flujo de bajas/resumen diario en UI |
| 4 | **P2** | Offline | Fallback offline del SW (opción A) + definir oferta "servidor local" (opción B) |
| 5 | ~~P2~~ | Seguridad | ~~Owner rate-limit a Redis~~ ✅ `79c4d1b`; ~~CSP report-only~~ ✅; ~~quitar X-XSS-Protection~~ ✅; ~~confirmar HSTS~~ ✅ — TODO COMPLETADO |
| 6 | ~~P2~~ | Fiscal | ~~Alerta automática de certificados fiscales a <30 días de vencer~~ ✅ `f90c0d9` (2026-07-11) |
| 7 | ~~P2~~ | Infra | ~~Verificar backups offsite + cron activo; probar restore trimestral~~ ✅ S3 offsite + cron auto-install + health-check integrados en `deploy-prod.sh`; `backup_restore_verify.py` reescrito (auto-discovery + cleanup + Docker). Se activa solo con `S3_BUCKET=<bucket>` en `.env` |
| 8 | **P3** | Rendimiento | Rutina mensual slow-query→índices; evaluar `innodb_buffer_pool_size`; auditar tamaño de State |
| 9 | **P3** | Landing | JSON-LD; Lighthouse; considerar landing estática si crece tráfico |
| 10 | **P3** | Producto | 2FA opcional para admins tenant; métricas MRR/churn en Owner; multi-sucursal Food (futuro confirmado, no agendado) |
| 11 | ~~P3~~ | Limpieza | ~~`default.conf` obsoleto (puerto 8000); `.gitignore` para dev.err/.coverage/e2e_screenshots~~ ✅ `79c4d1b` |

---

## 12. Guía de continuidad (para la próxima IA o dev)

### Reglas del proyecto (NO negociables)
1. **Idioma UI:** español latinoamericano neutro. Sin voseo argentino (nada de "tenés/hacés").
2. **Nunca `reflex run` para reiniciar en el flujo normal:** el entorno de referencia es Docker (`docker compose build && docker compose up -d`). Dos MySQL: Docker `:33306` ≠ local `:3306`.
3. **Multi-tenant:** todo acceso a datos dentro de `tenant_context()`; `tenant_bypass()` solo para owner/jobs con justificación.
4. **Ventas y TUWAYKIFOOD son repos independientes.** Código compartido → `tuwayki-core` (vendorizado en `_vendor/`).
5. **Push dual:** los cambios se pushean a `main` y a la rama de deploy (`docker-deploy-prod`) según el flujo vigente.
6. **Variables nuevas** van a `.env.example`; si son secretos/específicas de entorno, **comentadas** (el deploy auto-sinca las no comentadas al `.env` del servidor).

### Comandos esenciales (Windows dev)
```bash
# Tests (venv del proyecto)
~/Sistema-de-Ventas/.venv/Scripts/pytest.exe -q

# Stack local completo
docker compose -f docker-compose.local.yml up -d --build

# Migraciones manuales
alembic upgrade head

# Deploy servidor de prueba (uno a la vez)
ssh ubuntu@52.15.161.245   # repos: ~/sist-ventas-trebor , ~/sist-food
```

### Env vars críticas (ver `.env.example` para la lista completa)
`AUTH_SECRET_KEY` (≥32 chars; **rotarla invalida credenciales fiscales encriptadas**), `DB_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `REDIS_PASSWORD`, `APP_SURFACE` (landing|app|owner|all), `OWNER_ADMIN_EMAIL` + `OWNER_ADMIN_PASSWORD_HASH`, `FOOD_API_URL` + `FOOD_ADMIN_API_SECRET` (puente a TUWAYKIFOOD), `GA4_MEASUREMENT_ID`/`META_PIXEL_ID` (landing), `TENANT_STRICT` (dejar en 1), `FISCAL_RETRY_INTERVAL`/`FISCAL_RETRY_ENABLED`.

### Gotchas conocidos del stack
- MySQL 8: cuidado con columnas generadas; SQLModel es incompatible con `from __future__ import annotations` en modelos.
- Reflex emite un warning falso-positivo de schema — ignorable (documentado en memoria del proyecto).
- Windows: worktrees de git tienen pitfalls con el venv (usar el venv del repo principal para pytest).
- Reflex 0.9.x sirve frontend+API en un único proceso `:3000` (NPM apunta ahí; no existe más el `:8000` separado).

### Dónde leer más
`docs/SYSTEM_FULL_DOCUMENTATION.md` (funcional), `docs/DEPLOYMENT_SECURITY.md`, `docs/NGINX_PROXY_MANAGER.md`, `docs/CANARY_ROLLOUT_RUNBOOK.md`, `docs/PERFORMANCE_OPTIMIZATION_REPORT.md`, `docs/RESPONSIVE_AUDIT.md`, y este archivo como índice maestro.

---

*Generado por auditoría integral del 2026-07-05 sobre HEAD `c530a7c`. Las auditorías previas (Rounds 1–3, 148+ hallazgos) están cerradas; este documento refleja el estado posterior a esas correcciones.*
