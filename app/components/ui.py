"""
Componentes de UI reutilizables para la aplicacion Sistema de Ventas.

Este modulo brinda componentes comunes que siguen el principio DRY
para reducir duplicacion de codigo entre paginas.

Design System v2.0 - Estandarización UI/UX:
- Border radius: sm (inputs/botones), md (cards), lg (modales)
- Espaciado: Escala de 4px (p-1, p-2, p-3, p-4, p-6, p-8)
- Colores: indigo-600 (primario), green-600 (éxito), red-600 (peligro)
- Tipografía: tabular-nums para valores monetarios
"""
import reflex as rx
from typing import Callable


# =============================================================================
# DESIGN TOKENS - Valores centralizados para consistencia global
# =============================================================================

# Border radius estandarizados
RADIUS = {
    "sm": "rounded",           # 4px - Botones pequeños, badges
    "md": "rounded-md",        # 6px - Inputs, botones normales  
    "lg": "rounded-lg",        # 8px - Cards, dropdowns
    "xl": "rounded-xl",        # 12px - Modales, cards destacadas
    "full": "rounded-full",    # Círculos, avatares
}

# Sombras estandarizadas
SHADOWS = {
    "none": "",
    "sm": "shadow-sm",
    "md": "shadow-md",
    "lg": "shadow-lg",
    "xl": "shadow-xl",
}

# Transiciones suaves
TRANSITIONS = {
    "fast": "transition-all duration-150 ease-out",
    "normal": "transition-all duration-200 ease-out", 
    "slow": "transition-all duration-300 ease-out",
}

# Focus states para accesibilidad
FOCUS_RING = "focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
FOCUS_WITHIN = "focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-indigo-500"


# =============================================================================
# BUTTON STYLES - Con focus states y transiciones mejoradas
# =============================================================================

_BTN_BASE = f"flex items-center justify-center gap-2 {RADIUS['md']} {TRANSITIONS['fast']} {FOCUS_RING} font-medium"

BUTTON_STYLES = {
    "primary": f"{_BTN_BASE} px-4 py-2.5 bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 min-h-[44px]",
    "primary_sm": f"{_BTN_BASE} px-3 py-2 bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 min-h-[40px] text-sm",
    "secondary": f"{_BTN_BASE} px-4 py-2.5 border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 active:bg-gray-100 min-h-[44px]",
    "secondary_sm": f"{_BTN_BASE} px-3 py-2 border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 active:bg-gray-100 min-h-[40px] text-sm",
    "success": f"{_BTN_BASE} px-4 py-2.5 bg-emerald-600 text-white hover:bg-emerald-700 active:bg-emerald-800 min-h-[44px]",
    "success_sm": f"{_BTN_BASE} px-3 py-2 bg-emerald-600 text-white hover:bg-emerald-700 active:bg-emerald-800 min-h-[40px] text-sm",
    "danger": f"{_BTN_BASE} px-4 py-2.5 bg-red-600 text-white hover:bg-red-700 active:bg-red-800 min-h-[44px]",
    "danger_sm": f"{_BTN_BASE} px-3 py-2 bg-red-600 text-white hover:bg-red-700 active:bg-red-800 min-h-[40px] text-sm",
    "warning": f"{_BTN_BASE} px-4 py-2.5 bg-amber-500 text-white hover:bg-amber-600 active:bg-amber-700 min-h-[44px]",
    "ghost": f"{_BTN_BASE} px-4 py-2.5 text-gray-600 hover:bg-gray-100 active:bg-gray-200 min-h-[44px]",
    "ghost_sm": f"{_BTN_BASE} px-3 py-2 text-gray-600 hover:bg-gray-100 active:bg-gray-200 min-h-[40px] text-sm",
    "link_primary": f"{_BTN_BASE} px-3 py-2 border border-gray-200 text-indigo-600 hover:bg-indigo-50 active:bg-indigo-100 min-h-[40px]",
    "link_danger": f"{_BTN_BASE} px-3 py-2 border border-gray-200 text-red-600 hover:bg-red-50 active:bg-red-100 min-h-[40px]",
    "disabled": f"flex items-center justify-center gap-2 px-4 py-2.5 {RADIUS['md']} bg-gray-100 text-gray-400 cursor-not-allowed min-h-[44px] opacity-60",
    "disabled_sm": f"flex items-center justify-center gap-2 px-3 py-2 {RADIUS['md']} bg-gray-100 text-gray-400 cursor-not-allowed min-h-[40px] text-sm opacity-60",
    "icon_danger": f"p-2 text-red-500 hover:bg-red-100 active:bg-red-200 {RADIUS['full']} {TRANSITIONS['fast']}",
    "icon_primary": f"p-2 text-indigo-500 hover:bg-indigo-100 active:bg-indigo-200 {RADIUS['full']} {TRANSITIONS['fast']}",
    "icon_indigo": f"p-2 text-indigo-500 hover:bg-indigo-100 active:bg-indigo-200 {RADIUS['full']} {TRANSITIONS['fast']}",
    "icon_ghost": f"p-2 text-gray-500 hover:bg-gray-100 active:bg-gray-200 {RADIUS['full']} {TRANSITIONS['fast']}",
}


# =============================================================================
# INPUT STYLES - Con focus states mejorados
# =============================================================================

_INPUT_BASE = f"w-full px-3 py-2.5 border border-gray-300 {RADIUS['md']} {TRANSITIONS['fast']} placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"

INPUT_STYLES = {
    "default": _INPUT_BASE,
    "disabled": f"w-full px-3 py-2.5 border border-gray-200 {RADIUS['md']} bg-gray-50 text-gray-500 cursor-not-allowed",
    "search": f"{_INPUT_BASE} pl-10",  # Espacio para icono de búsqueda
    "error": f"w-full px-3 py-2.5 border-2 border-red-300 {RADIUS['md']} {TRANSITIONS['fast']} focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-red-50",
}


# =============================================================================
# CARD STYLES - Estandarizados
# =============================================================================

CARD_STYLES = {
    "default": f"bg-white p-5 sm:p-6 {RADIUS['lg']} {SHADOWS['md']}",
    "bordered": f"bg-white border border-gray-200 {RADIUS['lg']} p-5 sm:p-6 {SHADOWS['sm']}",
    "compact": f"bg-white border border-gray-200 {RADIUS['lg']} p-4 {SHADOWS['sm']}",
    "flat": f"bg-white border border-gray-200 {RADIUS['lg']} p-5 sm:p-6",
    "highlight": f"bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 {RADIUS['lg']} p-5 sm:p-6 {SHADOWS['sm']}",
}


# =============================================================================
# TABLE STYLES - Con más espaciado y hover mejorado
# =============================================================================

TABLE_STYLES = {
    "wrapper": f"overflow-hidden {RADIUS['lg']} border border-gray-200",
    "header": "bg-gray-50 border-b border-gray-200",
    "header_cell": "py-3.5 px-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider",
    "row": f"border-b border-gray-100 {TRANSITIONS['fast']} hover:bg-gray-50",
    "cell": "py-4 px-4 text-sm text-gray-700",
    "cell_mono": "py-4 px-4 text-sm text-gray-500 font-mono",
    "cell_currency": "py-4 px-4 text-sm font-semibold text-gray-900 tabular-nums text-right",
}

# Alias para compatibilidad
TABLE_HEADER_STYLE = TABLE_STYLES["header"]
TABLE_ROW_STYLE = TABLE_STYLES["row"]

# Alto de fila de textarea (en pixeles) para calcular min-height
TEXTAREA_ROW_HEIGHT = 24


# =============================================================================
# REUSABLE COMPONENTS - Componentes con estilos consistentes
# =============================================================================

# Tamaños para currency_display
_CURRENCY_SIZES = {
    "sm": "text-sm font-medium",
    "md": "text-base font-semibold", 
    "lg": "text-lg font-bold",
    "xl": "text-2xl font-bold",
    "2xl": "text-3xl font-extrabold",
}


def currency_display(
    value: rx.Var | str,
    symbol: rx.Var | str = "S/",
    size: str = "lg",
    color: str = "text-gray-900",
    show_symbol: bool = True,
) -> rx.Component:
    """
    Muestra valores monetarios con formato consistente.
    
    Usa tabular-nums para alineación perfecta en columnas.
    
    Args:
        value: Valor numérico formateado (ej: "1,234.56")
        symbol: Símbolo de moneda (ej: "S/", "$", "€")
        size: sm | md | lg | xl | 2xl
        color: Clase de color Tailwind
        show_symbol: Si mostrar el símbolo de moneda
    
    Returns:
        Componente con valor monetario estilizado
    """
    size_class = _CURRENCY_SIZES.get(size, _CURRENCY_SIZES["lg"])
    
    return rx.el.span(
        rx.cond(
            show_symbol,
            rx.el.span(symbol, class_name="text-gray-500 mr-0.5"),
            rx.fragment(),
        ),
        rx.el.span(value),
        class_name=f"{size_class} {color} tabular-nums tracking-tight",
    )


# Tamaños para loading_spinner
_SPINNER_SIZES = {
    "sm": "h-4 w-4",
    "md": "h-6 w-6",
    "lg": "h-8 w-8",
    "xl": "h-12 w-12",
}


def loading_spinner(
    size: str = "md",
    color: str = "text-indigo-600",
    label: str | None = None,
) -> rx.Component:
    """
    Spinner de carga con animación suave.
    
    Args:
        size: sm | md | lg | xl
        color: Clase de color Tailwind
        label: Texto opcional debajo del spinner
    
    Returns:
        Componente de spinner animado
    """
    size_class = _SPINNER_SIZES.get(size, _SPINNER_SIZES["md"])
    
    spinner = rx.el.div(
        rx.el.div(
            class_name=f"{size_class} {color} animate-spin rounded-full border-2 border-current border-t-transparent",
        ),
        class_name="flex justify-center",
    )
    
    if label:
        return rx.el.div(
            spinner,
            rx.el.p(label, class_name="mt-2 text-sm text-gray-500 text-center"),
            class_name="flex flex-col items-center",
        )
    
    return spinner


def permission_guard(
    has_permission: rx.Var[bool],
    content: rx.Component,
    redirect_message: str = "Acceso denegado",
) -> rx.Component:
    """
    Componente guard que muestra contenido solo si el usuario tiene permisos.
    
    Si no tiene permisos, muestra un mensaje de acceso denegado con animación
    de fade mientras la redirección ocurre.
    
    Args:
        has_permission: Variable reactiva booleana de permiso
        content: Componente a mostrar si tiene permiso
        redirect_message: Mensaje a mostrar si no tiene permiso
    
    Returns:
        Componente condicional basado en permisos
    """
    access_denied = rx.el.div(
        rx.el.div(
            rx.icon("shield-x", class_name="h-16 w-16 text-red-400 mb-4"),
            rx.el.h2(
                redirect_message,
                class_name="text-xl font-semibold text-gray-800 mb-2",
            ),
            rx.el.p(
                "No tienes permisos para acceder a este módulo.",
                class_name="text-gray-500 mb-4",
            ),
            rx.el.p(
                "Redirigiendo al Dashboard...",
                class_name="text-sm text-gray-400 animate-pulse",
            ),
            class_name="flex flex-col items-center text-center",
        ),
        class_name="flex items-center justify-center min-h-[60vh] animate-in fade-in duration-300",
    )
    
    return rx.cond(
        has_permission,
        content,
        access_denied,
    )


def page_header(
    title: str | rx.Var,
    subtitle: str | rx.Var | None = None,
    actions: list[rx.Component] | None = None,
    breadcrumb: str | None = None,
) -> rx.Component:
    """
    Encabezado de página estandarizado con soporte para acciones y breadcrumbs.
    
    Args:
        title: Título principal de la página
        subtitle: Descripción opcional
        actions: Lista de componentes de acción (botones)
        breadcrumb: Texto de breadcrumb opcional
    
    Returns:
        Componente de encabezado de página
    """
    # Seccion de titulo y subtitulo (consistente con page_title)
    title_section = rx.el.div(
        rx.el.h1(title, class_name="text-2xl font-bold text-gray-900 tracking-tight"),
        rx.el.p(subtitle, class_name="text-sm text-gray-500") if subtitle else rx.fragment(),
        class_name="flex flex-col gap-1",
    )
    
    content = []
    
    # Breadcrumb
    if breadcrumb:
        content.append(
            rx.el.nav(
                rx.el.span(breadcrumb, class_name="text-sm text-gray-500"),
                class_name="mb-2",
            )
        )
    
    # Layout principal
    if actions:
        content.append(
            rx.el.div(
                title_section,
                rx.el.div(
                    *actions,
                    class_name="flex items-center gap-3",
                ),
                class_name="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4",
            )
        )
    else:
        content.append(title_section)
    
    return rx.el.header(
        *content,
        class_name="mb-6",
    )


def empty_state(
    icon: str = "inbox",
    title: str = "Sin datos",
    description: str | None = None,
    action: rx.Component | None = None,
) -> rx.Component:
    """
    Estado vacío para listas y tablas sin datos.
    
    Args:
        icon: Nombre del icono Lucide
        title: Título del estado vacío
        description: Descripción opcional
        action: Botón de acción opcional
    
    Returns:
        Componente de estado vacío centrado
    """
    content = [
        rx.el.div(
            rx.icon(icon, class_name="h-12 w-12 text-gray-300"),
            class_name="mb-4",
        ),
        rx.el.h3(title, class_name="text-sm font-medium text-gray-900"),
    ]
    
    if description:
        content.append(
            rx.el.p(description, class_name="mt-1 text-sm text-gray-500")
        )
    
    if action:
        content.append(
            rx.el.div(action, class_name="mt-4")
        )
    
    return rx.el.div(
        *content,
        class_name="flex flex-col items-center justify-center py-12 text-center",
    )


def stat_card(
    label: str,
    value: rx.Var | str,
    icon: str | None = None,
    trend: rx.Var | str | None = None,
    trend_up: rx.Var | bool | None = None,
    variant: str = "default",
) -> rx.Component:
    """
    Tarjeta de estadística para dashboards.
    
    Args:
        label: Etiqueta de la métrica
        value: Valor principal
        icon: Icono Lucide opcional
        trend: Texto de tendencia (ej: "+12%")
        trend_up: Si la tendencia es positiva
        variant: default | highlight
    
    Returns:
        Componente de tarjeta de estadística
    """
    card_class = CARD_STYLES.get(variant, CARD_STYLES["default"])
    
    header = []
    if icon:
        header.append(
            rx.el.div(
                rx.icon(icon, class_name="h-5 w-5 text-gray-400"),
                class_name=f"p-2 bg-gray-100 {RADIUS['lg']}",
            )
        )
    
    header.append(
        rx.el.span(label, class_name="text-sm font-medium text-gray-500")
    )
    
    value_section = [
        rx.el.span(value, class_name="text-2xl font-bold text-gray-900 tabular-nums")
    ]
    
    if trend is not None and trend_up is not None:
        trend_color = rx.cond(
            trend_up,
            "text-emerald-600 bg-emerald-50",
            "text-red-600 bg-red-50",
        ) if isinstance(trend_up, rx.Var) else (
            "text-emerald-600 bg-emerald-50" if trend_up else "text-red-600 bg-red-50"
        )
        trend_icon = rx.cond(
            trend_up,
            rx.icon("trending-up", class_name="h-3 w-3"),
            rx.icon("trending-down", class_name="h-3 w-3"),
        ) if isinstance(trend_up, rx.Var) else (
            rx.icon("trending-up", class_name="h-3 w-3") if trend_up 
            else rx.icon("trending-down", class_name="h-3 w-3")
        )
        
        value_section.append(
            rx.el.span(
                trend_icon,
                rx.el.span(trend, class_name="ml-1"),
                class_name=f"ml-2 inline-flex items-center px-2 py-0.5 text-xs font-medium {RADIUS['full']} {trend_color}",
            )
        )
    
    return rx.el.div(
        rx.el.div(
            *header,
            class_name="flex items-center gap-3 mb-3",
        ),
        rx.el.div(
            *value_section,
            class_name="flex items-baseline",
        ),
        class_name=card_class,
    )


def action_button(
    text: str | rx.Component,
    on_click: Callable,
    variant: str = "primary",
    icon: str | None = None,
    disabled: rx.Var | bool = False,
    disabled_variant: str = "disabled",
    class_name: str = "",
    **kwargs,
) -> rx.Component:
    """
    Crea un boton de accion con estilo consistente.

    Parametros:
        text: Texto del boton o componente
        on_click: Manejador de click
        variant: Clave de estilo en BUTTON_STYLES
        icon: Nombre de icono (lucide) opcional
        disabled: Si el boton esta deshabilitado (puede ser var reactiva)
        disabled_variant: Estilo cuando esta deshabilitado
        class_name: Clases CSS adicionales
        **kwargs: Argumentos adicionales para el boton

    Retorna:
        Componente de boton con estilo
    """
    content = []
    if icon:
        content.append(rx.icon(icon, class_name="h-4 w-4"))
    if isinstance(text, str):
        content.append(rx.el.span(text))
    else:
        content.append(text)
    
    if isinstance(variant, rx.Var):
        base_style = variant
    else:
        base_style = BUTTON_STYLES.get(variant, BUTTON_STYLES["primary"])

    style_classes = rx.cond(
        disabled,
        BUTTON_STYLES.get(disabled_variant, BUTTON_STYLES["disabled"]),
        base_style,
    ) if isinstance(disabled, rx.Var) else (
        BUTTON_STYLES.get(disabled_variant, BUTTON_STYLES["disabled"]) if disabled 
        else base_style
    )

    if class_name:
        if isinstance(style_classes, str):
            style_classes = f"{style_classes} {class_name}"
        else:
            style_classes = style_classes + f" {class_name}"

    return rx.el.button(
        *content,
        on_click=on_click,
        disabled=disabled,
        class_name=style_classes,
        **kwargs,
    )


def icon_button(
    icon: str,
    on_click: Callable,
    variant: str = "icon_primary",
    disabled: rx.Var | bool = False,
    aria_label: str = "",
) -> rx.Component:
    """
    Crea un boton circular solo con icono.

    Parametros:
        icon: Nombre del icono (lucide)
        on_click: Manejador de click
        variant: Variante de estilo en BUTTON_STYLES
        disabled: Si el boton esta deshabilitado
        aria_label: Etiqueta de accesibilidad
    """
    return rx.el.button(
        rx.icon(icon, class_name="h-4 w-4"),
        on_click=on_click,
        disabled=disabled,
        aria_label=aria_label,
        class_name=BUTTON_STYLES.get(variant, BUTTON_STYLES["icon_primary"]),
    )


def form_field(
    label: str,
    input_component: rx.Component,
    label_style: str = "text-sm font-medium text-gray-700",
) -> rx.Component:
    """
    Crea un wrapper de campo con etiqueta.

    Parametros:
        label: Texto de la etiqueta
        input_component: Componente input/select/textarea
        label_style: Clase CSS para la etiqueta

    Retorna:
        Div con la etiqueta y el input
    """
    return rx.el.div(
        rx.el.label(label, class_name=label_style),
        input_component,
        class_name="flex flex-col gap-1",
    )


def toggle_switch(
    checked: rx.Var | bool,
    on_change: Callable,
    class_name: str = "",
) -> rx.Component:
    track_base = (
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors "
        "duration-200 ease-in-out"
    )
    thumb_base = (
        "inline-block h-5 w-5 transform rounded-full bg-white shadow transition "
        "duration-200 ease-in-out"
    )
    track_class = rx.cond(
        checked,
        f"{track_base} bg-indigo-600",
        f"{track_base} bg-gray-200",
    )
    thumb_class = rx.cond(
        checked,
        f"{thumb_base} translate-x-5",
        f"{thumb_base} translate-x-0",
    )

    return rx.el.label(
        rx.el.input(
            type="checkbox",
            checked=checked,
            on_change=on_change,
            class_name="sr-only",
        ),
        rx.el.span(rx.el.span(class_name=thumb_class), class_name=track_class),
        class_name=f"inline-flex items-center cursor-pointer {class_name}".strip(),
    )


def text_input(
    placeholder: str = "",
    value: rx.Var | str = "",
    on_change: Callable | None = None,
    input_type: str = "text",
    disabled: bool = False,
    style: str = "default",
    debounce_timeout: int = 300,
) -> rx.Component:
    """
    Crea un input de texto con estilo.

    Parametros:
        placeholder: Texto placeholder
        value: Valor del input (puede ser reactivo)
        on_change: Manejador de cambio
        input_type: Tipo de input HTML
        disabled: Si el input esta deshabilitado
        style: Clave de estilo en INPUT_STYLES
        debounce_timeout: Tiempo de debounce en ms
    """
    return rx.el.input(
        type=input_type,
        placeholder=placeholder,
        value=value,
        on_change=on_change,
        disabled=disabled,
        class_name=INPUT_STYLES.get(
            "disabled" if disabled else style, 
            INPUT_STYLES["default"]
        ),
        debounce_timeout=debounce_timeout,
    )


def section_card(
    title: str,
    description: str = "",
    children: list[rx.Component] | None = None,
    style: str = "bordered",
) -> rx.Component:
    """
    Crea una seccion en formato card con titulo y descripcion opcional.

    Parametros:
        title: Titulo de la seccion
        description: Texto de descripcion opcional
        children: Componentes hijos
        style: Clave de estilo en CARD_STYLES
    """
    header_parts = [
        rx.el.h3(title, class_name="text-lg font-semibold text-gray-800"),
    ]
    if description:
        header_parts.append(
            rx.el.p(description, class_name="text-sm text-gray-600")
        )
    
    content_parts = [
        rx.el.div(*header_parts, class_name="flex flex-col gap-1"),
    ]
    if children:
        content_parts.extend(children)
    
    return rx.el.div(
        *content_parts,
        class_name=f"{CARD_STYLES.get(style, CARD_STYLES['default'])} flex flex-col gap-4",
    )


def status_badge(
    status: rx.Var | str,
    status_colors: dict[str, tuple[str, str]] | None = None,
) -> rx.Component:
    """
    Crea un badge de estado con el color correspondiente.

    Parametros:
        status: Valor del estado
        status_colors: Dict que mapea estado a (bg_color, text_color).
                      Por defecto usa colores comunes.
    """
    if status_colors is None:
        status_colors = {
            "pagado": ("bg-emerald-100", "text-emerald-700"),
            "pendiente": ("bg-amber-100", "text-amber-700"),
            "cancelado": ("bg-red-100", "text-red-700"),
            "eliminado": ("bg-gray-200", "text-gray-700"),
        }
    
    # Para estado reactivo se usan cadenas de rx.cond
    if isinstance(status, rx.Var):
        return rx.cond(
            status == "pagado",
            rx.el.span(
                "Pagado",
                class_name="px-2 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-700",
            ),
            rx.cond(
                status == "cancelado",
                rx.el.span(
                    "Cancelado",
                    class_name="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-700",
                ),
                rx.cond(
                    status == "eliminado",
                    rx.el.span(
                        "Eliminado",
                        class_name="px-2 py-1 text-xs font-semibold rounded-full bg-gray-200 text-gray-700",
                    ),
                    rx.el.span(
                        "Pendiente",
                        class_name="px-2 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700",
                    ),
                ),
            ),
        )
    
    # Para estado estatico
    colors = status_colors.get(status.lower(), ("bg-gray-100", "text-gray-700"))
    return rx.el.span(
        status.capitalize(),
        class_name=f"px-2 py-1 text-xs font-semibold rounded-full {colors[0]} {colors[1]}",
    )


def empty_state(message: str) -> rx.Component:
    """
    Crea un mensaje de estado vacio centrado.

    Parametros:
        message: Mensaje a mostrar
    """
    return rx.el.p(
        message,
        class_name="text-gray-500 text-center py-8",
    )


def page_title(title: str, subtitle: str = "") -> rx.Component:
    """
    Crea un titulo de pagina con subtitulo opcional.

    Parametros:
        title: Titulo principal
        subtitle: Subtitulo o descripcion opcional
    """
    return rx.el.div(
        rx.el.h1(title, class_name="text-2xl font-bold text-gray-900 tracking-tight"),
        rx.el.p(subtitle, class_name="text-sm text-gray-500") if subtitle else rx.fragment(),
        class_name="flex flex-col gap-1 mb-6",
    )


def modal_container(
    is_open: rx.Var,
    on_close: Callable,
    title: str,
    description: str = "",
    children: list[rx.Component] | None = None,
    footer: rx.Component | None = None,
    max_width: str = "max-w-lg",
) -> rx.Component:
    """
    Crea un contenedor de modal.

    Parametros:
        is_open: Var reactiva que controla la visibilidad
        on_close: Manejador para cerrar el modal
        title: Titulo del modal
        description: Descripcion opcional
        children: Contenido del cuerpo del modal
        footer: Contenido del footer (normalmente botones)
        max_width: Clase Tailwind de max-width
    """
    header = rx.el.div(
        rx.el.h3(title, class_name="text-lg font-semibold text-gray-800"),
        rx.el.p(description, class_name="text-sm text-gray-600") if description else rx.fragment(),
        class_name="space-y-1",
    )
    body = (
        rx.el.div(
            *children,
            class_name="flex-1 overflow-y-auto min-h-0 space-y-4",
        )
        if children
        else rx.fragment()
    )
    footer_component = footer if footer else rx.fragment()
    
    return rx.cond(
        is_open,
        rx.el.div(
            rx.el.div(
                on_click=on_close,
                class_name="fixed inset-0 bg-black/40 modal-overlay",
            ),
            rx.el.div(
                header,
                body,
                footer_component,
                class_name=(
                    f"relative z-10 w-full {max_width} rounded-xl bg-white p-6 shadow-xl "
                    "max-h-[90vh] overflow-hidden flex flex-col gap-4"
                ),
            ),
            class_name="fixed inset-0 z-50 flex items-start sm:items-center justify-center px-4 py-6 overflow-hidden",
        ),
        rx.fragment(),
    )


def filter_section(
    filters: list[rx.Component],
    on_search: Callable,
    on_reset: Callable,
    extra_buttons: list[rx.Component] | None = None,
    grid_cols: str = "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
) -> rx.Component:
    """
    Crea una seccion de filtros estandarizada.

    Parametros:
        filters: Lista de componentes de filtro
        on_search: Manejador del boton buscar
        on_reset: Manejador del boton limpiar
        extra_buttons: Botones de accion adicionales
        grid_cols: Clases Tailwind para columnas del grid
    """
    buttons = [
        action_button("Buscar", on_search, variant="primary", icon="search"),
        action_button("Limpiar", on_reset, variant="secondary"),
    ]
    if extra_buttons:
        buttons.extend(extra_buttons)
    
    return rx.el.div(
        *filters,
        rx.el.div(
            *buttons,
            class_name="flex flex-col gap-2 sm:flex-row sm:flex-wrap",
        ),
        class_name=f"grid {grid_cols} gap-3 sm:gap-4 items-end",
    )


def date_range_filter(
    start_value: rx.Var | str,
    end_value: rx.Var | str,
    on_start_change: Callable,
    on_end_change: Callable,
    start_label: str = "Fecha Inicio",
    end_label: str = "Fecha Fin",
) -> tuple[rx.Component, rx.Component]:
    """
    Crea un par de inputs de fecha para filtros.

    Parametros:
        start_value: Valor de fecha inicio
        end_value: Valor de fecha fin
        on_start_change: Manejador para cambio de fecha inicio
        on_end_change: Manejador para cambio de fecha fin
        start_label: Etiqueta para fecha inicio
        end_label: Etiqueta para fecha fin

    Retorna:
        Tupla (start_input, end_input)
    """
    return (
        form_field(
            start_label,
            rx.el.input(
                type="date",
                value=start_value,
                on_change=on_start_change,
                class_name=INPUT_STYLES["default"],
            ),
        ),
        form_field(
            end_label,
            rx.el.input(
                type="date",
                value=end_value,
                on_change=on_end_change,
                class_name=INPUT_STYLES["default"],
            ),
        ),
    )


def stat_card(
    icon: str,
    title: str,
    value: rx.Var | rx.Component,
    icon_color: str = "text-gray-600",
) -> rx.Component:
    """
    Crea una card de estadistica con icono, titulo y valor.

    Parametros:
        icon: Nombre del icono (lucide)
        title: Titulo o etiqueta de la card
        value: Valor a mostrar (puede ser var reactiva o componente)
        icon_color: Clase Tailwind de color para el icono

    Retorna:
        Componente de card con estilo
    """
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name=f"h-6 w-6 {icon_color}"),
            class_name="p-3 bg-gray-100 rounded-lg",
        ),
        rx.el.div(
            rx.el.p(title, class_name="text-sm font-medium text-gray-500"),
            rx.el.p(value, class_name="text-2xl font-bold text-gray-800"),
            class_name="flex-grow",
        ),
        class_name="flex items-center gap-4 bg-white p-4 rounded-xl shadow-sm border",
    )


def pagination_controls(
    current_page: rx.Var,
    total_pages: rx.Var,
    on_prev: Callable,
    on_next: Callable,
) -> rx.Component:
    """
    Crea controles de paginacion con botones anterior/siguiente e info.

    Parametros:
        current_page: Numero de pagina actual (var reactiva)
        total_pages: Total de paginas (var reactiva)
        on_prev: Manejador para pagina anterior
        on_next: Manejador para pagina siguiente

    Retorna:
        Componente de controles de paginacion
    """
    return rx.el.div(
        rx.el.button(
            "Anterior",
            on_click=on_prev,
            disabled=current_page <= 1,
            class_name=rx.cond(
                current_page <= 1,
                "px-4 py-2 bg-gray-200 text-gray-500 rounded-md cursor-not-allowed min-h-[40px]",
                "px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 min-h-[40px]",
            ),
        ),
        rx.el.span(
            "Página ",
            current_page.to_string(),
            " de ",
            total_pages.to_string(),
            class_name="text-sm text-gray-600",
        ),
        rx.el.button(
            "Siguiente",
            on_click=on_next,
            disabled=current_page >= total_pages,
            class_name=rx.cond(
                current_page >= total_pages,
                "px-4 py-2 bg-gray-200 text-gray-500 rounded-md cursor-not-allowed min-h-[40px]",
                "px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 min-h-[40px]",
            ),
        ),
        class_name="flex flex-col sm:flex-row justify-center items-center gap-3 sm:gap-4 mt-6",
    )


def data_table(
    headers: list[tuple[str, str]],
    rows: rx.Component,
    empty_message: str = "No hay datos disponibles.",
    has_data: rx.Var | bool = True,
) -> rx.Component:
    """
    Crea una tabla de datos con estilo.

    Parametros:
        headers: Lista de tuplas (texto, clase de alineacion)
        rows: Contenido de tbody (usualmente rx.foreach)
        empty_message: Mensaje cuando la tabla esta vacia
        has_data: Si hay datos para mostrar (puede ser var reactiva)

    Retorna:
        Componente de tabla con estilo
    """
    header_cells = [
        rx.el.th(text, class_name=f"py-3 px-4 {align}")
        for text, align in headers
    ]
    
    # Construir el componente de estado vacio
    empty_component = rx.el.p(empty_message, class_name="text-gray-500 text-center py-8")
    
    # Manejar has_data reactivo o estatico
    if isinstance(has_data, rx.Var):
        # Para vars reactivas, usar rx.cond
        empty_state_section = rx.cond(
            has_data,
            rx.fragment(),
            empty_component,
        )
    else:
        # Para booleanos estaticos, incluir condicionalmente el componente
        empty_state_section = rx.fragment() if has_data else empty_component
    
    return rx.el.div(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(*header_cells, class_name=TABLE_HEADER_STYLE)
            ),
            rx.el.tbody(rows),
        ),
        empty_state_section,
        class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto flex flex-col gap-4",
    )


def card_container(
    *children: rx.Component,
    title: str | None = None,
    description: str | None = None,
    style: str = "bordered",
    gap: str = "gap-4",
) -> rx.Component:
    """
    Crea un contenedor de card con header opcional.

    Parametros:
        *children: Componentes hijos a renderizar dentro de la card
        title: Titulo opcional de la card
        description: Descripcion opcional de la card
        style: Clave de estilo en CARD_STYLES
        gap: Clases Tailwind para espaciado vertical

    Retorna:
        Componente de card con estilo
    """
    content_parts = []
    
    if title or description:
        header_parts = []
        if title:
            header_parts.append(
                rx.el.h3(title, class_name="text-lg font-semibold text-gray-800")
            )
        if description:
            header_parts.append(
                rx.el.p(description, class_name="text-sm text-gray-600")
            )
        content_parts.append(
            rx.el.div(*header_parts, class_name="flex flex-col gap-1")
        )
    
    content_parts.extend(children)
    
    return rx.el.div(
        *content_parts,
        class_name=f"{CARD_STYLES.get(style, CARD_STYLES['bordered'])} flex flex-col {gap}",
    )


def section_header(title: str, description: str = "") -> rx.Component:
    """
    Crea un encabezado de seccion con titulo y descripcion opcional.

    Parametros:
        title: Titulo de la seccion
        description: Texto de descripcion opcional

    Retorna:
        Componente de encabezado
    """
    parts = [rx.el.h2(title, class_name="text-lg font-semibold text-gray-800")]
    if description:
        parts.append(rx.el.p(description, class_name="text-sm text-gray-600"))
    
    return rx.el.div(*parts, class_name="flex flex-col gap-1")


def info_badge(
    text: str | rx.Var,
    variant: str = "default",
) -> rx.Component:
    """
    Crea un badge informativo.

    Parametros:
        text: Texto del badge
        variant: Variante de color (default, success, warning, danger, info)

    Retorna:
        Componente de badge con estilo
    """
    variant_styles = {
        "default": "bg-gray-100 text-gray-700",
        "success": "bg-emerald-100 text-emerald-700",
        "warning": "bg-amber-100 text-amber-700",
        "danger": "bg-red-100 text-red-700",
        "info": "bg-blue-100 text-blue-700",
    }
    style_class = variant_styles.get(variant, variant_styles["default"])
    
    return rx.el.span(
        text,
        class_name=f"px-2 py-1 text-xs font-semibold rounded-full {style_class}",
    )


def form_input(
    label: str,
    value: rx.Var | str,
    on_change: Callable,
    input_type: str = "text",
    placeholder: str = "",
    disabled: bool = False,
    step: str | None = None,
) -> rx.Component:
    """
    Crea un input con etiqueta.

    Parametros:
        label: Texto de la etiqueta
        value: Valor del input (puede ser reactivo)
        on_change: Manejador de cambio
        input_type: Tipo de input HTML (text, number, date, etc.)
        placeholder: Texto placeholder
        disabled: Si el input esta deshabilitado
        step: Step para inputs numericos

    Retorna:
        Componente de input con etiqueta
    """
    input_props = {
        "type": input_type,
        "placeholder": placeholder,
        "value": value,
        "on_change": on_change,
        "disabled": disabled,
        "class_name": INPUT_STYLES["disabled"] if disabled else INPUT_STYLES["default"],
    }
    if step:
        input_props["step"] = step
    
    return rx.el.div(
        rx.el.label(label, class_name="text-sm font-medium text-gray-700"),
        rx.el.input(**input_props),
        class_name="flex flex-col gap-1",
    )


def form_select(
    label: str,
    options: list[tuple[str, str]] | rx.Var,
    value: rx.Var | str,
    on_change: Callable,
    placeholder: str | None = None,
) -> rx.Component:
    """
    Crea un select con etiqueta.

    Parametros:
        label: Texto de la etiqueta del select
        options: Lista de tuplas (texto, valor) o var reactiva
        value: Valor seleccionado
        on_change: Manejador de cambio
        placeholder: Opcion placeholder opcional

    Retorna:
        Componente de select con etiqueta
    """
    option_elements = []
    if placeholder:
        option_elements.append(rx.el.option(placeholder, value=""))
    
    # Manejar lista estatica o var reactiva de opciones
    if isinstance(options, rx.Var):
        return rx.el.div(
            rx.el.label(label, class_name="text-sm font-medium text-gray-700"),
            rx.el.select(
                rx.el.option(placeholder, value="") if placeholder else rx.fragment(),
                rx.foreach(
                    options,
                    lambda opt: rx.el.option(opt[0], value=opt[1]),
                ),
                value=value,
                on_change=on_change,
                class_name="w-full p-2 border rounded-md bg-white",
            ),
            class_name="flex flex-col gap-1",
        )
    
    for display_text, opt_value in options:
        option_elements.append(rx.el.option(display_text, value=opt_value))
    
    return rx.el.div(
        rx.el.label(label, class_name="text-sm font-medium text-gray-700"),
        rx.el.select(
            *option_elements,
            value=value,
            on_change=on_change,
            class_name="w-full p-2 border rounded-md bg-white",
        ),
        class_name="flex flex-col gap-1",
    )


def form_textarea(
    label: str,
    value: rx.Var | str,
    on_change: Callable,
    placeholder: str = "",
    rows: int = 4,
) -> rx.Component:
    """
    Crea un textarea con etiqueta.

    Parametros:
        label: Texto de la etiqueta
        value: Valor del textarea
        on_change: Manejador de cambio
        placeholder: Texto placeholder
        rows: Numero de filas visibles

    Retorna:
        Componente de textarea con etiqueta
    """
    min_height = rows * TEXTAREA_ROW_HEIGHT
    return rx.el.div(
        rx.el.label(label, class_name="text-sm font-medium text-gray-700"),
        rx.el.textarea(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            class_name=f"w-full p-2 border rounded-md min-h-[{min_height}px]",
        ),
        class_name="flex flex-col gap-1",
    )


def filter_action_buttons(
    on_search: Callable,
    on_clear: Callable,
    on_export: Callable | None = None,
    search_text: str = "Buscar",
    clear_text: str = "Limpiar",
    export_text: str = "Exportar",
) -> rx.Component:
    """
    Crea un grupo de botones de accion para filtros.

    Parametros:
        on_search: Manejador del boton buscar
        on_clear: Manejador del boton limpiar
        on_export: Manejador opcional del boton exportar
        search_text: Texto del boton buscar
        clear_text: Texto del boton limpiar
        export_text: Texto del boton exportar

    Retorna:
        Componente de grupo de botones
    """
    buttons = [
        rx.el.button(
            rx.icon("search", class_name="h-4 w-4"),
            search_text,
            on_click=on_search,
            class_name=BUTTON_STYLES["primary"],
        ),
        rx.el.button(
            clear_text,
            on_click=on_clear,
            class_name=BUTTON_STYLES["secondary"],
        ),
    ]
    
    if on_export:
        buttons.append(
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                export_text,
                on_click=on_export,
                class_name=BUTTON_STYLES["success"],
            )
        )
    
    return rx.el.div(
        *buttons,
        class_name="flex flex-col gap-2 sm:flex-row sm:flex-wrap",
    )


def select_filter(
    label: str,
    options: list[tuple[str, str]],
    value: rx.Var | str,
    on_change: Callable,
) -> rx.Component:
    """
    Crea un select de filtro con etiqueta.

    Parametros:
        label: Etiqueta del filtro
        options: Lista de tuplas (texto, valor)
        value: Valor seleccionado
        on_change: Manejador de cambio

    Retorna:
        Componente de select de filtro con etiqueta
    """
    option_elements = [
        rx.el.option(display_text, value=opt_value)
        for display_text, opt_value in options
    ]
    
    return rx.el.div(
        rx.el.label(label, class_name="text-sm font-medium text-gray-600"),
        rx.el.select(
            *option_elements,
            value=value,
            on_change=on_change,
            class_name="w-full p-2 border rounded-md",
        ),
        class_name="flex flex-col gap-1",
    )
