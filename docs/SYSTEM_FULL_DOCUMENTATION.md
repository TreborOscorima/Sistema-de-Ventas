# TUWAYKISHOP - Documentación Completa del Sistema

Versión de referencia: julio 2026 (v4.3)

> **Marca.** **TUWAYKISHOP** es el producto de gestión/POS de la marca madre **TUWAYKIAPP**. El ecosistema de la marca incluye además **TUWAYKIFOOD** (gestión para restaurantes, repositorio independiente) y **TUWAYKILIFE** (gestión de clínicas, *próximamente*). El núcleo multi-tenant compartido (contexto de tenant, aislamiento por empresa/sucursal, RBAC base) vive en el paquete **tuwayki-core**.

## 1. Propósito del sistema

TUWAYKISHOP es un ERP/POS multiempresa (multi-tenant) orientado a:

- ventas y cobros,
- motor de pricing (listas de precios, promociones, impuestos),
- inventario y compras (variantes, lotes FEFO, reposición automática),
- presupuestos/cotizaciones convertibles a venta,
- facturación electrónica multi-país (SUNAT/AFIP),
- caja y auditoría,
- clientes y crédito,
- reservas de servicios/canchas,
- administración por roles/permisos.

El objetivo operativo es que cada cliente cree su propia compañía, sucursales y usuarios, y opere de forma aislada de otras empresas. Cada sucursal maneja su propio stock, precios/márgenes y configuración (papel de impresión, leyenda legal).

## 2. Arquitectura técnica

### 2.1 Stack

- Backend + frontend reactivo: Reflex 0.9.4 (`app/app.py`).
- Núcleo multi-tenant compartido: paquete `tuwayki-core` (contexto de tenant, listeners ORM, RBAC base).
- Persistencia: MySQL 8.0.
- ORM: SQLModel/SQLAlchemy 2.0.
- Migraciones: Alembic.
- Seguridad de autenticación: JWT + versionado de token + refresh tokens con rotación.
- Rate limiting: Redis (preferido en prod) con fallback en memoria configurable.
- Reportes/impresión: ReportLab (PDF) + OpenPyXL (Excel) + impresión nativa in-app (iframe).
- Despliegue: Docker multi-stage (landing/sys/admin) + Nginx Proxy Manager.

### 2.2 Composición del estado

La aplicación usa un `State` único construido por composición de mixins:

- `app/state.py`
- `app/states/root_state.py`

Subestados principales:

- `AuthState`, `RegisterState`
- `InventoryState` (paquete `inventory/`), `IngresoState`, `PurchasesState`, `SuppliersState`, `ReorderState`
- `VentaState` (paquete `venta/`, mixins `cart/payment/receipt/recent_moves`)
- `CashState` (paquete `cash/`), `HistorialState`, `ReportState`
- `PriceListState`, `PromotionsState`, `TaxState`, `QuotationState` (comercial)
- `BillingState`, `OwnerState` (fiscal / plataforma)
- `ServicesState`
- `ClientesState`, `CuentasState`
- `ConfigState`, `DashboardState`, `BranchesState`, `UIState`

> Los states de mayor tamaño (`venta`, `cash`, `inventory`) están divididos en subpaquetes por mixins; los archivos `venta_state.py`/`cash_state.py`/`inventory_state.py` se mantienen como alias de retrocompatibilidad.

### 2.3 Flujo de páginas y rutas

Definidas en `app/app.py`:

- Públicas: `/`, `/registro`, `/cambiar-clave`, `/periodo-prueba-finalizado`, `/cuenta-suspendida`
- Operativas: `/dashboard`, `/ingreso`, `/compras`, `/venta`, `/caja`, `/inventario`, `/historial`, `/reportes`, `/servicios`, `/clientes`, `/cuentas`, `/configuracion`

En cada carga se ejecutan validaciones comunes (`_common_on_load`):

- permisos/roles,
- estado de suscripción y trial,
- forzado de cambio de contraseña,
- carga de catálogos base.

## 3. Multi-tenant y aislamiento

El aislamiento se soporta (vía `tuwayki-core`, reexpuesto en `app/utils/tenant.py`) por:

- contexto tenant (`company_id`, `branch_id`) en `contextvars` mediante `set_tenant_context(...)`,
- listeners ORM (`do_orm_execute` + `with_loader_criteria`) para filtrar consultas por tenant y validar inserts,
- `tenant_bypass()` para operaciones de plataforma (Owner) que deben ver todas las empresas.

Regla operativa:

- toda lectura/escritura de entidades con `company_id` debe ejecutarse con contexto tenant activo.

> **Nota de implementación (v4.3).** Los criterios de tenant deben inyectarse con variables de **closure** (rastreadas por SQLAlchemy vía `bindparam`), **nunca** con argumentos por defecto de lambda: un default-arg hornea el `branch_id`/`company_id` de la primera consulta en la cache de sentencias del engine, lo que provocaba que al cambiar de sucursal el POS no encontrara productos hasta refrescar. Con closures, alternar sucursales A→B→C funciona sin refrescar la página.

## 4. Modelo de datos (resumen)

Modelos en `app/models/`.

### 4.1 Núcleo tenant y seguridad

- `Company`, `Branch`
- `User`, `Role`, `Permission`
- tablas pivote: `UserBranch`, `RolePermission`

> **Config por empresa/sucursal.** `Branch.consumer_defense_legend` (override por sucursal) y `CompanySettings.consumer_defense_legend` (global) definen la leyenda legal del ticket. `CompanySettings` guarda además el tamaño de papel de impresión y el margen de ganancia global/por-sucursal.

### 4.2 Ventas, caja y reservas

- `Sale`, `SaleItem`, `SalePayment`, `SaleInstallment`
- `SaleReturn`, `SaleReturnItem` (devoluciones parciales/totales con reversión de stock)
- `CashboxSession`, `CashboxLog`
- `FieldReservation`, `FieldPrice`
- `PaymentMethod`, `Currency`, `CompanySettings`

### 4.3 Inventario y compras

- `Product`, `ProductVariant`, `ProductBatch`, `ProductKit`, `ProductAttribute`, `PriceTier`
- `Category`, `Unit`, `StockMovement`
- `Supplier`, `Purchase`, `PurchaseItem`, `PurchaseOrder`, `PurchaseOrderItem`

> Cada sucursal tiene su propia fila de `Product`; los productos transferidos conservan precio/margen propios por sucursal. Ver `app/services/transfer_service.py`.

### 4.4 Clientes y crédito

- `Client` (con segmento y lista de precios asignada)
- cuotas y pagos por medio de `SaleInstallment` + servicios de crédito.

### 4.5 Pricing, promociones e impuestos

- `PriceList`, `PriceListItem` (listas nominadas asignadas por cliente)
- `Promotion`, `PromotionProduct` (4 tipos: PERCENTAGE, FIXED_AMOUNT, BUY_X_GET_Y, NTH_UNIT_DISCOUNT)
- `CompanyTaxRate` (tasas por empresa con presets por país)
- Resolución unificada en `app/services/pricing.py`: PriceList → Tier → base → promoción → impuesto.

### 4.6 Presupuestos y facturación electrónica

- `Quotation`, `QuotationItem` (ciclo draft→sent→accepted→converted, convertibles a `Sale`)
- `CompanyBillingConfig`, `FiscalDocument`, `DocumentLookupCache`, `PlatformBillingSettings`
- Emisión vía Strategy Pattern (SUNAT/Nubefact para PE, AFIP WSAA+WSFEv1 para AR).

## 5. Módulos funcionales

### 5.1 Registro y onboarding

- Página: `app/pages/registro.py`
- Estado: `app/states/register_state.py`
- Crea automáticamente:
  - compañía,
  - sucursal inicial,
  - usuario administrador,
  - configuración inicial de empresa.
- Trial configurable por entorno usando `TRIAL_DAYS`.

### 5.2 Autenticación y RBAC

- Estado: `app/states/auth_state.py`
- JWT con `cid` (company_id) y versionado (`token_version`).
- Rutas protegidas por permisos y guards por módulo.
- Gestión de usuarios/roles desde configuración.

### 5.3 Ventas (POS)

- Estado principal: paquete `app/states/venta/` (mixins `cart`/`payment`/`receipt`/`recent_moves`); `venta_state.py` es alias legacy.
- Servicio transaccional: `app/services/sale_service.py`
- Motor de precios: `app/services/pricing.py` (misma fuente de verdad que el preview del carrito).
- Impresión: `app/utils/print_helper.py` (iframe nativo) + `app/utils/receipt_format.py` (papel térmico/A4).
- Características:
  - búsqueda por barcode/SKU con autocompletado,
  - validación de stock por sucursal,
  - **precio por sucursal**: el ítem se re-resuelve contra la BD al seleccionar (respeta listas, tiers y promociones), evitando precios corruptos por el round-trip al cliente,
  - pagos simples y mixtos (efectivo, tarjetas, Yape/Plin/transferencia, wallet),
  - emisión de comprobante fiscal (Boleta/Factura) e **impresión nativa in-app** con el papel configurado (térmico o A4),
  - **leyenda de Defensa del Consumidor** según sucursal (override) o global,
  - integración con caja y logs.

### 5.4 Reservas/servicios

- Estado: `app/states/services_state.py`
- Flujos:
  - crear reserva,
  - registrar adelantos/pagos,
  - cobro completo con método de pago,
  - impacto en `Sale`, `SalePayment`, `SaleItem`, `CashboxLog`.

### 5.5 Caja y auditoría

- Estado: `app/states/cash_state.py`
- Control de apertura/cierre por sesión, movimientos y arqueo.
- Integración con ventas y reservas.

### 5.6 Inventario y compras

- Estados: `inventory_state.py`, `ingreso_state.py`, `purchases_state.py`
- Soporte para productos simples, variantes y lotes.
- Movimientos y trazabilidad de stock.

### 5.7 Clientes y cuentas corrientes

- Estados: `clientes_state.py`, `cuentas_state.py`
- Servicio de deuda/crédito: `app/services/credit_service.py`
- Cobranza de cuotas, validaciones de sobrepago y actualización de deuda.

### 5.8 Reportes y dashboard

- Estado de reportes: `app/states/report_state.py`
- Servicio analítico: `app/services/report_service.py`
- Dashboard y alertas: `app/states/dashboard_state.py`, `app/services/alert_service.py`

### 5.9 Módulos comerciales y fiscales

- **Pricing/Promociones/Impuestos:** `app/services/pricing.py`, `app/services/tax_service.py`; estados `price_list_state.py`, `promotions_state.py`, `tax_state.py`.
- **Presupuestos/Cotizaciones:** `quotation_state.py` + `app/services/quotation_service.py` (conversión directa a venta).
- **Reposición automática:** `reorder_state.py` + `app/services/reorder_service.py` (OC por proveedor preferido bajo `min_stock_alert`).
- **Devoluciones:** `app/services/return_service.py` (reversión de stock + egreso en caja + nota de crédito).
- **Etiquetas PDF:** `app/services/label_service.py` (tamaños 50x30/70x40/100x60mm; A4/térmico 58/80mm).
- **Facturación electrónica:** `app/services/billing_service.py` (Strategy SUNAT/AFIP/NoOp), `afip_wsaa.py`, `afip_wsfe.py`; worker `app/tasks/fiscal_retry_worker.py`.
- **Owner backoffice:** `owner_state.py` (gestión de empresas, planes, billing de plataforma, auditoría).

### 5.10 Configuración

- Estado: `app/states/config_state.py`; sucursales en `branches_state.py`.
- Datos de empresa/sucursales, usuarios y roles (RBAC), monedas, unidades, métodos de pago, impuestos.
- **Impresión:** tamaño de papel (térmico 58/80/57mm, ancho personalizado en mm o A4) global y por sucursal.
- **Leyenda Defensa del Consumidor:** global y por sucursal (override), con presets por provincia (Argentina).
- **Margen de ganancia:** global de empresa y opcional por sucursal.

## 6. Configuración de entorno

Variables base en `.env.example`:

- DB: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`
- Auth: `AUTH_SECRET_KEY`
- Entorno: `ENV`, `PUBLIC_API_URL`
- Trial: `TRIAL_ENFORCEMENT`, `TRIAL_DAYS`
- Rate limit: `REDIS_URL`, `ALLOW_MEMORY_RATE_LIMIT_FALLBACK`
- Seguridad de password: `PASSWORD_REQUIRE_*`

Regla para producción:

- `ENV=prod`
- `AUTH_SECRET_KEY` fuerte
- `REDIS_URL` activo
- `ALLOW_MEMORY_RATE_LIMIT_FALLBACK=0`

## 7. Scripts operativos

Todos en `scripts/`.

### 7.1 Calidad y readiness

- `smoke_live.py`: smoke funcional end-to-end multi-tenant.
- `ops_readiness_check.py`: chequeo de salud operativa (DB, alembic, backup, logs, Redis, alert pipeline).
- `stress_concurrency.py`: stress de ventas/reservas en DB de prueba.

### 7.2 Backups y datos

- `backup_db.py`: backup/restauración MySQL.
- `backup_restore_verify.py`: restauración a DB temporal y validación de conteos.
- `release_reset_db.py`: limpieza controlada para lanzamiento (con dry-run y confirmación fuerte).
- `cleanup_stress_data.py`: limpia empresas de stress (`STRESS-*`).

## 8. Calidad y pruebas

Suite con `pytest`.

Comando estándar:

```bash
python -m pytest -q
```

CI:

- workflow: `.github/workflows/tests.yml`
- valida dependencias, compilación y tests en cada push/PR.

## 9. Seguridad y cumplimiento operativo

Guías:

- `docs/DEPLOYMENT_SECURITY.md`
- `docs/CANARY_ROLLOUT_RUNBOOK.md`

Controles implementados:

- RBAC por tenant,
- rate limiting de login,
- validaciones y sanitización de inputs,
- trazabilidad de caja y ventas,
- migraciones versionadas.

## 10. Flujo recomendado de despliegue

1. Provisionar cloud + MySQL + Redis.
2. Configurar `.env` de producción.
3. Ejecutar migraciones:

```bash
alembic upgrade head
```

4. Ejecutar checks:

```bash
python scripts/ops_readiness_check.py --require-redis --backup-max-age-hours 24
python scripts/smoke_live.py
```

5. Ejecutar canary según `docs/CANARY_ROLLOUT_RUNBOOK.md`.

## 11. `plan.md`: qué es y para qué sirve

`plan.md` es un roadmap histórico de evolución del producto:

- útil para contexto de fases y deuda técnica,
- no reemplaza documentación operativa ni runbooks de producción.

Para operación diaria y despliegue, usar principalmente:

- `docs/SYSTEM_FULL_DOCUMENTATION.md`
- `docs/DEPLOYMENT_SECURITY.md`
- `docs/CANARY_ROLLOUT_RUNBOOK.md`

## 12. Criterio de “sistema documentado”

Este proyecto queda documentado en cuatro niveles:

1. Overview funcional y técnico (este documento).
2. Seguridad y hardening (`DEPLOYMENT_SECURITY`).
3. Operación de release gradual (`CANARY_ROLLOUT_RUNBOOK`).
4. Roadmap histórico (`plan.md`) como referencia de producto.
