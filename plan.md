# Plan: Sistema Completo de Gestión de Ventas e Inventario

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

## Phase 4: Sistema de Autenticación y Login
**Objetivo:** Implementar sistema de login con usuario superadmin predefinido

### Tareas:
- [ ] Crear modelo de datos para usuarios (username, password hash, role, privileges)
- [ ] Implementar página de login con formulario de autenticación
- [ ] Crear usuario superadmin predefinido con credenciales por defecto (admin/admin)
- [ ] Agregar sistema de hash de contraseñas con bcrypt
- [ ] Implementar lógica de autenticación (validar credenciales)
- [ ] Crear estado de sesión para usuario autenticado con rx.LocalStorage
- [ ] Proteger todas las rutas principales (requieren autenticación)
- [ ] Agregar botón de logout en el sidebar
- [ ] Implementar redirección automática a login si no está autenticado
- [ ] Mostrar nombre de usuario y rol en el sidebar/header con avatar

---

## Phase 5: Módulo de Configuración - Gestión de Usuarios
**Objetivo:** Crear módulo de configuración para crear y administrar usuarios del sistema

### Tareas:
- [ ] Agregar opción "Configuracion" al menú del sidebar
- [ ] Crear página de Configuración con sección de Gestión de Usuarios
- [ ] Implementar formulario para crear nuevos usuarios (username, password, confirmar password, rol)
- [ ] Agregar tabla para listar todos los usuarios existentes con acciones
- [ ] Implementar funcionalidad de edición de usuarios (cambiar password, rol, privilegios)
- [ ] Agregar botón para eliminar usuarios (protegido: no se puede eliminar admin ni a sí mismo)
- [ ] Validar que solo usuarios con privilegio manage_users puedan acceder al módulo
- [ ] Implementar validaciones: username único, passwords coinciden, campos requeridos

---

## Phase 6: Sistema de Privilegios con Switches
**Objetivo:** Implementar sistema de permisos granulares para cada usuario

### Tareas:
- [ ] Definir privilegios del sistema: view_ingresos, create_ingresos, view_ventas, create_ventas, view_inventario, edit_inventario, view_historial, export_data, manage_users
- [ ] Crear interfaz con switches activables/desactivables para cada privilegio en formulario de usuario
- [ ] Implementar lógica para guardar privilegios por usuario en el estado
- [ ] Proteger cada módulo según privilegios del usuario autenticado (validación en event handlers)
- [ ] Ocultar/mostrar secciones del UI según privilegios del usuario
- [ ] Implementar superadmin con todos los privilegios habilitados por defecto
- [ ] Agregar indicadores visuales de privilegios activos
- [ ] Validar privilegios antes de ejecutar acciones críticas (crear ingreso, venta, exportar, etc.)

---

## Notas Técnicas
- **Autenticación:** Hash de passwords con bcrypt, sesión persistente con rx.LocalStorage
- **Roles:** Superadmin (todos los privilegios), Usuario Normal (privilegios personalizables)
- **Privilegios:** Sistema granular con switches para cada funcionalidad
- **Seguridad:** Validación en frontend y backend, protección de rutas
- **UX:** Login moderno, gestión intuitiva de usuarios, feedback visual claro
- **Superadmin por defecto:** Username: admin, Password: admin
