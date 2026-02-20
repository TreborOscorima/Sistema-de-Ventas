# Auditoría de Responsividad — Sistema de Ventas

> **Tipo:** Solo lectura (sin correcciones aplicadas)  
> **Framework:** Reflex (Python) + Tailwind CSS  
> **Breakpoints usados:** `sm:640px` · `md:768px` · `lg:1024px` · `xl:1280px`  
> **Fecha de auditoría:** 2025-06-13

---

## Resumen Ejecutivo

| Severidad | Hallazgos |
|-----------|-----------|
| 🔴 **Crítico** | 2 |
| 🟡 **Medio** | 8 |
| 🟢 **Bajo** | 5 |
| **Total** | **15** |

El proyecto muestra un **buen nivel de responsividad general**. El sistema de diseño centralizado en `ui.py` (tokens `CARD_STYLES`, `BUTTON_STYLES`, `INPUT_STYLES`, `TABLE_STYLES`) y los componentes reutilizables (`modal_container`, `page_title`, `pagination_controls`, `filter_section`) aplican patrones mobile-first consistentes. El sidebar (`sidebar.py`) tiene excelente implementación con overlay móvil y ancho adaptable (`w-[88vw] max-w-[320px] md:w-64 xl:w-72`).

Los problemas se concentran en **tablas anchas sin alternativa móvil** y en **algunos modales que no aplican el patrón bottom-sheet**.

---

## Hallazgos por Archivo

---

### 🔴 `app/pages/inventario.py`

#### 1. Tabla principal de inventario — sin alternativa móvil (CRÍTICO)

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~963–1058 |
| **class_name actual** | `min-w-[980px]` en la `<table>`, contenedor con `overflow-x-auto` |
| **Problema** | La tabla muestra 9 columnas (Código Barra, Descripción, Categoría, Stock, Unidad, Precio Compra, Precio Venta, Valor Total, Acciones). Con `min-w-[980px]`, en pantallas <1024px el usuario necesita hacer scroll horizontal extenso. No hay vista de tarjetas móvil ni columnas ocultas con `hidden md:table-cell`. |
| **Comparación** | `venta.py` resuelve el mismo problema con `mobile_sale_item_card()` + `hidden sm:table` / `sm:hidden` |
| **Sugerencia** | Ocultar columnas menos críticas (`hidden md:table-cell` para Código Barra, Precio Compra, Valor Total) o crear vista de tarjetas para móvil similar a `venta.py` |
| **Severidad** | 🔴 Crítico |

#### 2. Modal de ajuste de inventario — posicionamiento sin transición sm:

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~759 |
| **class_name actual** | `fixed inset-0 z-50 flex items-start md:items-center justify-center px-4 py-6` |
| **Problema** | Salta de `items-start` (base) a `md:items-center` sin pasar por `sm:`. El `modal_container` estándar usa `items-end sm:items-center` (bottom-sheet → centrado). Este modal usa renderizado manual en vez del componente reutilizable. |
| **Sugerencia** | Usar `items-end sm:items-center` o migrar a `modal_container()` |
| **Severidad** | 🟡 Medio |

---

### 🔴 `app/pages/servicios.py`

#### 3. Tabla de reservas — sin alternativa móvil (CRÍTICO)

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~1152–1195 |
| **class_name actual** | `min-w-[980px]` en la `<table>`, contenedor con `overflow-x-auto` |
| **Problema** | 7 columnas (Cliente, Campo, Horario, Monto, Estado, Acciones, Saldo). Columna "Acciones" tiene hasta 4 botones apilados. En móvil, fuerza scroll horizontal masivo. No hay columnas ocultas ni vista alternativa. |
| **Sugerencia** | Aplicar `hidden md:table-cell` a columnas como "Campo" y "Saldo", o crear vista de tarjetas para pantallas < md |
| **Severidad** | 🔴 Crítico |

#### 4. Modal de reserva — sin patrón bottom-sheet

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~688 |
| **class_name actual** | `fixed inset-0 z-50 flex items-center justify-center px-4` |
| **Problema** | En móvil usa `items-center` que puede cortar contenido en pantallas pequeñas. El `modal_container()` usa `items-end sm:items-center` (bottom-sheet en móvil). Este modal renderiza manualmente. |
| **Sugerencia** | Cambiar a `items-end sm:items-center` o migrar a `modal_container()` |
| **Severidad** | 🟡 Medio |

---

### 🟡 `app/pages/dashboard.py`

#### 5. Padding principal sin responsividad

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~623 |
| **class_name actual** | `p-6 ` (espacio extra al final) |
| **Problema** | Todas las demás páginas (`caja.py`, `compras.py`, `configuracion.py`, etc.) usan `p-4 sm:p-6`. Dashboard usa `p-6` fijo, resultando en padding excesivo en pantallas pequeñas donde cada píxel cuenta. |
| **Sugerencia** | Cambiar a `p-4 sm:p-6` |
| **Severidad** | 🟡 Medio |

---

### 🟡 `app/pages/ingreso.py`

#### 6. Tabla de items sin columnas ocultas

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~430–480 (tabla de items del ingreso) |
| **class_name actual** | 9+ columnas en tabla con `overflow-x-auto` |
| **Problema** | Columnas: Tipo, Serie, N°, Proveedor, RUC, Productos, Precio Total, Fecha y Usuario — todas visibles en todas las pantallas. Depende enteramente de scroll horizontal. |
| **Sugerencia** | Aplicar `hidden md:table-cell` o `hidden lg:table-cell` a columnas como "Serie", "RUC" y "Usuario" |
| **Severidad** | 🟡 Medio |

---

### 🟡 `app/pages/caja.py`

#### 7. Tabla de aperturas/cierres — todas las columnas visibles

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~562–580 |
| **class_name actual** | 6 columnas: Fecha/Hora, Evento, Usuario, Monto Apertura, Monto Cierre, Acciones. `min-w-full` con `overflow-x-auto`. |
| **Problema** | En pantallas < 768px, 6 columnas causan scroll horizontal. "Monto Apertura" podría ocultarse en móvil. |
| **Sugerencia** | Añadir `hidden md:table-cell` a "Monto Apertura" o "Usuario" |
| **Severidad** | 🟡 Medio |

#### 8. Tabla de caja chica — 7 columnas sin ocultar

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~1044–1095 |
| **class_name actual** | 7 columnas (Fecha/Hora, Usuario, Motivo, Cant., Unidad, Costo, Total). `min-w-full` + `overflow-x-auto`. |
| **Problema** | Similar al punto anterior. "Unidad" y "Costo" podrían ocultarse en móvil. |
| **Sugerencia** | `hidden md:table-cell` en "Cant.", "Unidad" y "Costo" |
| **Severidad** | 🟡 Medio |

---

### 🟡 `app/pages/cuentas.py`

#### 9. Tabla de cuotas — 8 columnas sin ocultar

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~636–690 |
| **class_name actual** | 8 columnas (Cliente, DNI, Vencimiento, Monto, Pagado, Pendiente, Estado, Acciones). `min-w-full` con `overflow-x-auto`. |
| **Problema** | Tabla muy ancha en móvil. "DNI", "Pagado" y "Pendiente" podrían ocultarse. |
| **Sugerencia** | Aplicar `hidden md:table-cell` a "DNI" y "Pagado" |
| **Severidad** | 🟡 Medio |

---

### 🟡 `app/pages/compras.py`

#### 10. Tabla de proveedores — 6 columnas sin ocultar

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~778–800 |
| **class_name actual** | 6 columnas (Proveedor, N° Registro, Teléfono, Email, Dirección, Acción). `overflow-x-auto` presente. |
| **Problema** | "Email" y "Dirección" podrían ocultarse en pantallas < md para reducir scroll. La tabla de compras sí usa `hidden md:table-cell` para columnas secundarias pero la tabla de proveedores no. |
| **Sugerencia** | Aplicar `hidden md:table-cell` a "Email" y "Dirección" |
| **Severidad** | 🟡 Medio |

---

### 🟢 `app/pages/configuracion.py`

#### 11. Formularios de monedas/pagos saltan de 1 a 4 columnas

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~1072 (monedas), ~1259 (pagos) |
| **class_name actual** | `grid grid-cols-1 md:grid-cols-4` |
| **Problema** | Salta de 1 columna a 4 columnas sin paso intermedio en `sm:`. Entre 640px y 768px los campos son single-column (y podría usarse `sm:grid-cols-2` para aprovechar mejor el espacio). |
| **Sugerencia** | Cambiar a `grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4` |
| **Severidad** | 🟢 Bajo |

#### 12. Formulario de unidades — salto de 1 a 3 columnas

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~1193 |
| **class_name actual** | `grid grid-cols-1 md:grid-cols-3` |
| **Problema** | Mismo patrón: salta de 1 a 3 sin paso por `sm:grid-cols-2`. |
| **Sugerencia** | `grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3` |
| **Severidad** | 🟢 Bajo |

---

### 🟢 `app/pages/historial.py`

#### 13. Grid de tarjetas salta de 1 a 2 columnas

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~270 (tarjetas de ventas recientes) |
| **class_name actual** | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` |
| **Problema** | No aprovecha `sm:` para un layout de 2 columnas más temprano. En un rango 640px–768px, las tarjetas se muestran en 1 sola columna cuando podrían ser 2. |
| **Sugerencia** | Cambiar a `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` |
| **Severidad** | 🟢 Bajo |

---

### 🟢 `app/pages/servicios.py`

#### 14. Tabla de log administrativo — 7 columnas sin ocultar

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~1400–1430 |
| **class_name actual** | 7 columnas (Fecha/Hora, Movimiento, Cliente, Campo, Monto, Estado, Notas). `min-w-full` + `overflow-x-auto`. |
| **Problema** | Tabla ancha pero menos frecuentemente accedida. Tiene `overflow-x-auto` como mitigación. |
| **Sugerencia** | Añadir `hidden md:table-cell` a "Campo" y "Notas" |
| **Severidad** | 🟢 Bajo |

---

### 🟢 `app/pages/marketing.py`

#### 15. Hero section — badges flotantes sin responsive vertical

| Campo | Detalle |
|-------|---------|
| **Líneas** | ~315 |
| **class_name actual** | `absolute -bottom-3 left-4 right-4 grid gap-2 sm:grid-cols-2` |
| **Problema** | En pantallas muy pequeñas (<375px) los badges flotantes podrían solaparse con contenido inferior. El `pb-8` del padre mitiga esto pero al borde. |
| **Sugerencia** | Minor — considerar aumentar `pb-8` a `pb-10` en el contenedor padre |
| **Severidad** | 🟢 Bajo |

---

## Archivos Bien Implementados ✅

Los siguientes archivos muestran patrones responsivos ejemplares:

| Archivo | Patrones destacados |
|---------|-------------------|
| **`app/components/sidebar.py`** | Overlay móvil con `md:hidden`, sidebar fijo con `w-[88vw] max-w-[320px] md:w-64 xl:w-72`, botón hamburguesa, cierre por overlay |
| **`app/components/ui.py`** | `modal_container()` con bottom-sheet móvil (`items-end sm:items-center`), `pagination_controls()` con `flex-col sm:flex-row`, todas las CARD/BUTTON/INPUT_STYLES con tokens responsivos |
| **`app/components/notification.py`** | `w-[90vw] max-w-sm` — proporción perfecta para notificaciones móvil/desktop |
| **`app/app.py`** | `authenticated_layout()` con `p-4 sm:p-6`, `cashbox_banner()` con `flex-col md:flex-row`, márgenes de sidebar condicionales |
| **`app/pages/venta.py`** | Doble vista: tarjetas móvil + tabla desktop (`sm:hidden` / `hidden sm:table`), sidebar de pago `hidden lg:block` + `payment_mobile_section()` `lg:hidden` |
| **`app/pages/login.py`** | Layout centrado con `max-w-md`, `min-h-screen`, `px-4` |
| **`app/pages/registro.py`** | Grid de teléfono `grid-cols-[116px_1fr] sm:grid-cols-[130px_1fr]`, formulario centrado responsive |
| **`app/pages/reportes.py`** | Padding triple nivel `p-3 sm:p-4 lg:p-6`, layout `flex-col xl:flex-row` |
| **`app/pages/compras.py`** | Tabla de compras con `hidden md:table-cell` en columnas secundarias, filtros `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` |
| **`app/pages/marketing.py`** | Landing page con grids progresivos, menú móvil con `<details>`, CTAs `flex-col sm:flex-row`, WhatsApp flotante con texto `hidden sm:inline` |
| **`app/pages/cambiar_contrasena.py`** | Card centrada simple, bien responsive |
| **`app/pages/periodo_prueba_finalizado.py`** | Card centrada simple, bien responsive |
| **`app/pages/cuenta_suspendida.py`** | Card centrada simple, bien responsive |

---

## Patrón Más Común a Corregir

El **anti-patrón dominante** es la presencia de tablas con muchas columnas que dependen únicamente de `overflow-x-auto` sin:
- Columnas ocultas con `hidden md:table-cell`
- Vista alternativa de tarjetas para móvil

Esto afecta a: `inventario.py`, `servicios.py`, `ingreso.py`, `caja.py` (×2), `cuentas.py`, `compras.py` (proveedores).

**El mejor ejemplo de solución en el propio codebase** está en `venta.py`, que implementa:
```python
# Vista móvil: tarjeta compacta
rx.el.div(..., class_name="sm:hidden ...")

# Vista desktop: tabla completa
rx.el.div(..., class_name="hidden sm:block ...")
```

Y en `compras.py` / `historial.py` que usan `hidden md:table-cell` para ocultar columnas no esenciales.

---

## Recomendación de Priorización

1. **Inmediato** → Inventario y Reservas (tablas 🔴 críticas — son módulos de uso frecuente)
2. **Siguiente sprint** → Dashboard padding + modales sin bottom-sheet (🟡 medio)
3. **Mejora continua** → Tablas secundarias + breakpoints sm: faltantes (🟡/🟢)
