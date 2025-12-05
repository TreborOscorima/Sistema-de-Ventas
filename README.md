📘 StockFlow: Sistema Integral de Gestión (ERP/POS)

Versión: 2.0 (Stable - MySQL Persistence)
Tecnología: Python / Reflex / MySQL
Autor: Trebor Oscorima

1. 🚀 Visión General

StockFlow es una solución tecnológica integral de gestión empresarial (ERP) y Punto de Venta (POS) diseñada para comercios y centros deportivos.

Esta versión v2.0 marca un hito en la arquitectura del sistema al implementar una capa de persistencia robusta con MySQL, eliminando la volatilidad de los datos en memoria. El sistema garantiza la integridad transaccional de ventas, inventarios, cajas y reservas, permitiendo un despliegue seguro en entornos de producción local.

Capacidades Principales

Persistencia Total: Almacenamiento seguro en base de datos relacional para todos los módulos.

Punto de Venta (POS): Procesamiento de ventas con múltiples métodos de pago, control de stock en tiempo real y emisión de comprobantes.

Gestión Financiera: Control estricto de sesiones de caja (Apertura/Cierre) y auditoría de movimientos.

Gestión de Servicios: Módulo especializado para alquiler de canchas deportivas con agenda visual y control de estados (Reserva -> Adelanto -> Pago).

Configuración Dinámica: Gestión de monedas, unidades de medida y métodos de pago directamente desde la interfaz, sin tocar código.

Seguridad RBAC: Control de acceso basado en roles y privilegios granulares.

2. 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura Full-Stack en Python utilizando el framework Reflex, que compila el frontend a React y gestiona el backend en Python puro.

Stack Tecnológico

Frontend/Backend: Reflex

Base de Datos: MySQL 8.0

ORM: SQLModel (SQLAlchemy)

Migraciones: Alembic

Estilos: Tailwind CSS

Modelo de Datos (E-R)

La estructura de datos se define en app/models.py y se gestiona mediante migraciones automáticas:

Módulo

Entidades Principales

Descripción

Auth

User

Usuarios, contraseñas (hash bcrypt) y privilegios (JSON).

Inventario

Product, Category

Catálogo de productos y categorización dinámica.

Ventas

Sale, SaleItem

Cabecera y detalle de transacciones, vinculadas a la sesión de caja.

Caja

CashboxSession, CashboxLog

Registro de turnos y auditoría de flujo de efectivo.

Servicios

FieldReservation, FieldPrice

Reservas de canchas y configuración de tarifas.

Config

Currency, Unit, PaymentMethod

Tablas maestras para personalización del sistema.

3. 📦 Estructura del Proyecto

Sistema-de-Ventas/
├── alembic/             # Historial de migraciones de base de datos
├── app/
│   ├── components/      # Componentes UI reutilizables (Botones, Modales, Tablas)
│   ├── models.py        # Definición de tablas y modelos SQLModel
│   ├── pages/           # Vistas de la aplicación (Frontend)
│   ├── states/          # Lógica de negocio y gestión de estado (Backend)
│   │   ├── auth_state.py      # Autenticación y Usuarios
│   │   ├── cash_state.py      # Gestión de Caja y Reportes
│   │   ├── config_state.py    # Configuración Global
│   │   ├── inventory_state.py # CRUD de Productos
│   │   ├── services_state.py  # Reservas y Servicios
│   │   └── venta_state.py     # Lógica del POS
│   ├── utils/           # Utilidades (Formatos, Fechas, Exports)
│   └── app.py           # Punto de entrada
├── assets/              # Recursos estáticos
├── rxconfig.py          # Configuración del entorno y conexión BD
└── requirements.txt     # Dependencias


4. ⚙️ Guía de Instalación y Despliegue

Prerrequisitos

Python 3.10 o superior.

Servidor MySQL 8.0 instalado y en ejecución.

Git.

Pasos de Instalación

Clonar el repositorio:

git clone [https://github.com/TreborOscorima/Sistema-de-Ventas.git](https://github.com/TreborOscorima/Sistema-de-Ventas.git)
cd Sistema-de-Ventas


Configurar Entorno Virtual:

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate


Instalar Dependencias:

pip install -r requirements.txt


Configurar Base de Datos:

Crea una base de datos vacía en MySQL llamada sistema_ventas.

Edita rxconfig.py con tus credenciales:

db_url="mysql+pymysql://USUARIO:PASSWORD@localhost:3306/sistema_ventas"


Ejecutar Migraciones (Inicialización):
Construye las tablas en la base de datos:

reflex db init
reflex db makemigrations --message "deploy_inicial"
reflex db migrate


Iniciar el Sistema:

reflex run


Accede a: http://localhost:3000

Nota: Al primer inicio, el sistema poblará automáticamente las tablas de configuración (monedas, unidades, métodos de pago) gracias al método ensure_default_data.

5. 📖 Manual de Módulos

🛒 Punto de Venta (Ventas)

Interfaz Ágil: Diseñada para registro rápido mediante códigos de barras.

Validación de Caja: Impide realizar ventas si no existe una sesión de caja abierta.

Pagos Flexibles: Soporta pagos mixtos (ej: parte efectivo, parte tarjeta) y registra el detalle exacto.

📦 Inventario

Gestión Persistente: CRUD completo de productos conectado directamente a MySQL.

Categorización: Creación dinámica de categorías que persisten entre sesiones.

Reportes: Exportación de inventario valorizado a Excel.

💵 Gestión de Caja

Sesiones: Control estricto de turnos por usuario.

Arqueo: Cierre de caja con cálculo automático de totales esperados vs. registrados.

Historial: Consulta de movimientos históricos y reimpresión de tickets.

⚽ Servicios (Reservas)

Agenda Visual: Planificador interactivo para canchas deportivas.

Ciclo de Vida: Controla el flujo completo: Reserva -> Adelanto -> Pago Final.

Integración Contable: Los pagos de reservas se inyectan automáticamente en la caja activa como ítems de servicio.

🔧 Configuración

Panel Administrativo: Permite gestionar usuarios, roles, monedas, unidades y métodos de pago sin intervención técnica.

6. Mantenimiento

Actualizaciones de Base de Datos

Si se realizan cambios en app/models.py, se debe actualizar el esquema:

reflex db makemigrations --message "descripcion_cambio"
reflex db migrate


© 2025 StockFlow. Desarrollado con ❤️ usando Reflex.