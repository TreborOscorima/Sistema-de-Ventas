# Plan: Sistema Completo de Gestión de Ventas e Inventario

## Qué es este archivo

Este archivo es el **roadmap histórico/evolutivo** del proyecto (fases, objetivos y tareas).

No es un runbook operativo de producción ni un manual técnico integral.  
Para documentación operativa y técnica actualizada, consultar:

- `docs/SYSTEM_FULL_DOCUMENTATION.md`
- `docs/DEPLOYMENT_SECURITY.md`
- `docs/CANARY_ROLLOUT_RUNBOOK.md`

## Estado general de este plan

- Fases 1 a 9: completadas.
- Fase 10: hardening/refactorización continua.

Se recomienda mantener este archivo como visión de producto y deuda técnica, no como única fuente para deploy/operación.

## Objetivo

Desarrollar un sistema completo de gestión de ventas e inventario con interfaz moderna, sidebar navegable, formularios interactivos, base de datos integrada, y sistema de autenticación con control de privilegios.

---

## Phase 1: Estructura Base y Módulo de Ingreso de Productos ✅

**Objetivo:** Crear la estructura principal con sidebar navegable y el módulo completo de ingreso de productos

### Tareas:

- [x] Diseñar layout principal con sidebar responsivo (colapsable en móvil/tablet)
- [x] Implementar menú de navegación con secciones: Control de Movimiento (Ingreso, Venta), Inventario Actual, Historial de Movimientos
- [x] Crear estado global para gestión de productos, ventas e inventario
- [x] Implementar módulo INGRESO con formulario dinámico para agregar múltiples productos
- [x] Formulario debe incluir: descripción, cantidad, unidad de medida (dropdown), precio de compra, cálculo automático de subtotal
- [x] Agregar funcionalidad para añadir múltiples productos en una sola transacción
- [x] Implementar cálculo automático del Total general de la transacción
- [x] Añadir validación de formularios y manejo de errores
- [x] Crear tabla/lista editable de productos agregados antes de confirmar ingreso
- [x] Implementar botón de confirmación que guarda todos los productos en el inventario

---

## Phase 2: Módulo de Ventas e Inventario Actual ✅

**Objetivo:** Desarrollar el sistema de ventas con autocompletado y visualización de inventario actual

### Tareas:

- [x] Implementar módulo VENTA con formulario inteligente
- [x] Agregar autocompletado de productos basado en inventario existente
- [x] Al seleccionar producto, auto-rellenar: unidad de medida y precio sugerido
- [x] Permitir edición de cantidad y precio de venta
- [x] Calcular automáticamente subtotal por producto y total de venta
- [x] Validar stock disponible antes de permitir venta
- [x] Crear interfaz para agregar múltiples productos en una venta
- [x] Implementar confirmación de venta que actualiza inventario (reduce stock)
- [x] Desarrollar módulo INVENTARIO ACTUAL con tabla responsiva
- [x] Mostrar todos los productos: Descripción, Stock actual, Unidad de medida, Precio unitario, Valor total del stock
- [x] Agregar filtros de búsqueda y ordenamiento en inventario
- [x] Implementar indicadores visuales para stock bajo (rojo < 5, naranja 6-10)
- [x] Formatear correctamente valores monetarios con 2 decimales

---

## Phase 3: Historial de Movimientos y Reportes ✅

**Objetivo:** Completar el sistema con historial completo, análisis y optimizaciones finales

### Tareas:

- [x] Implementar módulo HISTORIAL DE MOVIMIENTOS con tabla completa
- [x] Mostrar todos los movimientos: Fecha/Hora, Tipo (Ingreso/Salida), Descripción, Cantidad, Unidad, Total
- [x] Agregar filtros por: fecha (inicio y fin), tipo de movimiento (ingreso/venta), producto
- [x] Implementar paginación para grandes volúmenes de datos
- [x] Crear visualización de estadísticas: total ingresos, total ventas, ganancia bruta, total movimientos
- [x] Agregar gráficos con recharts para visualizar tendencias de Ingresos vs Ventas por día
- [x] Implementar sección de Productos Más Vendidos (Top 5)
- [x] Agregar alertas de Productos con Stock Bajo (≤10 unidades)
- [x] Implementar exportación de datos a Excel
- [x] Optimizar diseño responsivo en todos los módulos
- [x] Implementar notificaciones/toasts para confirmaciones de acciones
- [x] Añadir botón para resetear todos los filtros
- [x] Pulir estilos y asegurar consistencia visual en todo el sistema

---

## Phase 4: Sistema de Autenticación y Login ✅

**Objetivo:** Implementar sistema de login seguro y gestión de sesiones.

### Tareas:

- [x] Crear modelo de datos para usuarios (username, password hash, role, privileges)
- [x] Implementar página de login con formulario de autenticación
- [x] Crear usuario superadmin predefinido con credenciales por defecto (admin/admin)
- [x] Agregar sistema de hash de contraseñas con bcrypt
- [x] Implementar lógica de autenticación (validar credenciales)
- [x] Crear estado de sesión para usuario autenticado con JWT y rx.LocalStorage
- [x] Proteger todas las rutas principales (requieren autenticación)
- [x] Agregar botón de logout en el sidebar
- [x] Implementar redirección automática a login si no está autenticado
- [x] Mostrar nombre de usuario y rol en el sidebar/header con avatar

---

## Phase 5: Módulo de Configuración - Gestión de Usuarios ✅

**Objetivo:** Crear módulo de configuración para crear y administrar usuarios del sistema.

### Tareas:

- [x] Agregar opción "Configuracion" al menú del sidebar
- [x] Crear página de Configuración con sección de Gestión de Usuarios
- [x] Implementar formulario para crear nuevos usuarios (username, password, confirmar password, rol)
- [x] Agregar tabla para listar todos los usuarios existentes con acciones
- [x] Implementar funcionalidad de edición de usuarios (cambiar password, rol, privilegios)
- [x] Agregar botón para eliminar usuarios (protegido: no se puede eliminar admin ni a sí mismo)
- [x] Validar que solo usuarios con privilegio manage_users puedan acceder al módulo
- [x] Implementar validaciones: username único, passwords coinciden, campos requeridos

---

## Phase 6: Sistema de Privilegios y Roles ✅

**Objetivo:** Implementar sistema de permisos granulares (RBAC).

### Tareas:

- [x] Definir privilegios del sistema (view_ingresos, create_ventas, manage_cashbox, etc.)
- [x] Crear interfaz con switches activables/desactivables para cada privilegio en formulario de usuario
- [x] Implementar lógica para guardar privilegios por usuario en la BD
- [x] Proteger cada módulo según privilegios del usuario autenticado (validación en event handlers y UI guards)
- [x] Ocultar/mostrar secciones del UI según privilegios del usuario (MixinState computed vars)
- [x] Implementar superadmin con todos los privilegios habilitados por defecto
- [x] Agregar indicadores visuales de privilegios activos (badges)

---

## Phase 7: Gestión de Caja y Flujo de Dinero ✅

**Objetivo:** Controlar apertura, cierre y movimientos de efectivo (Caja Chica).

### Tareas:

- [x] Implementar modelo de datos para Sesiones de Caja y Movimientos
- [x] Crear UI para Apertura de Caja (monto inicial)
- [x] Bloquear operaciones de venta si la caja no está abierta
- [x] Implementar Cierre de Caja con resumen de ventas, ingresos y egresos
- [x] Crear módulo de "Caja Chica" para registrar gastos/salidas de dinero
- [x] Generar reportes de cierre de caja (PDF/Vista) con arqueo de efectivo
- [x] Historial de aperturas y cierres por usuario

---

## Phase 8: Gestión de Clientes y Créditos ✅

**Objetivo:** Administrar base de datos de clientes y cuentas corrientes (fiado).

### Tareas:

- [x] Crear módulo de Clientes (CRUD: nombre, documento, teléfono)
- [x] Implementar opción de venta a crédito ("Fiado") en el módulo de Venta
- [x] Desarrollar servicio de deuda/crédito (`credit_service.py`)
- [x] Crear vista de Cuentas por Cobrar (Saldos pendientes)
- [x] Permitir amortizaciones o pagos de deuda desde el módulo de Clientes
- [x] Historial de pagos y estado de cuenta por cliente

---

## Phase 9: Módulo de Reservas y Servicios ✅

**Objetivo:** Gestión de alquiler de campos deportivos y servicios por horario.

### Tareas:

- [x] Crear interfaz de Calendario/Agenda
- [x] Implementar lógica de slots de tiempo (horarios disponibles/ocupados)
- [x] Soporte para múltiples tipos de servicio (Fútbol, Vóley)
- [x] Formulario de Reserva con datos de cliente y adelanto de pago
- [x] Integración con caja (adelantos suman al flujo de dinero)
- [x] Visualización gráfica de ocupación de campos

---

## Phase 10: Refactorización y Hardening (Actual) 🚧

**Objetivo:** Pagar deuda técnica, mejorar seguridad y optimizar rendimiento.

### Tareas:

- [ ] **Refactorización de Venta:** Migrar `venta_state.py` para usar IDs de producto en lugar de descripciones (evita errores con nombres duplicados).
- [ ] **Seguridad:** Implementar sanitización estricta de inputs para prevenir XSS en todos los formularios.
- [ ] **Optimización:** Auditar y corregir consultas N+1 en reportes y listados (usar `selectinload` consistentemente).
- [ ] **DevOps:** Configurar CI/CD con GitHub Actions para tests y deployment automatizado.
- [ ] **Testing:** Aumentar cobertura de pruebas unitarias para servicios críticos (Caja, Stock).
