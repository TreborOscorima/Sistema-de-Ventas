# TUWAYKIAPP: Sistema Integral de Gestion (ERP/POS)

**Version:** 4.1 (Auto-pricing + State Refactor)
**Tecnologia:** Python 3.13 / Reflex 0.9.2 / MySQL 8.0 / Docker
**Autor:** Trebor Oscorima

---

## 1. Vision General

**TUWAYKIAPP** es una plataforma SaaS multi-tenant de gestion empresarial (ERP) y Punto de Venta (POS) diseñada para comercios, PYMES y centros deportivos en Latinoamerica.

La version **v4.1** incorpora auto-calculo de precio de venta desde margen efectivo y un refactor de states en paquetes por mixins. La **v4.0** agrego un **Motor de Pricing completo** (Listas de Precios, Promociones avanzadas, Impuestos por empresa) y un sistema de **Presupuestos/Cotizaciones** convertibles a venta, sobre la base de la Facturacion Electronica multi-pais incorporada en v3.0.

### Capacidades Principales

* **SaaS Multi-tenant:** Aislamiento por empresa y sucursal con RBAC granular.
* **Punto de Venta (POS):** Ventas rapidas con codigos de barras, pagos mixtos y emision de comprobantes.
* **Motor de Pricing:** Listas de precios nominadas, precios por volumen (PriceTier), promociones automaticas y un unico punto de verdad para resolucion de precio.
* **Promociones Avanzadas:** PERCENTAGE, FIXED_AMOUNT, BUY_X_GET_Y y NTH_UNIT_DISCOUNT con scope por producto/categoria/todos.
* **Presupuestos/Cotizaciones:** Documentos pre-venta con ciclo de vida completo (borrador → enviado → aceptado → convertido a venta) y exportacion PDF.
* **Impuestos por Empresa:** Tasas configurables por empresa (IGV, IVA, IVA-I) con presets por pais y desglose en recibos.
* **Facturacion Electronica:** Emision de Facturas, Boletas y Notas de Credito ante SUNAT (Peru) y AFIP (Argentina).
* **Inventario Avanzado:** Variantes (talla/color), lotes FEFO con vencimiento, atributos dinamicos (EAV), importacion masiva CSV/Excel y etiquetas PDF listas para imprimir.
* **Reposicion Automatica:** Deteccion de productos bajo umbral con generacion de ordenes de compra sugeridas por proveedor.
* **Devoluciones:** Parciales o totales con reversion de stock y registro en caja.
* **Gestion Financiera:** Sesiones de caja, arqueo por denominacion y auditoria de movimientos.
* **Compras y Proveedores:** Documentos de compra, ordenes de compra y trazabilidad de costos.
* **Clientes y Creditos:** Limites de credito, cuotas, cobranza y cuentas corrientes con segmento de cliente.
* **Servicios y Reservas:** Agenda visual para canchas deportivas con ciclo completo de pago.
* **Reportes y Exportacion:** Consolidados por periodo con descarga Excel/PDF.
* **Owner Backoffice:** Panel independiente para gestion de empresas, planes y billing de plataforma.
* **Despliegue Docker:** Arquitectura multi-stage de 5 contenedores con Nginx Proxy Manager.

### Novedades v4.1 (2026)

* **Auto-precio desde margen:** En el formulario de ingreso de productos, si el producto no tiene precio de venta configurado, el sistema calcula automaticamente `sale_price = cost × (1 + margen_efectivo)` al confirmar el ingreso.
* **State refactor — paquetes por mixins:** Los tres states de mayor tamano se dividieron en subpaquetes para mejorar mantenibilidad:
  * `app/states/cash/` — 6 mixins: `_session`, `_close`, `_delete`, `_petty_cash`, `_reports`, `_history`
  * `app/states/inventory/` — 5 mixins: `_product`, `_search`, `_adjustment`, `_export`, `_label`
  * `app/states/venta/` — 4 mixins: `cart`, `payment`, `receipt`, `recent_moves`
  * Los archivos legacy `cash_state.py` e `inventory_state.py` se mantienen como alias de retrocompatibilidad.
* **Multi-vertical:** `business_vertical` en `CompanySettings` permite adaptar la UI del POS segun el tipo de negocio (retail, deportivo, servicios).
* **1024 tests** — 2 tests adicionales para auto-precio y validaciones de margen.

### Novedades v4.0 (2026)

* **Motor de Pricing (single source of truth):** `app/services/pricing.py` — resolucion de precio en jerarquia Lista → Tier → Base, compartida entre POS y previsualizacion del carrito.
* **Listas de Precios nominadas:** PriceList + PriceListItem; asignacion por cliente; precios con 4 decimales.
* **Promociones completas:** NTH_UNIT_DISCOUNT (Nth unidad con X% off), cap por transaccion, horario de aplicacion, monto minimo y multi-producto.
* **Impuestos por empresa:** CompanyTaxRate con presets por pais (PE, AR, MX, CO, CL, US); desglose pre/post-impuesto en recibos y etiquetas.
* **Presupuestos/Cotizaciones:** Ciclo completo draft→sent→accepted→converted; PDF; integracion POS con conversion directa a venta.
* **Etiquetas PDF supermercado:** Tres tamanos (50x30, 70x40, 100x60mm); precio pre-impuesto; codigo de barras; soporte A4, termico 58mm y 80mm.
* **Segmento de cliente:** Campo de segmento en ficha de cliente para campanas y listas de precio diferenciadas.
* **1024 tests automatizados** — suite ampliada con pricing engine, promotion consumption, tax service, label service, quotations y variante picker.

### Novedades v3.0 (2026)

* **Facturacion Electronica Peru:** Integracion completa con Nubefact/SUNAT (REST API).
* **Facturacion Electronica Argentina:** WSAA + WSFEv1 SOAP con certificados digitales.
* **Encriptacion de credenciales:** Fernet + PBKDF2 (600k iteraciones) para certificados y tokens.
* **Worker de reintentos:** Procesamiento automatico de documentos fiscales fallidos.
* **Consulta RUC/DNI:** Integracion con APIs de consulta de documentos.
* **Pagina Documentos Fiscales:** Listado con filtros, paginacion y modal de detalle.
* **PlatformBillingSettings:** Credenciales maestras Nubefact a nivel plataforma (singleton Owner).

### Novedades v2.x (2026)

* **Reposicion automatica:** ReorderService detecta productos bajo `min_stock_alert` y genera PurchaseOrder por proveedor preferido.
* **Devoluciones parciales/totales:** SaleReturn/SaleReturnItem con reversion de stock y nota de credito automatica.
* **Arqueo de caja por denominacion:** Conteo de efectivo al cierre con totales esperados vs. registrados.
* **Importacion masiva de productos:** CSV/Excel con validacion y ajuste de stock.
* **Kit/Combo en POS:** Explosion de kits en carrito con validacion de stock por componente.
* **Selectores de lote y variante en POS:** Eleccion manual al agregar producto.
* **Atributos dinamicos (EAV):** ProductAttribute para rubros con multiples caracteristicas.
* **Refresh tokens JWT** con rotacion para sesiones de larga duracion.
* **Trazabilidad de caja:** CashboxLog vincula movimientos con ventas y marca anulaciones.
* **Creditos seguros:** Bloqueo de concurrencia y validacion de sobrepago en cuotas.
* **Sidebar flyout:** Submenu flotante en rail mode al colapsar el sidebar.
* **Reflex 0.9.2:** Migracion rx.Model → SQLModel, tema Radix como plugin, eliminacion de state_auto_setters.

---

## 2. Arquitectura del Sistema

### Stack Tecnologico

| Capa | Tecnologia |
|:-----|:-----------|
| **Frontend** | React (compilado por Reflex desde Python) |
| **Backend** | Python 3.13 + Reflex 0.9.2 |
| **Base de Datos** | MySQL 8.0 + SQLModel/SQLAlchemy 2.0 |
| **Migraciones** | Alembic 1.18 |
| **Cache / Rate Limiting** | Redis 7 |
| **HTTP Client** | httpx (async) para APIs fiscales |
| **Criptografia** | cryptography (Fernet + PBKDF2) |
| **Autenticacion** | JWT (PyJWT) con refresh tokens + bcrypt |
| **Estilos** | Tailwind CSS v3 + Radix Theme |
| **Reportes** | ReportLab (PDF) + OpenPyXL (Excel) |
| **Testing** | pytest + pytest-asyncio + pytest-mock |
| **Despliegue** | Docker Compose multi-stage + Nginx Proxy Manager |
| **ASGI Server** | Granian |

### Arquitectura Multi-Tenant

```text
Landing (tuwayki.app)     App (app.tuwayki.app)     Owner (admin.tuwayki.app)
       |                         |                          |
       v                         v                          v
  [Nginx Proxy Manager - SSL/TLS termination]
       |                         |                          |
  tuwayki_landing           tuwayki_sys              tuwayki_admin
  APP_SURFACE=landing       APP_SURFACE=app          APP_SURFACE=owner
       |                         |                          |
       +------------+------------+------------+-------------+
                    |                         |
              [MySQL 8.0]               [Redis 7]
              tenant-scoped             rate limiting
              company_id +              session cache
              branch_id
```

### Motor de Pricing — Jerarquia de Resolucion

```text
Para cada item del carrito / venta:

  1. PriceListItem   (lista asignada al cliente)   — mayor prioridad
  2. PriceTier       (precio por volumen)
  3. Product.sale_price                            — precio base fallback

  Luego, sobre el precio base resuelto:

  4. Promotion       (descuento automatico — PERCENTAGE / FIXED_AMOUNT /
                      BUY_X_GET_Y / NTH_UNIT_DISCOUNT)

  5. CompanyTaxRate  (tasa de impuesto por empresa — IGV, IVA, etc.)

  >> app/services/pricing.py es la unica fuente de verdad <<
     Tanto sale_service como el preview del carrito llaman este modulo.
```

### Patron Strategy — Facturacion Electronica

```text
BillingStrategy (ABC)
 |-- NoOpBillingStrategy      -> Paises sin billing / billing deshabilitado
 |-- SUNATBillingStrategy     -> Peru via Nubefact REST API
 +-- AFIPBillingStrategy      -> Argentina via WSAA + WSFEv1 SOAP

BillingFactory.get_strategy(country_code) -> instancia concreta

emit_fiscal_document() -> orquestacion:
  1. Valida cuota mensual (rate limit por plan)
  2. Asigna numeracion atomica (SELECT ... FOR UPDATE)
  3. Invoca la strategy en background
  4. Persiste FiscalDocument con resultado (authorized/error)
```

### Modelo de Datos

| Modulo | Entidades | Descripcion |
|:-------|:----------|:------------|
| **Auth/RBAC** | `User`, `Role`, `Permission`, `RolePermission`, `UserBranch` | Usuarios, roles, permisos granulares y asignacion multi-sucursal. |
| **Empresa** | `Company`, `Branch` | Empresas y sucursales con aislamiento de datos. |
| **Clientes** | `Client`, `SaleInstallment` | Clientes con segmento, limites de credito y cuotas. |
| **Inventario** | `Product`, `ProductVariant`, `ProductBatch`, `ProductKit`, `ProductAttribute`, `Category`, `StockMovement`, `Unit`, `PriceTier` | Catalogo, variantes, lotes FEFO, kits, atributos EAV y movimientos. |
| **Pricing** | `PriceList`, `PriceListItem` | Listas de precios nominadas asignadas por cliente. |
| **Promociones** | `Promotion`, `PromotionProduct` | Reglas de descuento automatico (4 tipos, 3 scopes). |
| **Impuestos** | `CompanyTaxRate` | Tasas configurables por empresa con presets por pais. |
| **Compras** | `Supplier`, `Purchase`, `PurchaseItem`, `PurchaseOrder`, `PurchaseOrderItem` | Documentos de compra, ordenes y proveedores. |
| **Ventas** | `Sale`, `SaleItem`, `SalePayment`, `CashboxSession`, `CashboxLog` | Ventas, pagos mixtos y auditoria de caja. |
| **Devoluciones** | `SaleReturn`, `SaleReturnItem` | Devoluciones parciales/totales con reversion de stock. |
| **Presupuestos** | `Quotation`, `QuotationItem` | Documentos pre-venta convertibles a Sale. |
| **Servicios** | `FieldReservation`, `FieldPrice` | Reservas deportivas y tarifas. |
| **Configuracion** | `Currency`, `PaymentMethod`, `CompanySettings` | Monedas, metodos de pago y datos del negocio. |
| **Billing** | `CompanyBillingConfig`, `FiscalDocument`, `DocumentLookupCache`, `PlatformBillingSettings` | Config fiscal por empresa, documentos emitidos, cache RUC/DNI y credenciales maestras de plataforma. |
| **Auditoria** | `OwnerAuditLog` | Log de acciones del Owner backoffice. |

---

## 3. Estructura del Proyecto

```text
Sistema-de-Ventas/
|-- .github/workflows/       # CI con GitHub Actions
|-- alembic/                 # Migraciones de base de datos
|-- app/
|   |-- components/          # UI reutilizable (Sidebar, Modales, Tablas)
|   |-- models/              # Modelos SQLModel (tablas MySQL)
|   |   |-- billing.py       # CompanyBillingConfig, FiscalDocument, PlatformBillingSettings
|   |   |-- inventory.py     # Product, ProductVariant, ProductBatch, ProductKit, ProductAttribute
|   |   |-- price_lists.py   # PriceList, PriceListItem
|   |   |-- promotions.py    # Promotion, PromotionProduct (4 tipos de descuento)
|   |   |-- quotations.py    # Quotation, QuotationItem
|   |   |-- taxes.py         # CompanyTaxRate con presets por pais
|   |   |-- purchases.py     # Supplier, Purchase, PurchaseOrder
|   |   |-- sales.py         # Sale, SaleItem, SaleReturn, CashboxSession
|   |   +-- ...              # auth, client, company, owner, etc.
|   |-- pages/               # Vistas de la aplicacion
|   |   |-- etiquetas.py          # Generador de etiquetas PDF
|   |   |-- listas_precios.py     # CRUD de listas de precios
|   |   |-- presupuestos.py       # Presupuestos/Cotizaciones
|   |   |-- promociones.py        # CRUD de promociones
|   |   |-- reposicion.py         # Reposicion automatica de inventario
|   |   |-- documentos_fiscales.py# Listado de documentos fiscales
|   |   +-- ...              # dashboard, venta, inventario, caja, etc.
|   |-- services/            # Servicios de negocio
|   |   |-- pricing.py                   # Motor de pricing (single source of truth)
|   |   |-- tax_service.py               # CRUD de tasas de impuesto
|   |   |-- label_service.py             # Generador PDF de etiquetas
|   |   |-- quotation_service.py         # Presupuestos y conversion a Sale
|   |   |-- reorder_service.py           # Reposicion automatica por proveedor
|   |   |-- return_service.py            # Devoluciones con reversion de stock
|   |   |-- billing_service.py           # Strategy Pattern (SUNAT/AFIP/NoOp)
|   |   |-- afip_wsaa.py                 # WSAA: autenticacion CMS/PKCS#7
|   |   |-- afip_wsfe.py                 # WSFEv1: FECAESolicitar SOAP
|   |   |-- alert_service.py             # Alertas de stock bajo y cuotas
|   |   |-- credit_service.py            # Credito y cuotas de clientes
|   |   |-- receipt_service.py           # Generacion de recibos PDF
|   |   +-- ...              # sale_service, report_service, etc.
|   |-- states/              # Logica de negocio (Reflex State)
|   |   |-- cash/                  # Caja — 6 mixins (_session, _close, _delete, _petty_cash, _reports, _history)
|   |   |-- inventory/             # Inventario — 5 mixins (_product, _search, _adjustment, _export, _label)
|   |   |-- venta/                 # POS — 4 mixins (cart, payment, receipt, recent_moves)
|   |   |-- price_list_state.py    # Listas de precios
|   |   |-- promotions_state.py    # Gestion de promociones
|   |   |-- quotation_state.py     # Presupuestos
|   |   |-- reorder_state.py       # Reposicion automatica
|   |   |-- tax_state.py           # Configuracion de impuestos
|   |   |-- ui_state.py            # Estado de UI (flyout, modales)
|   |   |-- billing_state.py       # Config fiscal del usuario
|   |   |-- owner_state.py         # Backoffice del Owner
|   |   |-- venta_state.py         # Alias legacy → venta/ package
|   |   +-- ...                    # auth, dashboard, clientes, config, etc.
|   |-- tasks/               # Workers en background
|   |   +-- fiscal_retry_worker.py  # Reintentos de docs fiscales
|   |-- utils/               # Utilidades
|   |   |-- pricing.py / pricing helpers # Integrados en services/pricing.py
|   |   |-- tax_presets.py           # Presets de tasas IGV/IVA por pais
|   |   |-- stock.py                 # recalculate_stock_totals
|   |   |-- payment.py               # Validaciones de pago
|   |   |-- formatting.py            # Formateo de moneda y numeros
|   |   |-- dates.py                 # Helpers de fechas
|   |   |-- exports.py               # Export Excel unificado
|   |   |-- crypto.py                # Encriptacion Fernet + PBKDF2
|   |   |-- fiscal_validators.py     # Validadores RUC/CUIT/URL
|   |   |-- performance.py           # query_timer
|   |   +-- ...                      # timezone, tenant, rate_limit, etc.
|   |-- enums.py             # Enums: SaleStatus, ReturnReason, PaymentMethodType, etc.
|   +-- app.py               # Punto de entrada y rutas
|-- tests/                   # 1024 tests automatizados
|   |-- test_pricing_engine.py       # Motor de pricing y jerarquia
|   |-- test_promotion_consumption.py# Consumo y cap de promociones
|   |-- test_tax_service.py          # CRUD de tasas y presets
|   |-- test_label_service.py        # Generador de etiquetas PDF
|   |-- test_quotation_service.py    # Presupuestos y conversion
|   |-- test_reorder_service.py      # Reposicion automatica
|   |-- test_venta_variant_picker.py # Picker de variantes en POS
|   |-- test_venta_batch_picker.py   # Picker de lotes en POS
|   |-- test_venta_kit_explosion.py  # Explosion de kits en carrito
|   |-- test_billing.py              # Billing service (Strategy)
|   |-- test_afip.py                 # AFIP (WSAA + WSFEv1)
|   |-- test_fiscal_validators.py    # Validadores RUC/CUIT/URL
|   |-- test_security_fixes.py       # Seguridad (tenant isolation)
|   +-- ...                          # sale_service, credit, inventario, caja, etc.
|-- docker-compose.yml           # Orquestacion principal (5 contenedores)
|-- docker-compose.local.yml     # Testing prod en Windows/local
|-- docker-compose.prod.yml      # Despliegue produccion
|-- docker-compose.rollback.yml  # Rollback de emergencia
|-- Dockerfile                   # Multi-stage build (builder + runtime) python:3.11-slim base image
|-- rxconfig.py                  # Configuracion Reflex + DB
|-- requirements.txt             # Dependencias Python
+-- .env.example                 # Template de variables de entorno
```

---

## 4. Guia de Instalacion

### Prerrequisitos

* Python 3.13 o superior
* MySQL 8.0
* Redis 7 (produccion) o memoria (desarrollo)
* Git
* Docker y Docker Compose (para despliegue en produccion)

### Instalacion Local (Desarrollo)

```bash
# 1. Clonar repositorio
git clone https://github.com/TreborOscorima/Sistema-de-Ventas.git
cd Sistema-de-Ventas

# 2. Entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env
# Editar .env con credenciales de MySQL y AUTH_SECRET_KEY

# 5. Base de datos
# Crear BD vacia: CREATE DATABASE sistema_ventas;
reflex db init
reflex db makemigrations --message "deploy_inicial"
reflex db migrate

# 6. Iniciar
reflex run
# Acceder a http://localhost:3000
```

### Despliegue con Docker (Produccion)

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con valores de produccion

# 2. Levantar servicios (build multi-stage)
docker-compose -f docker-compose.prod.yml up -d

# Servicios desplegados:
# - tuwayki_mysql    (MySQL 8.0, puerto 3306)
# - tuwayki_redis    (Redis 7, puerto 6379)
# - tuwayki_landing  (Landing page)
# - tuwayki_sys      (Aplicacion SaaS — POS, ERP, billing)
# - tuwayki_admin    (Owner backoffice)

# Testing local equivalente a prod (Windows):
docker-compose -f docker-compose.local.yml up -d
```

### Variables de Entorno Principales

```env
# Base de Datos
DB_USER=app
DB_PASSWORD=secreto_seguro
DB_HOST=tuwayki_mysql
DB_PORT=3306
DB_NAME=sistema_ventas

# Seguridad (OBLIGATORIO en produccion)
AUTH_SECRET_KEY=clave_minimo_32_caracteres_aleatoria
OWNER_ADMIN_PASSWORD_HASH=$2b$12$...  # bcrypt hash

# Superficie de la app (landing | app | owner)
APP_SURFACE=app

# URLs publicas
PUBLIC_API_URL=https://api.tuwayki.app
PUBLIC_SITE_URL=https://tuwayki.app
PUBLIC_APP_URL=https://app.tuwayki.app

# Redis
REDIS_URL=redis://tuwayki_redis:6379/0

# Entorno
ENV=prod
```

---

## 5. Modulos del Sistema

### Dashboard
* KPIs en tiempo real: ventas, caja, reservas y credito.
* Alertas operativas: stock bajo, lotes por vencer, cuotas vencidas, caja abierta prolongada.
* Graficos de tendencia y ranking de productos.
* Panel de lotes proximos a vencer con dias restantes.

### Punto de Venta (POS)
* Registro rapido con codigos de barras o busqueda manual.
* Selector de comprobante: **Nota de Venta**, **Boleta** o **Factura**.
* Pagos mixtos (efectivo + tarjeta + Yape/Plin/transferencia + wallet).
* Resolucion automatica de precio: lista del cliente → tier → base.
* Aplicacion automatica de promociones activas con preview en carrito.
* Seleccion manual de variante (talla/color) y lote al agregar producto.
* Explosion de kits/combos con validacion de stock por componente.
* Emision automatica de documento fiscal al seleccionar Boleta o Factura.
* Desglose de impuesto en ticket de venta.
* Validacion de caja abierta antes de operar.

### Motor de Pricing
* `app/services/pricing.py` — unico punto de resolucion de precio.
* Jerarquia: PriceListItem → PriceTier → Product.sale_price.
* Promociones con 4 tipos: PERCENTAGE, FIXED_AMOUNT, BUY_X_GET_Y, NTH_UNIT_DISCOUNT.
* Cap por transaccion y monto minimo configurable en cada promocion.
* Misma logica en POS y previsualizacion de presupuesto, sin divergencia.

### Listas de Precios
* Listas nominadas (Mayorista, VIP, Distribuidores, etc.) con `is_active`.
* Asignacion por cliente — se aplica automaticamente en POS y presupuesto.
* Precios con 4 decimales para precision en multiples monedas.
* Vista con columna de precio base y diferencial.

### Promociones
* Cuatro tipos de descuento: porcentual, monto fijo, 3x2 (BUY_X_GET_Y) y Nth-unidad.
* Scope: todos los productos, categoria o producto especifico.
* Horario de aplicacion (dias de semana y rango de horas).
* Monto minimo de compra y cap maximo de descuento por transaccion.
* Control de `max_uses` y contador `current_uses`.

### Impuestos por Empresa
* CompanyTaxRate: multiples tasas por empresa (IGV 18%, IVA 21%, IVA-I 10.5%, etc.).
* Presets automaticos al crear empresa segun pais (PE, AR, MX, CO, CL, US).
* Tasa default para documentos fiscales y desglose en recibos.
* Precio pre-impuesto y post-impuesto en etiquetas y ticket de venta.

### Presupuestos/Cotizaciones
* Ciclo de vida completo: draft → sent → accepted/rejected → converted.
* Expiracion automatica por fecha de vencimiento configurable.
* Conversion directa a Sale con un clic desde el POS o historial.
* Generacion de PDF con misma calidad de presentacion que los recibos.
* Soporte de descuento por item y snapshot de producto para auditoria.
* Integracion con Idempotency Key para evitar duplicados.

### Etiquetas PDF
* Tres tamanos: small (50x30mm), medium (70x40mm), large (100x60mm).
* Formatos de pagina: A4, termico 58mm y termico 80mm.
* Filtros: todos los productos, precio cambiado recientemente o sin barcode.
* Codigo de barras (EAN interno si el producto no tiene barcode valido).
* Muestra precio con y sin impuesto (disenio supermercado).
* Categorias normalizadas a MAYUSCULAS en filtros e impresion.

### Reposicion Automatica
* Deteccion de productos con stock <= `min_stock_alert` por sucursal.
* Agrupacion por proveedor preferido (`default_supplier_id`).
* Generacion de PurchaseOrder con cantidad sugerida (doble del umbral).
* Ciclo de vida de OC: borrador → enviado → convertido a compra / cancelado.

### Ingreso de Productos (Compras)
* Documento de compra con series/numero y proveedor.
* Variantes (Talla/Color) y Lotes (Vencimiento) con UI dinamica.
* Ajuste automatico de stock y costos.
* Importacion masiva CSV/Excel con validacion y mapeo de columnas.

### Inventario
* CRUD completo con categorizacion dinamica (MAYUSCULAS normalizadas).
* Variantes por SKU con stock separado por Talla/Color.
* Lotes FEFO con fecha de vencimiento y alertas de proximidad.
* Atributos dinamicos (EAV) para rubros con multiples caracteristicas.
* Umbral de stock bajo configurable por variante (`min_stock_alert`).
* Ajuste fisico por SKU o descripcion.
* Exportacion de inventario valorizado con desglose.
* Margen bruto calculado automaticamente en reportes.

### Devoluciones
* Devolucion parcial o total de items de una venta.
* Reversion de stock (variante, lote o producto segun el item).
* Registro en CashboxLog como egreso de caja.
* Nota de credito automatica al emitir devolucion de venta electronica.
* Motivo de devolucion (defectuoso, equivocado, cambio de opinion, etc.).

### Clientes y Cuentas Corrientes
* Gestion de clientes con limite de credito y segmento (VIP, mayorista, etc.).
* Asignacion de lista de precios por cliente.
* Cuotas pendientes, pagadas y vencidas.
* Cobranza con pagos parciales o totales.

### Gestion de Caja
* Sesiones estrictas por usuario (apertura/cierre).
* Arqueo de efectivo por denominacion al cierre con totales esperados.
* Movimientos con trazabilidad (sale_id + is_voided).
* Registro de devoluciones como egresos auditados.

### Historial de Ventas
* Consulta de ventas con desglose de items y promociones aplicadas.
* Estadisticas por metodo de pago.
* Devoluciones desde el historial con reversion automatica.
* Reimpresion de tickets.
* Exportacion Excel con una fila por item.

### Reportes
* Consolidados por periodo (dia/semana/mes).
* Detalle por item y por variante.
* Inventario valorizado por SKU con margen bruto.
* Reporte de devoluciones.
* Exportacion Excel con formatos legibles y unified export utility.

### Servicios (Reservas)
* Agenda visual para canchas deportivas.
* Ciclo completo: Reserva -> Adelanto -> Pago Final.
* Constancias de reserva con formato ticket.
* Pagos mixtos integrados con caja.

### Facturacion Electronica
* **Peru (SUNAT):** Emision via Nubefact REST API (Factura, Boleta, Nota de Credito).
* **Argentina (AFIP):** Emision via WSAA + WSFEv1 SOAP (Factura A/B/C, NC, ND).
* **Validaciones fiscales:** RUC (checksum SUNAT), CUIT (Ley 20.594), URL HTTPS.
* **Concepto AFIP configurable:** Productos (1), Servicios (2), Ambos (3).
* **Datos QR:** Generacion automatica (SUNAT pipe-separated, AFIP RG 4291/2018).
* **Reintentos automaticos:** Worker con exponential backoff (max 3 intentos).
* **Cuota mensual por plan:** trial=0, standard=500, professional=1000, enterprise=2000.
* **Pagina Documentos Fiscales:** Listado con filtros por estado/tipo/fecha, paginacion y detalle.
* **Credenciales encriptadas:** Certificados X.509 y tokens con Fernet + PBKDF2.
* **PlatformBillingSettings:** Una cuenta Nubefact maestra cubre todas las empresas PE del SaaS.

### Configuracion
* Datos de empresa y sucursales.
* Gestion de usuarios y roles (RBAC granular).
* Monedas, unidades de medida y metodos de pago.
* Tasas de impuesto por empresa con presets por pais.
* Facturacion electronica (datos fiscales del usuario).
* Suscripcion y plan.

### Owner Backoffice
* Panel independiente para administracion de plataforma.
* Gestion de empresas: planes, suscripciones, estados.
* Configuracion tecnica de billing: ambiente, series, certificados, tokens.
* Configuracion de PlatformBillingSettings (credenciales maestras Nubefact).
* Auditoria de acciones con log persistente.

---

## 6. Facturacion Electronica — Guia de Activacion

### Peru (SUNAT/Nubefact)

1. Registrarse en [nubefact.com](https://www.nubefact.com) y obtener URL + Token de API.
2. En SUNAT, habilitar emision electronica y autorizar al OSE (Nubefact).
3. En el **Owner Panel** > Platform Billing: configurar URL maestra y Token Nubefact integrador.
4. En **Configuracion > Facturacion** de cada empresa: ingresar RUC, razon social y direccion fiscal.
5. Probar en `sandbox` antes de cambiar a `production`.

### Argentina (AFIP)

1. Obtener CUIT + Clave Fiscal Nivel 3 en [afip.gob.ar](https://www.afip.gob.ar).
2. Adherir servicios WSAA y Facturacion Electronica (wsfe).
3. Generar certificado digital: `openssl genrsa` + `openssl req` -> subir CSR a AFIP.
4. Habilitar Punto de Venta electronico en AFIP.
5. En el **Owner Panel** > Billing: configurar punto de venta, condicion IVA, concepto, pegar certificado + clave privada.
6. En **Configuracion > Facturacion**: ingresar CUIT, razon social y direccion fiscal.
7. Probar en `sandbox` (homologacion) antes de cambiar a `production`.

### Worker de Reintentos

```bash
# Ejecucion manual
python -m app.tasks.fiscal_retry_worker

# Modo preview (sin ejecutar)
python -m app.tasks.fiscal_retry_worker --dry-run

# Cron cada 5 minutos (Linux)
*/5 * * * * cd /path/to/app && .venv/bin/python -m app.tasks.fiscal_retry_worker
```

---

## 7. Pruebas Automatizadas

### Ejecutar tests

```bash
# Suite completa (1024 tests)
python -m pytest -q

# Motor de pricing
python -m pytest tests/test_pricing_engine.py -v

# Promociones
python -m pytest tests/test_promotion_consumption.py -v

# Impuestos
python -m pytest tests/test_tax_service.py -v

# Etiquetas PDF
python -m pytest tests/test_label_service.py -v

# Presupuestos
python -m pytest tests/test_quotation_service.py -v

# Solo validadores fiscales
python -m pytest tests/test_fiscal_validators.py -v

# Solo AFIP
python -m pytest tests/test_afip.py -v

# Solo billing service
python -m pytest tests/test_billing.py -v

# Solo seguridad
python -m pytest tests/test_security_fixes.py -v
```

### Cobertura por area

| Area | Tests | Cobertura |
|:-----|------:|:----------|
| Motor de pricing (jerarquia + PriceList + Tier) | 40+ | Resolucion completa |
| Promociones (4 tipos + cap + consumption) | 30+ | Flujos y limites |
| Impuestos por empresa (CRUD + presets) | 20+ | Multi-pais |
| Etiquetas PDF (tamanos + filtros) | 20+ | Layout y datos |
| Presupuestos (ciclo de vida + conversion) | 25+ | DRAFT→CONVERTED |
| POS pickers (variante + lote + kit) | 30+ | Flujos de carrito |
| Reposicion automatica | 15+ | OC por proveedor |
| Validadores fiscales (RUC/CUIT/URL) | 35 | Checksum, prefijos |
| AFIP (WSAA + WSFEv1) | 30 | Auth, XML, CAE, errores |
| Billing service (Strategy) | 45+ | Quota, Nubefact, retry, QR |
| Seguridad (tenant isolation) | 20+ | FOR UPDATE, RBAC |
| Ventas y creditos | 50+ | Flujos completos |
| Otros modulos | 600+ | Inventario, caja, reportes |
| **Total** | **1024** | |

### CI/CD

GitHub Actions ejecuta la suite completa en cada push/PR via `.github/workflows/tests.yml`.

---

## 8. Seguridad

### Encriptacion de Credenciales Fiscales

| Aspecto | Implementacion |
|:--------|:---------------|
| Algoritmo | Fernet (AES-128-CBC + HMAC-SHA256) |
| Derivacion de clave | PBKDF2-HMAC-SHA256, 600,000 iteraciones |
| Salt | 16 bytes aleatorios por credencial |
| Almacenamiento | Columnas `Text` en MySQL (cifrado) |
| Clave maestra | `AUTH_SECRET_KEY` (variable de entorno) |
| Descifrado | Solo en memoria durante llamadas API |

### Aislamiento Multi-Tenant

* Todas las queries filtradas por `company_id` + `branch_id` via TenantMixin.
* Numeracion fiscal atomica con `SELECT ... FOR UPDATE`.
* Credenciales fiscales separadas por empresa.
* Contexto de tenant validado en cada operacion.
* Tasas de impuesto con scope empresa (sin branch_id — regimen fiscal por empresa).

### RBAC y Autenticacion

* JWT con versionado de tokens para invalidacion + refresh tokens con rotacion.
* bcrypt para hash de contrasenas.
* Rate limiting con Redis (fallback a memoria).
* Sanitizacion XSS en inputs.
* Validacion de contrasenas configurable (mayusculas, digitos, especiales).
* Privilegio especifico `view_labels` para acceso al modulo de etiquetas.

### Documentacion de Seguridad

Para despliegue en produccion, consulta:
* **[docs/DEPLOYMENT_SECURITY.md](docs/DEPLOYMENT_SECURITY.md)** — Headers HTTP, SSL/TLS, rate limiting, checklist.

---

## 9. Mantenimiento

### Migraciones de Base de Datos

```bash
# Con Reflex
reflex db makemigrations --message "descripcion_cambio"
reflex db migrate

# Con Alembic directo
alembic upgrade head
```

### Monitoreo de Performance

```python
from app.utils.performance import query_timer

async with query_timer("cargar_productos"):
    products = await session.exec(select(Product))
# Logea automaticamente si excede 1 segundo
```

### Tracking de Marketing (Landing)

```env
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
META_PIXEL_ID=123456789012345
```

Eventos: `view_landing`, `click_trial_cta`. Solo se cargan con consentimiento de cookies.

---

## 10. Auditoria de Codigo

| Area | Puntuacion | Estado |
|:-----|:----------:|:------:|
| Seguridad | 87/100 | Robusto |
| Base de Datos | 91/100 | Optimizado |
| Backend/Estado | 90/100 | Limpio |
| Frontend/UX | 87/100 | Consistente |
| Arquitectura | 93/100 | Bien estructurado |
| Testing | 92/100 | 1024 tests |
| Billing/Fiscal | 90/100 | Multi-pais |
| Pricing/Comercial | 90/100 | Single source of truth |

---

## Documentacion Adicional

* Indice documental: `docs/README.md`
* Guia completa del sistema: `docs/SYSTEM_FULL_DOCUMENTATION.md`
* Seguridad de despliegue: `docs/DEPLOYMENT_SECURITY.md`
* Runbook de canary/rollback: `docs/CANARY_ROLLOUT_RUNBOOK.md`

---

&copy; 2025-2026 TUWAYKIAPP. Desarrollado con Python y Reflex.
