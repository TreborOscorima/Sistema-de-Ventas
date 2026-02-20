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

from app.constants import WHATSAPP_NUMBER


# =============================================================================
# DESIGN TOKENS - Valores centralizados para consistencia global
# =============================================================================

# Border radius estandarizados
RADIUS = {
    "sm": "rounded",           # 4px - Botones pequeños, badges
    "md": "rounded-md",        # 8px - Inputs, botones normales
    "lg": "rounded-xl",        # 12px - Cards, dropdowns
    "xl": "rounded-2xl",       # 16px - Modales destacados
    "full": "rounded-full",    # Círculos, avatares
}

# Sombras estandarizadas
SHADOWS = {
    "none": "",
    "sm": "shadow-sm",
    "md": "shadow-sm",
    "lg": "shadow-md",
    "xl": "shadow-lg",
}

# Transiciones suaves
TRANSITIONS = {
    "fast": "transition-all duration-150 ease-out",
    "normal": "transition-all duration-200 ease-out", 
    "slow": "transition-all duration-300 ease-out",
}

# Focus states para accesibilidad
FOCUS_RING = "focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"


# =============================================================================
# BUTTON STYLES - Con focus states y transiciones mejoradas
# =============================================================================

_BTN_BASE = f"flex items-center justify-center gap-2 {RADIUS['md']} {TRANSITIONS['fast']} {FOCUS_RING} text-sm font-medium"

BUTTON_STYLES = {
    "primary": f"{_BTN_BASE} h-10 px-4 bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800",
    "primary_sm": f"{_BTN_BASE} h-9 px-3 bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800 text-sm",
    "secondary": f"{_BTN_BASE} h-10 px-4 border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 active:bg-slate-100",
    "secondary_sm": f"{_BTN_BASE} h-9 px-3 border border-slate-200 text-slate-700 bg-white hover:bg-slate-50 active:bg-slate-100 text-sm",
    "success": f"{_BTN_BASE} h-10 px-4 bg-emerald-600 text-white hover:bg-emerald-700 active:bg-emerald-800",
    "success_sm": f"{_BTN_BASE} h-9 px-3 bg-emerald-600 text-white hover:bg-emerald-700 active:bg-emerald-800 text-sm",
    "danger": f"{_BTN_BASE} h-10 px-4 bg-red-600 text-white hover:bg-red-700 active:bg-red-800",
    "danger_sm": f"{_BTN_BASE} h-9 px-3 bg-red-600 text-white hover:bg-red-700 active:bg-red-800 text-sm",
    "warning": f"{_BTN_BASE} h-10 px-4 bg-amber-500 text-white hover:bg-amber-600 active:bg-amber-700",
    "ghost": f"{_BTN_BASE} h-10 px-4 text-slate-600 hover:bg-slate-100 active:bg-slate-200",
    "ghost_sm": f"{_BTN_BASE} h-9 px-3 text-slate-600 hover:bg-slate-100 active:bg-slate-200 text-sm",
    "link_primary": f"{_BTN_BASE} h-9 px-3 border border-slate-200 text-indigo-600 hover:bg-indigo-50 active:bg-indigo-100",
    "link_danger": f"{_BTN_BASE} h-9 px-3 border border-slate-200 text-red-600 hover:bg-red-50 active:bg-red-100",
    "disabled": f"flex items-center justify-center gap-2 h-10 px-4 {RADIUS['md']} bg-slate-100 text-slate-400 cursor-not-allowed opacity-60",
    "disabled_sm": f"flex items-center justify-center gap-2 h-9 px-3 {RADIUS['md']} bg-slate-100 text-slate-400 cursor-not-allowed text-sm opacity-60",
    "icon_danger": f"p-2 text-red-500 hover:bg-red-100 active:bg-red-200 {RADIUS['full']} {TRANSITIONS['fast']}",
    "icon_primary": f"p-2 text-indigo-500 hover:bg-indigo-100 active:bg-indigo-200 {RADIUS['full']} {TRANSITIONS['fast']}",
    "icon_indigo": f"p-2 text-indigo-500 hover:bg-indigo-100 active:bg-indigo-200 {RADIUS['full']} {TRANSITIONS['fast']}",
    "icon_ghost": f"p-2 text-slate-500 hover:bg-slate-100 active:bg-slate-200 {RADIUS['full']} {TRANSITIONS['fast']}",
}

# =============================================================================
# INPUT STYLES - Con focus states mejorados
# =============================================================================

_INPUT_BASE = f"w-full h-10 px-3 text-sm bg-white border border-slate-200 {RADIUS['md']} {TRANSITIONS['fast']} placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"

INPUT_STYLES = {
    "default": _INPUT_BASE,
    "disabled": f"w-full h-10 px-3 text-sm border border-slate-200 {RADIUS['md']} bg-slate-50 text-slate-500 cursor-not-allowed",
    "search": f"{_INPUT_BASE} pl-10",  # Espacio para icono de búsqueda
    "error": f"w-full h-10 px-3 text-sm border-2 border-red-300 {RADIUS['md']} {TRANSITIONS['fast']} focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 bg-red-50",
}


# =============================================================================
# CARD STYLES - Estandarizados
# =============================================================================

CARD_STYLES = {
    "default": f"bg-white border border-slate-200 {RADIUS['lg']} p-5 sm:p-6 {SHADOWS['sm']}",
    "bordered": f"bg-white border border-slate-200 {RADIUS['lg']} p-5 sm:p-6 {SHADOWS['sm']}",
    "compact": f"bg-white border border-slate-200 {RADIUS['lg']} p-4 {SHADOWS['sm']}",
    "flat": f"bg-white border border-slate-200 {RADIUS['lg']} p-5 sm:p-6",
    "highlight": f"bg-gradient-to-br from-indigo-50 to-white border border-indigo-100 {RADIUS['lg']} p-5 sm:p-6 {SHADOWS['sm']}",
}


# =============================================================================
# TABLE STYLES - Con más espaciado y hover mejorado
# =============================================================================

TABLE_STYLES = {
    "wrapper": f"overflow-hidden {RADIUS['lg']} border border-slate-200",
    "header": "bg-slate-50/50 border-b border-slate-200",
    "header_cell": "py-3.5 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider",
    "row": f"border-b border-slate-100 {TRANSITIONS['fast']} hover:bg-slate-50/80",
    "cell": "py-4 px-4 text-sm text-slate-700",
    "cell_mono": "py-4 px-4 text-sm text-slate-500 font-mono",
    "cell_currency": "py-4 px-4 text-sm font-semibold text-slate-900 tabular-nums text-right",
}

# Alto de fila de textarea (en pixeles) para calcular min-height
TEXTAREA_ROW_HEIGHT = 24


# =============================================================================
# REUSABLE COMPONENTS - Componentes con estilos consistentes
# =============================================================================


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
                class_name="text-xl font-semibold text-slate-800 mb-2",
            ),
            rx.el.p(
                "No tienes permisos para acceder a este módulo.",
                class_name="text-slate-500 mb-4",
            ),
            rx.el.p(
                "Redirigiendo al Dashboard...",
                class_name="text-sm text-slate-400 animate-pulse",
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
        rx.el.h1(title, class_name="text-2xl font-bold text-slate-900 tracking-tight"),
        rx.el.p(subtitle, class_name="text-sm text-slate-500") if subtitle else rx.fragment(),
        class_name="flex flex-col gap-1",
    )
    
    content = []
    
    # Breadcrumb
    if breadcrumb:
        content.append(
            rx.el.nav(
                rx.el.span(breadcrumb, class_name="text-sm text-slate-500"),
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


def form_field(
    label: str,
    input_component: rx.Component,
    label_style: str = "text-sm font-medium text-slate-700",
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
        f"{track_base} bg-slate-200",
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
            "eliminado": ("bg-slate-200", "text-slate-700"),
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
                        class_name="px-2 py-1 text-xs font-semibold rounded-full bg-slate-200 text-slate-700",
                    ),
                    rx.el.span(
                        "Pendiente",
                        class_name="px-2 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700",
                    ),
                ),
            ),
        )
    
    # Para estado estatico
    colors = status_colors.get(status.lower(), ("bg-slate-100", "text-slate-700"))
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
        class_name="text-slate-500 text-center py-8",
    )


def page_title(title: str, subtitle: str = "") -> rx.Component:
    """
    Crea un titulo de pagina con subtitulo opcional.

    Parametros:
        title: Titulo principal
        subtitle: Subtitulo o descripcion opcional
    """
    return rx.el.div(
        rx.el.h1(
            title,
            class_name="text-xl sm:text-2xl lg:text-[1.65rem] font-bold text-slate-900 tracking-tight leading-tight",
        ),
        rx.el.p(subtitle, class_name="text-sm sm:text-[15px] text-slate-500")
        if subtitle
        else rx.fragment(),
        class_name="flex flex-col gap-1 mb-4 sm:mb-6",
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
        rx.el.h3(title, class_name="text-base sm:text-lg font-semibold text-slate-800"),
        rx.el.p(description, class_name="text-sm text-slate-600") if description else rx.fragment(),
        class_name="space-y-1",
    )
    body = (
        rx.el.div(
            *children,
            class_name="flex-1 overflow-y-auto min-h-0 space-y-3 sm:space-y-4",
        )
        if children
        else rx.fragment()
    )
    footer_component = footer if footer else rx.fragment()
    modal_sections = [header]
    if children:
        modal_sections.extend([rx.divider(color="slate-100"), body])
    if footer:
        modal_sections.extend([rx.divider(color="slate-100"), footer_component])
    
    return rx.cond(
        is_open,
        rx.el.div(
            rx.el.div(
                on_click=on_close,
                class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay",
            ),
            rx.el.div(
                *modal_sections,
                class_name=(
                    f"relative z-10 w-full {max_width} rounded-xl sm:rounded-2xl bg-white p-4 sm:p-6 shadow-xl "
                    "max-h-[92vh] overflow-hidden flex flex-col gap-4"
                ),
            ),
            class_name="fixed inset-0 z-50 flex items-end sm:items-center justify-center px-3 sm:px-4 py-3 sm:py-6 overflow-hidden",
        ),
        rx.fragment(),
    )


def limit_reached_modal(
    is_open: rx.Var,
    on_close: Callable,
    message: rx.Var | str,
    on_primary: Callable | None = None,
    primary_label: str = "Ver Planes",
) -> rx.Component:
    """
    Modal para límites de plan alcanzados.

    Parametros:
        is_open: Var reactiva que controla visibilidad
        on_close: Manejador para cerrar el modal
        message: Mensaje principal del cuerpo
        on_primary: Accion del boton principal (opcional)
        primary_label: Texto del boton principal
    """
    footer = rx.el.div(
        action_button("Cerrar", on_close, variant="secondary"),
        action_button(
            primary_label,
            on_primary if on_primary else on_close,
            variant="primary",
        ),
        class_name="flex flex-col sm:flex-row justify-end gap-2",
    )

    body = rx.el.div(
        rx.el.div(
            rx.icon("rocket", class_name="h-6 w-6 text-indigo-600"),
            rx.el.div(
                rx.el.p(message, class_name="text-sm text-slate-700"),
                rx.el.p(
                    "Para seguir creciendo, actualiza tu suscripción.",
                    class_name="text-xs text-slate-500",
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="flex items-start gap-3",
        ),
    )

    return modal_container(
        is_open=is_open,
        on_close=on_close,
        title="🚀 Mejora tu Plan",
        description="",
        children=[body],
        footer=footer,
        max_width="max-w-md",
    )


def pricing_modal(
    is_open: rx.Var,
    on_close: Callable,
) -> rx.Component:
    def _plan_card(
        title: str,
        icon: str,
        limits: list[str],
        modules: list[str],
        action_label: str,
        action_href: str,
        highlight: bool = False,
        badge_text: str | None = None,
    ) -> rx.Component:
        show_badge = rx.Var.create(bool(badge_text))
        accent_ring = "ring-2 ring-amber-200/70" if highlight else "ring-1 ring-slate-200/80"
        header_bg = (
            "bg-gradient-to-r from-amber-50 via-amber-100/60 to-white"
            if highlight
            else "bg-gradient-to-r from-indigo-50 via-white to-white"
        )
        icon_wrap = "bg-amber-100 text-amber-700" if highlight else "bg-indigo-100 text-indigo-600"
        button_style = BUTTON_STYLES["primary"] if highlight else BUTTON_STYLES["secondary"]

        def _bullet(item: str) -> rx.Component:
            return rx.el.li(
                rx.icon(
                    "circle_check",
                    class_name="h-4 w-4 text-emerald-600 flex-shrink-0",
                ),
                rx.el.span(item, class_name="text-sm text-slate-700"),
                class_name="flex items-start gap-2",
            )

        plan_name = title.replace("PLAN ", "")
        return rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon(icon, class_name="h-5 w-5"),
                    class_name=f"p-2 rounded-lg {icon_wrap}",
                ),
                rx.el.div(
                    rx.el.p("PLAN", class_name="text-xs font-semibold uppercase text-slate-500"),
                    rx.el.h4(plan_name, class_name="text-lg font-semibold text-slate-900"),
                    class_name="flex flex-col leading-tight",
                ),
                rx.cond(
                    show_badge,
                    rx.badge(
                        badge_text or "",
                        color_scheme="amber" if highlight else "indigo",
                    ),
                    rx.fragment(),
                ),
                class_name="flex items-center justify-between",
            ),
            rx.el.div(
                rx.el.p("Límites", class_name="text-xs uppercase text-slate-400 tracking-wide"),
                rx.el.ul(
                    *[_bullet(item) for item in limits],
                    class_name="space-y-1.5",
                ),
                class_name="space-y-2",
            ),
            rx.el.div(
                rx.el.p("Módulos", class_name="text-xs uppercase text-slate-400 tracking-wide"),
                rx.el.ul(
                    *[_bullet(item) for item in modules],
                    class_name="space-y-1.5",
                ),
                class_name="space-y-2",
            ),
            rx.link(
                rx.el.button(
                    action_label,
                    class_name=button_style + " w-full justify-center",
                ),
                href=action_href,
                is_external=True,
                class_name="w-full",
            ),
            class_name=(
                f"{CARD_STYLES['bordered']} space-y-4 {accent_ring} "
                f"{header_bg} shadow-sm hover:shadow-md transition-all"
            ),
        )

    standard_link = (
        f"https://wa.me/{WHATSAPP_NUMBER}?text="
        "Hola,%20quiero%20el%20Plan%20Standard%20(USD%2045/mes)%20de%20TUWAYKIAPP."
    )
    professional_link = (
        f"https://wa.me/{WHATSAPP_NUMBER}?text="
        "Hola,%20quiero%20el%20Plan%20Professional%20(USD%2075/mes)%20de%20TUWAYKIAPP."
    )
    enterprise_link = (
        f"https://wa.me/{WHATSAPP_NUMBER}?text="
        "Hola,%20quiero%20el%20Plan%20Enterprise%20(USD%20175/mes)%20de%20TUWAYKIAPP."
    )

    content = rx.el.div(
        _plan_card(
            title="PLAN STANDARD",
            icon="sparkles",
            limits=["Hasta 5 sucursales", "10 usuarios"],
            modules=[
                "Múltiples usuarios y roles",
                "Ventas rápidas con lector de código o teclado",
                "Productos por unidad, peso y litros",
                "Gestión de stock y reposición",
                "Reportes diarios de ventas e ingresos",
                "Clientes y cuentas corrientes",
            ],
            action_label="Elegir Standard",
            action_href=standard_link,
        ),
        _plan_card(
            title="PLAN PROFESSIONAL",
            icon="crown",
            limits=["Hasta 10 sucursales", "Usuarios ilimitados"],
            modules=[
                "Todo lo del Standard",
                "Multi-sucursal con control centralizado",
                "Reportes avanzados y comparativos",
                "Soporte prioritario",
                "Automatizaciones y aprobaciones",
                "Integraciones personalizadas",
            ],
            action_label="Elegir Professional",
            action_href=professional_link,
            highlight=True,
            badge_text="Más popular",
        ),
        _plan_card(
            title="PLAN ENTERPRISE",
            icon="rocket",
            limits=["Sucursales a medida", "Usuarios ilimitados"],
            modules=[
                "Facturación electrónica",
                "API Access y webhooks",
                "Gerente de cuenta dedicado",
                "SLA y soporte 24/7",
                "Implementación a medida",
                "Onboarding y capacitación",
            ],
            action_label="Contactar",
            action_href=enterprise_link,
        ),
        class_name="grid grid-cols-1 md:grid-cols-3 gap-5",
    )

    return modal_container(
        is_open=is_open,
        on_close=on_close,
        title="Elige el plan ideal para tu crecimiento",
        description="Compará opciones y elegí el plan que mejor se adapta a tu negocio.",
        children=[content],
        footer=rx.el.div(
            action_button("Cerrar", on_close, variant="secondary"),
            class_name="flex justify-end",
        ),
        max_width="max-w-5xl",
    )


# =============================================================================
# PAYMENT METHOD BADGE - Componente unificado para badges de método de pago
# =============================================================================

def _method_chip(label: rx.Var | str, color_classes: str) -> rx.Component:
    """Chip estilizado para representar un método de pago."""
    return rx.el.span(
        label,
        class_name=(
            "inline-flex items-center rounded-full px-2 py-0.5 "
            f"text-[11px] font-semibold tracking-wide {color_classes}"
        ),
    )


def payment_method_badge(method: rx.Var[str]) -> rx.Component:
    """Badge unificado para mostrar el método de pago con colores distintivos."""
    is_empty = (method == None) | (method == "") | (method == "-") | (method == "No especificado")  # noqa: E711
    return rx.cond(
        is_empty,
        _method_chip("No especificado", "bg-slate-100 text-slate-500"),
        rx.match(
            method,
            # Crédito / Fiado
            ("Crédito", _method_chip("Crédito", "bg-amber-100 text-amber-700")),
            ("Credito", _method_chip("Crédito", "bg-amber-100 text-amber-700")),
            ("Crédito c/ Inicial", _method_chip("Crédito c/ Inicial", "bg-amber-100 text-amber-700")),
            ("Credito c/ Inicial", _method_chip("Crédito c/ Inicial", "bg-amber-100 text-amber-700")),
            # Efectivo
            ("Efectivo", _method_chip("Efectivo", "bg-emerald-100 text-emerald-700")),
            # Billeteras digitales
            ("Yape", _method_chip("Yape", "bg-violet-100 text-violet-700")),
            ("Billetera Digital (Yape)", _method_chip("Yape", "bg-violet-100 text-violet-700")),
            ("Plin", _method_chip("Plin", "bg-violet-100 text-violet-700")),
            ("Billetera Digital (Plin)", _method_chip("Plin", "bg-violet-100 text-violet-700")),
            # Transferencia
            ("Transferencia", _method_chip("Transferencia", "bg-sky-100 text-sky-700")),
            ("Transferencia Bancaria", _method_chip("Transferencia", "bg-sky-100 text-sky-700")),
            # Tarjetas
            ("Tarjeta", _method_chip(method, "bg-blue-100 text-blue-700")),
            ("T. Debito", _method_chip("T. Débito", "bg-blue-100 text-blue-700")),
            ("T. Credito", _method_chip("T. Crédito", "bg-blue-100 text-blue-700")),
            ("Tarjeta de Débito", _method_chip("Tarjeta Débito", "bg-blue-100 text-blue-700")),
            ("Tarjeta de Crédito", _method_chip("Tarjeta Crédito", "bg-blue-100 text-blue-700")),
            # Pago mixto
            ("Pago Mixto", _method_chip("Mixto", "bg-amber-100 text-amber-700")),
            # Fallback
            _method_chip(method, "bg-slate-100 text-slate-600"),
        ),
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
                "px-4 py-2 bg-slate-200 text-slate-500 rounded-md cursor-not-allowed min-h-[40px]",
                "px-4 py-2 bg-slate-200 rounded-md hover:bg-slate-300 min-h-[40px]",
            ),
        ),
        rx.el.span(
            "Página ",
            current_page.to_string(),
            " de ",
            total_pages.to_string(),
            class_name="text-sm text-slate-600",
        ),
        rx.el.button(
            "Siguiente",
            on_click=on_next,
            disabled=current_page >= total_pages,
            class_name=rx.cond(
                current_page >= total_pages,
                "px-4 py-2 bg-slate-200 text-slate-500 rounded-md cursor-not-allowed min-h-[40px]",
                "px-4 py-2 bg-slate-200 rounded-md hover:bg-slate-300 min-h-[40px]",
            ),
        ),
        class_name="flex flex-col sm:flex-row justify-center items-center gap-3 sm:gap-4 mt-6",
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
                rx.el.h3(title, class_name="text-lg font-semibold text-slate-800")
            )
        if description:
            header_parts.append(
                rx.el.p(description, class_name="text-sm text-slate-600")
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
    parts = [rx.el.h2(title, class_name="text-lg font-semibold text-slate-800")]
    if description:
        parts.append(rx.el.p(description, class_name="text-sm text-slate-600"))
    
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
        "default": "bg-slate-100 text-slate-700",
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


def form_textarea(
    label: str,
    value: rx.Var | str | None = None,
    on_change: Callable | None = None,
    placeholder: str = "",
    rows: int = 4,
    default_value: rx.Var | str | None = None,
    on_blur: Callable | None = None,
) -> rx.Component:
    """
    Crea un textarea con etiqueta.

    Parametros:
        label: Texto de la etiqueta
        value: Valor controlado del textarea (opcional)
        on_change: Manejador en cambios por tecla (opcional)
        placeholder: Texto placeholder
        rows: Numero de filas visibles
        default_value: Valor no controlado inicial (opcional)
        on_blur: Manejador al perder foco (opcional)

    Retorna:
        Componente de textarea con etiqueta
    """
    min_height = rows * TEXTAREA_ROW_HEIGHT
    textarea_props = {
        "placeholder": placeholder,
        "class_name": f"w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 min-h-[{min_height}px]",
    }
    if default_value is not None:
        textarea_props["default_value"] = default_value
    elif value is not None:
        textarea_props["value"] = value
    if on_blur is not None:
        textarea_props["on_blur"] = on_blur
    elif on_change is not None:
        textarea_props["on_change"] = on_change

    return rx.el.div(
        rx.el.label(label, class_name="text-sm font-medium text-slate-700"),
        rx.el.textarea(**textarea_props),
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
        rx.el.label(label, class_name="text-sm font-medium text-slate-600"),
        rx.el.select(
            *option_elements,
            value=value,
            on_change=on_change,
            class_name="w-full h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        class_name="flex flex-col gap-1",
    )
