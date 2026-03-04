# 📘 TUWAYKIAPP: Sistema Integral de Gestión (ERP/POS)

**Versión:** 2.0 (Stable - MySQL Persistence)  
**Tecnología:** Python / Reflex / MySQL  
**Autor:** Trebor Oscorima

---

## 1. 🚀 Visión General

**TUWAYKIAPP** es una solución tecnológica integral de gestión empresarial (ERP) y Punto de Venta (POS) diseñada para comercios y centros deportivos.

Esta versión **v2.0** marca un hito en la arquitectura del sistema al implementar una capa de persistencia robusta con **MySQL**, eliminando la volatilidad de los datos en memoria. El sistema garantiza la integridad transaccional de ventas, inventarios, cajas y reservas, permitiendo un despliegue seguro en entornos de producción local.

### 🌟 Capacidades Principales

*   **Persistencia Total:** Almacenamiento seguro en base de datos relacional para todos los módulos.
*   **Punto de Venta (POS):** Procesamiento de ventas con múltiples métodos de pago, control de stock en tiempo real y emisión de comprobantes térmicos estandarizados.
*   **Gestión Financiera:** Control estricto de sesiones de caja (Apertura/Cierre), auditoría de movimientos y estadísticas detalladas por método de pago.
*   **Compras y Proveedores:** Registro de documentos de compra, proveedores y trazabilidad de costos.
*   **Clientes y Cuentas Corrientes:** Gestión de clientes, límites de crédito, cuotas y cobranza.
*   **Reportes y Exportación:** Reportes consolidados y exportación a Excel por módulo.
*   **Gestión de Servicios:** Módulo especializado para alquiler de canchas deportivas con agenda visual, control de estados (Reserva -> Adelanto -> Pago) y emisión de constancias.
*   **Configuración Dinámica:** Gestión de monedas, unidades de medida y métodos de pago directamente desde la interfaz.
*   **Seguridad RBAC:** Control de acceso basado en roles y privilegios granulares.

### Novedades recientes (2026)

*   **Trazabilidad de caja:** `CashboxLog` vincula cada movimiento con su venta (`sale_id`) y marca anulaciones con `is_voided` para excluirlas de reportes sin perder auditoría.
*   **Ventas más precisas:** prioridad por código de barras ante descripciones duplicadas.
*   **Créditos más seguros:** bloqueo de concurrencia y validación de sobrepago en cuotas.
*   **Reservas con pagos mixtos:** desglose real por método y registro consistente en caja.
*   **Permisos reforzados:** altas/bajas de categorías protegidas por `edit_inventario`.
*   **Variantes y lotes en ingresos:** soporte de Tallas/Colores y Lotes/Vencimientos en compras con UI dinámica.
*   **Exportes por ítem:** reportes de Historial y Detalle de Transacciones con una fila por ítem vendido.
*   **Inventario por SKU:** exportación de inventario valorizado con desglose por variantes.
*   **Caja más legible:** listas de productos en exportes con saltos de línea y ajuste de texto.
*   **QA automatizado:** tests con pytest + CI en GitHub Actions.

---

## 2. 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura **Full-Stack en Python** utilizando el framework **Reflex**, que compila el frontend a React y gestiona el backend en Python puro.

### 🛠️ Stack Tecnológico

*   **Frontend/Backend:** Reflex (Python)
*   **Base de Datos:** MySQL 8.0
*   **ORM:** SQLModel (SQLAlchemy)
*   **Migraciones:** Alembic
*   **Estilos:** Tailwind CSS
*   **Reportes:** Generación de HTML/JS para impresión térmica.

### 📊 Modelo de Datos (E-R)

La estructura de datos se define en `app/models/` y se gestiona mediante migraciones automáticas:

| Módulo | Entidades Principales | Descripción |
| :--- | :--- | :--- |
| **Auth/RBAC** | `User`, `Role`, `Permission` | Usuarios, roles y permisos con control granular. |
| **Clientes & Crédito** | `Client`, `SaleInstallment` | Clientes, límites de crédito, cuotas y estado de deuda. |
| **Inventario** | `Product`, `ProductVariant`, `ProductBatch`, `Category`, `StockMovement`, `Unit` | Catálogo, variantes, lotes, movimientos y unidades de medida. |
| **Compras/Proveedores** | `Supplier`, `Purchase`, `PurchaseItem` | Documentos de compra y relación con proveedores. |
| **Ventas & Caja** | `Sale`, `SaleItem`, `SalePayment`, `CashboxSession`, `CashboxLog` | Ventas, pagos y auditoría de caja. |
| **Servicios** | `FieldReservation`, `FieldPrice` | Reservas de canchas y tarifas. |
| **Configuración** | `Currency`, `PaymentMethod`, `CompanySettings` | Monedas, métodos de pago y datos del negocio. |

---

## 3. 📦 Estructura del Proyecto

```text
Sistema-de-Ventas/
├── .github/             # Workflows de CI
│   └── workflows/       # GitHub Actions
├── alembic/             # Historial de migraciones de base de datos
├── app/
│   ├── components/      # Componentes UI reutilizables (Sidebar, Modales, Tablas)
│   ├── models/          # Definición de tablas y modelos SQLModel
│   ├── pages/           # Vistas de la aplicación (Frontend)
│   ├── schemas/         # DTOs y validaciones
│   ├── services/        # Servicios de negocio
│   ├── states/          # Lógica de negocio y gestión de estado (Backend)
│   │   ├── auth_state.py       # Autenticación y RBAC
│   │   ├── dashboard_state.py  # KPIs y alertas
│   │   ├── clientes_state.py   # Clientes
│   │   ├── cuentas_state.py    # Cuentas corrientes / cuotas
│   │   ├── ingreso_state.py    # Ingreso de productos
│   │   ├── purchases_state.py  # Compras
│   │   ├── suppliers_state.py  # Proveedores
│   │   ├── inventory_state.py  # Inventario
│   │   ├── cash_state.py       # Caja y movimientos
│   │   ├── historial_state.py  # Historial de ventas
│   │   ├── services_state.py   # Reservas y servicios
│   │   ├── report_state.py     # Reportes
│   │   ├── venta_state.py      # POS e impresión
│   │   ├── ui_state.py         # UI global
│   │   ├── root_state.py       # Estado raíz
│   │   ├── mixin_state.py      # Mixins compartidos
│   │   ├── cash/               # Subestados de caja
│   │   └── venta/              # Subestados de venta
│   ├── utils/           # Utilidades (Formatos, Fechas, Exports)
│   ├── enums.py         # Enums del dominio
│   └── app.py           # Punto de entrada
├── assets/              # Recursos estáticos
├── tests/               # Tests automatizados (pytest)
├── rxconfig.py          # Configuración del entorno y conexión BD
└── requirements.txt     # Dependencias
```

---

## 4. ⚙️ Guía de Instalación y Despliegue

### Prerrequisitos
*   Python 3.10 o superior.
*   Servidor MySQL 8.0 instalado y en ejecución.
*   Git.

### Pasos de Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/TreborOscorima/Sistema-de-Ventas.git
    cd Sistema-de-Ventas
    ```

2.  **Configurar Entorno Virtual:**
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/Mac:
    source .venv/bin/activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Base de Datos:**
    *   Crea una base de datos vacía en MySQL llamada `sistema_ventas`.
    *   Edita `rxconfig.py` con tus credenciales:
        ```python
        db_url="mysql+pymysql://USUARIO:PASSWORD@localhost:3306/sistema_ventas"
        ```

5.  **Ejecutar Migraciones (Inicialización):**
    Construye las tablas en la base de datos:
    ```bash
    reflex db init
    reflex db makemigrations --message "deploy_inicial"
    reflex db migrate
    ```

6.  **Iniciar el Sistema:**
    ```bash
    reflex run
    ```
    Accede a: `http://localhost:3000`

> **Nota:** Al primer inicio, el sistema poblará automáticamente las tablas de configuración (monedas, unidades, métodos de pago) gracias al método `ensure_default_data`.

### Tracking de Marketing (Landing `/sitio`)

Para habilitar analítica productiva en la landing:

```env
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
META_PIXEL_ID=123456789012345
```

Eventos instrumentados actualmente:
- `view_landing` (una vez por sesión)
- `click_trial_cta` (clics en CTAs clave de prueba)

Si no configuras esos IDs, la landing sigue funcionando y guarda eventos localmente para depuración.

---

## 5. 📖 Manual de Módulos

### 📊 Dashboard
*   **KPIs en tiempo real:** ventas, caja, reservas y crédito.
*   **Alertas operativas:** stock bajo, cuotas vencidas y caja abierta prolongada.
*   **Gráficos y ranking:** tendencias por período y top productos.

### 🛒 Punto de Venta (Ventas)
*   **Interfaz Ágil:** Diseñada para registro rápido mediante códigos de barras o búsqueda manual.
*   **Prioridad por código de barras:** evita colisiones cuando hay descripciones duplicadas.
*   **Validación de Caja:** Impide realizar ventas si no existe una sesión de caja abierta.
*   **Pagos Flexibles:** Soporta pagos mixtos (ej: parte efectivo, parte tarjeta) y registra el detalle exacto para el arqueo.
*   **Impresión:** Generación automática de tickets de venta estandarizados.
*   **Crédito controlado:** valida límites y evita sobrepagos en cuotas.

### 📥 Ingreso de Productos
*   **Documento de compra:** registro de ingreso con series/número y proveedor.
*   **Ajuste de stock:** actualiza existencias y costos de manera controlada.
*   **Detalle de ítems:** cantidades, unidad, precio de compra y venta.
*   **Variantes y Lotes:** ingreso por Talla/Color o por Lote/Vencimiento según categoría.
*   **Modo camaleónico:** el formulario se adapta automáticamente al tipo de producto escaneado.

### 🧾 Compras y Proveedores
*   **Registro de compras:** historial de documentos, búsqueda y filtros.
*   **Gestión de proveedores:** alta/edición/baja con validaciones de RUC/CUIT.
*   **Detalle de compras:** ver ítems y totales con moneda.

### 📦 Inventario
*   **Gestión Persistente:** CRUD completo de productos conectado directamente a MySQL.
*   **Categorización:** Creación dinámica de categorías que persisten entre sesiones.
*   **Permisos:** crear/eliminar categorías requiere privilegio `edit_inventario`.
*   **Variantes por SKU:** stock y movimientos separados por Talla/Color.
*   **Ajuste físico mejorado:** búsqueda por SKU o descripción con sugerencias de variantes.
*   **Reportes:** Exportación de inventario valorizado a Excel con desglose por variantes.

### 👥 Clientes
*   **Gestión de clientes:** datos básicos, límites de crédito y validaciones.
*   **Edición rápida:** actualización de datos desde la interfaz.

### 💳 Cuentas Corrientes
*   **Cuotas y pagos:** control de cuotas pendientes, pagadas y vencidas.
*   **Cobranza:** registro de pagos parciales o totales por cuota.

### 💵 Gestión de Caja e Historial
*   **Sesiones:** Control estricto de turnos por usuario.
*   **Arqueo:** Cierre de caja con cálculo automático de totales esperados vs. registrados.
*   **Historial Detallado:** Consulta de movimientos históricos con desglose de ítems y estadísticas precisas por método de pago (Efectivo, Tarjeta, Yape/Plin).
*   **Anulaciones seguras:** movimientos marcados como anulados y excluidos de totales/reportes.
*   **Reimpresión:** Capacidad de reimprimir tickets de ventas pasadas.
*   **Exportes legibles:** productos listados con saltos de línea y celdas con ajuste de texto.

### 📈 Reportes
*   **Reportes consolidados:** ingresos por método de pago, cierres de caja y ventas.
*   **Detalle por ítem:** historial y transacciones con una fila por ítem vendido.
*   **Inventario por variantes:** valorizado por SKU para análisis real de stock.
*   **Exportación:** descarga en Excel según módulo con formatos legibles.

### ⚽ Servicios (Reservas)
*   **Agenda Visual:** Planificador interactivo para canchas deportivas.
*   **Ciclo de Vida:** Controla el flujo completo: `Reserva` -> `Adelanto` -> `Pago Final`.
*   **Constancias:** Emisión de "Constancia de Reserva" incluso para reservas sin pago inicial, con formato ticket profesional.
*   **Integración Contable:** Los pagos de reservas se inyectan automáticamente en la caja activa.
*   **Pagos mixtos:** desglose real por método y registro consistente en caja.

### 🔧 Configuración
*   **Panel Administrativo:** Permite gestionar usuarios, roles, monedas, unidades y métodos de pago sin intervención técnica.
*   **Seguridad:** gestión de roles/privilegios con RBAC.

### 🔐 Acceso y Seguridad
*   **Login y cambio de contraseña:** flujo seguro de autenticación.
*   **Bloqueo por sesión:** tokens versionados para invalidación controlada.

---

## 6. Pruebas Automatizadas y CI

### Tests locales
```bash
python -m pytest -q
```

### Subconjuntos útiles
```bash
python -m pytest -q tests/test_sale_service.py tests/test_credit_service.py
```

### CI
GitHub Actions ejecuta los tests en cada push/PR desde `.github/workflows/tests.yml`.

---

## 7. 🔒 Seguridad y Deployment

### Documentación de Seguridad

Para despliegue en producción, consulta la guía completa en:

📄 **[docs/DEPLOYMENT_SECURITY.md](docs/DEPLOYMENT_SECURITY.md)**

Incluye:
- Configuración de headers HTTP seguros (Nginx/Caddy)
- Variables de entorno requeridas
- Configuración SSL/TLS con Let's Encrypt
- Rate limiting con Redis
- Checklist de producción

Para producción con **dominios tuwayki.app** (landing, sys, admin) y **Nginx Proxy Manager**, ver:

📄 **[docs/NGINX_PROXY_MANAGER.md](docs/NGINX_PROXY_MANAGER.md)** — Proxy Hosts para tuwayki.app, sys.tuwayki.app, admin.tuwayki.app y redirect www.

### Validación de Contraseñas

Para activar validación robusta de contraseñas en producción, añade a `.env`:

```env
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

### Monitoreo de Performance

El sistema incluye utilidades para detectar queries lentas:

```python
from app.utils.performance import query_timer

async with query_timer("cargar_productos"):
    products = await session.exec(select(Product))
# Automáticamente logea si excede 1 segundo
```

Configurar umbrales en `.env`:
```env
SLOW_QUERY_THRESHOLD=1.0
CRITICAL_QUERY_THRESHOLD=5.0
```

---

## 8. Mantenimiento

### Actualizaciones de Base de Datos
Si se realizan cambios en `app/models/`, se debe actualizar el esquema:

```bash
reflex db makemigrations --message "descripcion_cambio"
reflex db migrate
```

Si usas Alembic directamente:
```bash
alembic upgrade head
```

---

## 9. 📊 Auditoría de Código

El sistema ha pasado una auditoría integral de código (360°) con los siguientes resultados:

| Área | Puntuación | Estado |
|:-----|:----------:|:------:|
| Seguridad | 85/100 | ✅ Robusto |
| Base de Datos | 90/100 | ✅ Optimizado |
| Backend/Estado | 88/100 | ✅ Limpio |
| Frontend/UX | 85/100 | ✅ Consistente |
| Arquitectura | 92/100 | ✅ Bien estructurado |
| Testing | 75/100 | ✅ Mejorado |

**Fortalezas clave:**
- JWT con versionado de tokens para invalidación
- Rate limiting (Redis/memoria)
- RBAC granular con permisos por rol
- Sanitización XSS en inputs
- Tipos `Decimal` para precisión monetaria
- Mixins para composición de estados

---
© 2025 TUWAYKIAPP. Desarrollado con ❤️ usando Reflex.

---

## Documentación recomendada

Para documentación actualizada por capas:

- Índice documental: `docs/README.md`
- Guía completa del sistema: `docs/SYSTEM_FULL_DOCUMENTATION.md`
- Seguridad de despliegue: `docs/DEPLOYMENT_SECURITY.md`
- Nginx Proxy Manager (tuwayki.app): `docs/NGINX_PROXY_MANAGER.md`
- Runbook de canary/rollback: `docs/CANARY_ROLLOUT_RUNBOOK.md`
- Roadmap histórico: `plan.md`
