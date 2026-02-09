# TUWAYKIAPP - Documentación Completa del Sistema

Versión de referencia: febrero 2026

## 1. Propósito del sistema

TUWAYKIAPP es un ERP/POS multiempresa (multi-tenant) orientado a:

- ventas y cobros,
- inventario y compras,
- caja y auditoría,
- clientes y crédito,
- reservas de servicios/canchas,
- administración por roles/permisos.

El objetivo operativo es que cada cliente cree su propia compañía, sucursales y usuarios, y opere de forma aislada de otras empresas.

## 2. Arquitectura técnica

### 2.1 Stack

- Backend + frontend reactivo: Reflex (`app/app.py`).
- Persistencia: MySQL.
- ORM: SQLModel/SQLAlchemy.
- Migraciones: Alembic.
- Seguridad de autenticación: JWT + versionado de token.
- Rate limiting: Redis (preferido en prod) con fallback en memoria configurable.

### 2.2 Composición del estado

La aplicación usa un `State` único construido por composición de mixins:

- `app/state.py`
- `app/states/root_state.py`

Subestados principales:

- `AuthState`, `RegisterState`
- `InventoryState`, `IngresoState`, `PurchasesState`, `SuppliersState`
- `VentaState` + mixins `cart/payment/receipt/recent_moves`
- `CashState`, `HistorialState`, `ReportState`
- `ServicesState`
- `ClientesState`, `CuentasState`
- `ConfigState`, `DashboardState`, `BranchesState`, `UIState`

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

El aislamiento se soporta por:

- contexto tenant (`company_id`, `branch_id`) en `app/utils/tenant.py`,
- listeners ORM para filtrar consultas por tenant y validar inserts,
- uso consistente de `set_tenant_context(...)` en estados y servicios.

Regla operativa:

- toda lectura/escritura de entidades con `company_id` debe ejecutarse con contexto tenant activo.

## 4. Modelo de datos (resumen)

Modelos en `app/models/`.

### 4.1 Núcleo tenant y seguridad

- `Company`, `Branch`
- `User`, `Role`, `Permission`
- tablas pivote: `UserBranch`, `RolePermission`

### 4.2 Ventas, caja y reservas

- `Sale`, `SaleItem`, `SalePayment`, `SaleInstallment`
- `CashboxSession`, `CashboxLog`
- `FieldReservation`, `FieldPrice`
- `PaymentMethod`, `Currency`, `CompanySettings`

### 4.3 Inventario y compras

- `Product`, `ProductVariant`, `ProductBatch`, `ProductKit`, `PriceTier`
- `Category`, `Unit`, `StockMovement`
- `Supplier`, `Purchase`, `PurchaseItem`

### 4.4 Clientes y crédito

- `Client`
- cuotas y pagos por medio de `SaleInstallment` + servicios de crédito.

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

- Estado principal: `app/states/venta_state.py`
- Servicio transaccional: `app/services/sale_service.py`
- Características:
  - búsqueda por barcode/SKU,
  - validación de stock,
  - pagos simples y mixtos,
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
