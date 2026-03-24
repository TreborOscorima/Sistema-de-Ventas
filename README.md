# TUWAYKIAPP: Sistema Integral de Gestion (ERP/POS)

**Version:** 3.0 (Multi-Country Electronic Billing)
**Tecnologia:** Python / Reflex / MySQL / Docker
**Autor:** Trebor Oscorima

---

## 1. Vision General

**TUWAYKIAPP** es una plataforma SaaS multi-tenant de gestion empresarial (ERP) y Punto de Venta (POS) disenada para comercios, PYMES y centros deportivos en Latinoamerica.

La version **v3.0** incorpora **Facturacion Electronica** para Peru (SUNAT/Nubefact) y Argentina (AFIP), convirtiendo al sistema en una solucion fiscal completa lista para produccion.

### Capacidades Principales

* **SaaS Multi-tenant:** Aislamiento por empresa y sucursal con RBAC granular.
* **Punto de Venta (POS):** Ventas rapidas con codigos de barras, pagos mixtos y emision de comprobantes.
* **Facturacion Electronica:** Emision de Facturas, Boletas y Notas de Credito ante SUNAT (Peru) y AFIP (Argentina).
* **Gestion Financiera:** Sesiones de caja, arqueo automatico y auditoria de movimientos.
* **Inventario Avanzado:** Variantes (talla/color), lotes con vencimiento y ajuste fisico por SKU.
* **Compras y Proveedores:** Documentos de compra, trazabilidad de costos y gestion de proveedores.
* **Clientes y Creditos:** Limites de credito, cuotas, cobranza y cuentas corrientes.
* **Servicios y Reservas:** Agenda visual para canchas deportivas con ciclo completo de pago.
* **Reportes y Exportacion:** Consolidados por periodo con descarga Excel/PDF.
* **Owner Backoffice:** Panel de administracion de plataforma independiente para gestion de empresas, planes y billing.
* **Despliegue Docker:** Arquitectura de 5 contenedores con Nginx Proxy Manager.

### Novedades v3.0 (2026)

* **Facturacion Electronica Peru:** Integracion completa con Nubefact/SUNAT (REST API).
* **Facturacion Electronica Argentina:** WSAA + WSFEv1 SOAP con certificados digitales.
* **Validadores fiscales:** RUC con checksum SUNAT, CUIT con digito verificador Ley 20.594.
* **Encriptacion de credenciales:** Fernet + PBKDF2 (600k iteraciones) para certificados y tokens.
* **Worker de reintentos:** Procesamiento automatico de documentos fiscales fallidos.
* **Consulta RUC/DNI:** Integracion con APIs de consulta de documentos (apis.net.pe).
* **Pagina Documentos Fiscales:** Listado con filtros, paginacion y modal de detalle.
* **Concepto AFIP configurable:** Productos (1), Servicios (2) o Ambos (3).
* **598 tests automatizados** con pytest (validadores fiscales, AFIP, billing, seguridad).

### Novedades v2.x (2026)

* **Trazabilidad de caja:** `CashboxLog` vincula movimientos con ventas y marca anulaciones.
* **Prioridad por codigo de barras** ante descripciones duplicadas.
* **Creditos seguros:** bloqueo de concurrencia y validacion de sobrepago en cuotas.
* **Reservas con pagos mixtos:** desglose real por metodo y registro consistente en caja.
* **Variantes y lotes en ingresos:** Tallas/Colores y Lotes/Vencimientos con UI dinamica.
* **Normalizacion horaria:** Persistencia UTC + zona IANA del negocio para vistas.
* **Auditoria de seguridad integral:** 360 grados con puntuacion por area.

---

## 2. Arquitectura del Sistema

### Stack Tecnologico

| Capa | Tecnologia |
|:-----|:-----------|
| **Frontend** | React (compilado por Reflex desde Python) |
| **Backend** | Python 3.11 + Reflex 0.8.26 |
| **Base de Datos** | MySQL 8.0 + SQLModel/SQLAlchemy 2.0 |
| **Migraciones** | Alembic 1.18 |
| **Cache / Rate Limiting** | Redis 7 |
| **HTTP Client** | httpx (async) para APIs fiscales |
| **Criptografia** | cryptography (Fernet + PBKDF2) |
| **Autenticacion** | JWT (PyJWT) + bcrypt |
| **Estilos** | Tailwind CSS v3 |
| **Reportes** | ReportLab (PDF) + OpenPyXL (Excel) |
| **Testing** | pytest + pytest-asyncio + pytest-mock |
| **Despliegue** | Docker Compose + Nginx Proxy Manager |
| **ASGI Server** | Granian |

### Arquitectura Multi-Tenant

```
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

### Patron Strategy — Facturacion Electronica

```
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
| **Clientes** | `Client`, `SaleInstallment` | Clientes, limites de credito y cuotas. |
| **Inventario** | `Product`, `ProductVariant`, `ProductBatch`, `ProductKit`, `Category`, `StockMovement`, `Unit`, `PriceTier` | Catalogo, variantes, lotes, kits y movimientos. |
| **Compras** | `Supplier`, `Purchase`, `PurchaseItem` | Documentos de compra y proveedores. |
| **Ventas** | `Sale`, `SaleItem`, `SalePayment`, `CashboxSession`, `CashboxLog` | Ventas, pagos mixtos y auditoria de caja. |
| **Servicios** | `FieldReservation`, `FieldPrice` | Reservas deportivas y tarifas. |
| **Configuracion** | `Currency`, `PaymentMethod`, `CompanySettings` | Monedas, metodos de pago y datos del negocio. |
| **Billing** | `CompanyBillingConfig`, `FiscalDocument`, `DocumentLookupCache` | Config fiscal por empresa, documentos emitidos y cache de consultas RUC/DNI. |
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
|   |   |-- billing.py       # CompanyBillingConfig, FiscalDocument
|   |   |-- lookup_cache.py  # DocumentLookupCache
|   |   +-- ...              # auth, sales, inventory, company, etc.
|   |-- pages/               # Vistas de la aplicacion
|   |   |-- documentos_fiscales.py  # Listado de documentos fiscales
|   |   +-- ...              # dashboard, venta, inventario, etc.
|   |-- services/            # Servicios de negocio
|   |   |-- billing_service.py           # Strategy Pattern (SUNAT/AFIP/NoOp)
|   |   |-- afip_wsaa.py                 # WSAA: autenticacion CMS/PKCS#7
|   |   |-- afip_wsfe.py                 # WSFEv1: FECAESolicitar SOAP
|   |   |-- document_lookup_service.py   # Consulta RUC/DNI/CUIT
|   |   +-- ...              # sale_service, report_service, etc.
|   |-- states/              # Logica de negocio (Reflex State)
|   |   |-- billing_state.py    # Config fiscal del usuario
|   |   |-- owner_state.py      # Backoffice del Owner
|   |   |-- venta_state.py      # POS + seleccion Boleta/Factura
|   |   +-- ...                 # auth, dashboard, inventory, etc.
|   |-- tasks/               # Workers en background
|   |   +-- fiscal_retry_worker.py  # Reintentos de docs fiscales
|   |-- utils/               # Utilidades
|   |   |-- crypto.py            # Encriptacion Fernet + PBKDF2
|   |   |-- fiscal_validators.py # Validadores RUC/CUIT/URL/Environment
|   |   |-- db_seeds.py          # Datos iniciales idempotentes
|   |   +-- ...                  # timezone, tenant, rate_limit, etc.
|   |-- enums.py             # Enums: FiscalStatus, ReceiptType, etc.
|   +-- app.py               # Punto de entrada y rutas
|-- tests/                   # 598 tests automatizados
|   |-- test_billing.py          # Tests de billing service
|   |-- test_afip.py             # Tests de AFIP (WSAA + WSFEv1)
|   |-- test_fiscal_validators.py # Tests de validadores fiscales
|   |-- test_security_fixes.py   # Tests de seguridad
|   +-- ...                      # sale_service, credit, etc.
|-- docker-compose.yml       # Orquestacion de 5 contenedores
|-- Dockerfile               # Imagen Python 3.11-slim
|-- rxconfig.py              # Configuracion Reflex + DB
|-- requirements.txt         # 62 dependencias Python
+-- .env.example             # Template de variables de entorno
```

---

## 4. Guia de Instalacion

### Prerrequisitos

* Python 3.11 o superior
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

# 2. Levantar servicios
docker-compose up -d

# Servicios desplegados:
# - tuwayki_mysql    (MySQL 8.0, puerto 3306)
# - tuwayki_redis    (Redis 7, puerto 6379)
# - tuwayki_landing  (Landing page, puerto 3000)
# - tuwayki_sys      (Aplicacion SaaS, puerto 3000)
# - tuwayki_admin    (Owner backoffice, puerto 3000)
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
* Alertas operativas: stock bajo, cuotas vencidas, caja abierta prolongada.
* Graficos de tendencia y ranking de productos.

### Punto de Venta (POS)
* Registro rapido con codigos de barras o busqueda manual.
* Selector de comprobante: **Nota de Venta**, **Boleta** o **Factura**.
* Pagos mixtos (efectivo + tarjeta + Yape/Plin/transferencia).
* Emision automatica de documento fiscal al seleccionar Boleta o Factura.
* Validacion de caja abierta antes de operar.
* Impresion de tickets termicos estandarizados.

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

### Ingreso de Productos
* Documento de compra con series/numero y proveedor.
* Variantes (Talla/Color) y Lotes (Vencimiento) con UI dinamica.
* Ajuste automatico de stock y costos.

### Compras y Proveedores
* Historial de documentos con busqueda y filtros.
* Gestion de proveedores con validacion RUC/CUIT.

### Inventario
* CRUD completo con categorizacion dinamica.
* Variantes por SKU con stock separado por Talla/Color.
* Ajuste fisico por SKU o descripcion.
* Exportacion de inventario valorizado con desglose.

### Clientes y Cuentas Corrientes
* Gestion de clientes con limites de credito.
* Cuotas pendientes, pagadas y vencidas.
* Cobranza con pagos parciales o totales.

### Gestion de Caja
* Sesiones estrictas por usuario (apertura/cierre).
* Arqueo automatico con totales esperados vs. registrados.
* Movimientos con trazabilidad (sale_id + is_voided).

### Historial de Ventas
* Consulta de ventas con desglose de items.
* Estadisticas por metodo de pago.
* Reimpresion de tickets.
* Exportacion Excel con una fila por item.

### Reportes
* Consolidados por periodo (dia/semana/mes).
* Detalle por item y por variante.
* Inventario valorizado por SKU.
* Exportacion Excel con formatos legibles.

### Servicios (Reservas)
* Agenda visual para canchas deportivas.
* Ciclo completo: Reserva -> Adelanto -> Pago Final.
* Constancias de reserva con formato ticket.
* Pagos mixtos integrados con caja.

### Configuracion
* Datos de empresa y sucursales.
* Gestion de usuarios y roles (RBAC).
* Monedas, unidades de medida y metodos de pago.
* Facturacion electronica (datos fiscales del usuario).
* Suscripcion y plan.

### Owner Backoffice
* Panel independiente para administracion de plataforma.
* Gestion de empresas: planes, suscripciones, estados.
* Configuracion tecnica de billing: ambiente, series, certificados, tokens.
* Auditoria de acciones con log persistente.

---

## 6. Facturacion Electronica — Guia de Activacion

### Peru (SUNAT/Nubefact)

1. Registrarse en [nubefact.com](https://www.nubefact.com) y obtener URL + Token de API.
2. En SUNAT, habilitar emision electronica y autorizar al OSE (Nubefact).
3. En el **Owner Panel** > Billing: configurar URL, Token, series (F001/B001), ambiente.
4. En **Configuracion > Facturacion**: ingresar RUC, razon social y direccion fiscal.
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
# Suite completa (598 tests)
python -m pytest -q

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
| Validadores fiscales (RUC/CUIT/URL) | 35 | Checksum, prefijos, formatos |
| AFIP (WSAA + WSFEv1) | 30 | Auth, XML, CAE, errores |
| Billing service (Strategy) | 45+ | Quota, Nubefact, retry, QR |
| Seguridad (tenant isolation) | 20+ | FOR UPDATE, info leakage, RBAC |
| Ventas y creditos | 50+ | Flujos completos, concurrencia |
| Otros modulos | 400+ | Inventario, caja, reportes |
| **Total** | **598** | |

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

* Todas las queries filtradas por `company_id` + `branch_id`.
* Numeracion fiscal atomica con `SELECT ... FOR UPDATE`.
* Credenciales fiscales separadas por empresa.
* Contexto de tenant validado en cada operacion.

### RBAC y Autenticacion

* JWT con versionado de tokens para invalidacion.
* bcrypt para hash de contrasenas.
* Rate limiting con Redis (fallback a memoria).
* Sanitizacion XSS en inputs.
* Validacion de contrasenas configurable (mayusculas, digitos, especiales).

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
| Seguridad | 85/100 | Robusto |
| Base de Datos | 90/100 | Optimizado |
| Backend/Estado | 88/100 | Limpio |
| Frontend/UX | 85/100 | Consistente |
| Arquitectura | 92/100 | Bien estructurado |
| Testing | 80/100 | 598 tests |
| Billing/Fiscal | 90/100 | Multi-pais |

---

## Documentacion Adicional

* Indice documental: `docs/README.md`
* Guia completa del sistema: `docs/SYSTEM_FULL_DOCUMENTATION.md`
* Seguridad de despliegue: `docs/DEPLOYMENT_SECURITY.md`
* Runbook de canary/rollback: `docs/CANARY_ROLLOUT_RUNBOOK.md`

---

&copy; 2025-2026 TUWAYKIAPP. Desarrollado con Python y Reflex.
