"""
Reusable UI components for the Sistema de Ventas application.

This module provides common UI components that follow the DRY principle
to reduce code duplication across pages.
"""
import reflex as rx
from typing import Callable


# Button style variants - eliminates hardcoded CSS strings across files
BUTTON_STYLES = {
    "primary": "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[44px]",
    "primary_sm": "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[40px]",
    "secondary": "flex items-center justify-center gap-2 px-4 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[44px]",
    "secondary_sm": "flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-gray-700 hover:bg-gray-50 min-h-[40px]",
    "success": "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-green-600 text-white hover:bg-green-700 min-h-[44px]",
    "success_sm": "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-green-600 text-white hover:bg-green-700 min-h-[40px]",
    "danger": "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 min-h-[44px]",
    "danger_sm": "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 min-h-[40px]",
    "warning": "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-amber-600 text-white hover:bg-amber-700 min-h-[44px]",
    "ghost": "flex items-center justify-center gap-2 px-4 py-2 rounded-md text-gray-600 hover:bg-gray-100 min-h-[44px]",
    "link_primary": "flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-blue-600 hover:bg-blue-50 min-h-[40px]",
    "link_danger": "flex items-center justify-center gap-2 px-3 py-2 rounded-md border text-red-600 hover:bg-red-50 min-h-[40px]",
    "disabled": "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[44px]",
    "disabled_sm": "flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[40px]",
    "icon_danger": "p-2 text-red-500 hover:bg-red-100 rounded-full",
    "icon_primary": "p-2 text-blue-500 hover:bg-blue-100 rounded-full",
    "icon_indigo": "p-2 text-indigo-500 hover:bg-indigo-100 rounded-full",
}

# Input style constants
INPUT_STYLES = {
    "default": "w-full p-2 border rounded-md",
    "disabled": "w-full p-2 border rounded-md bg-gray-100",
    "search": "w-full p-2 border rounded-md",
}

# Card style constants
CARD_STYLES = {
    "default": "bg-white p-4 sm:p-6 rounded-lg shadow-md",
    "bordered": "bg-white border border-gray-200 rounded-lg p-4 sm:p-5 shadow-sm",
}

# Table styles
TABLE_HEADER_STYLE = "bg-gray-100"
TABLE_ROW_STYLE = "border-b"


def action_button(
    text: str | rx.Component,
    on_click: Callable,
    variant: str = "primary",
    icon: str | None = None,
    disabled: rx.Var | bool = False,
    disabled_variant: str = "disabled",
) -> rx.Component:
    """
    Creates a styled action button with consistent styling.
    
    Args:
        text: Button text or component
        on_click: Click handler
        variant: Style variant key from BUTTON_STYLES
        icon: Optional lucide icon name
        disabled: Whether button is disabled (can be a reactive var)
        disabled_variant: Style to use when disabled
    
    Returns:
        A styled button component
    """
    content = []
    if icon:
        content.append(rx.icon(icon, class_name="h-4 w-4"))
    if isinstance(text, str):
        content.append(rx.el.span(text))
    else:
        content.append(text)
    
    return rx.el.button(
        *content,
        on_click=on_click,
        disabled=disabled,
        class_name=rx.cond(
            disabled,
            BUTTON_STYLES.get(disabled_variant, BUTTON_STYLES["disabled"]),
            BUTTON_STYLES.get(variant, BUTTON_STYLES["primary"]),
        ) if isinstance(disabled, rx.Var) else (
            BUTTON_STYLES.get(disabled_variant, BUTTON_STYLES["disabled"]) if disabled 
            else BUTTON_STYLES.get(variant, BUTTON_STYLES["primary"])
        ),
    )


def icon_button(
    icon: str,
    on_click: Callable,
    variant: str = "icon_primary",
    disabled: rx.Var | bool = False,
    aria_label: str = "",
) -> rx.Component:
    """
    Creates a circular icon-only button.
    
    Args:
        icon: Lucide icon name
        on_click: Click handler
        variant: Style variant from BUTTON_STYLES
        disabled: Whether button is disabled
        aria_label: Accessibility label
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
    Creates a labeled form field wrapper.
    
    Args:
        label: Field label text
        input_component: The input/select/textarea component
        label_style: CSS class for the label
    
    Returns:
        A div containing label and input
    """
    return rx.el.div(
        rx.el.label(label, class_name=label_style),
        input_component,
        class_name="flex flex-col gap-1",
    )


def text_input(
    placeholder: str = "",
    value: rx.Var | str = "",
    on_change: Callable | None = None,
    input_type: str = "text",
    disabled: bool = False,
    style: str = "default",
) -> rx.Component:
    """
    Creates a styled text input.
    
    Args:
        placeholder: Placeholder text
        value: Input value (can be reactive)
        on_change: Change handler
        input_type: HTML input type
        disabled: Whether input is disabled
        style: Style key from INPUT_STYLES
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
    )


def section_card(
    title: str,
    description: str = "",
    children: list[rx.Component] | None = None,
    style: str = "bordered",
) -> rx.Component:
    """
    Creates a card section with title and optional description.
    
    Args:
        title: Section title
        description: Optional description text
        children: Child components
        style: Card style key from CARD_STYLES
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
    Creates a status badge with appropriate coloring.
    
    Args:
        status: Status value
        status_colors: Dict mapping status to (bg_color, text_color) CSS classes.
                      Defaults to common status colors.
    """
    if status_colors is None:
        status_colors = {
            "pagado": ("bg-emerald-100", "text-emerald-700"),
            "pendiente": ("bg-amber-100", "text-amber-700"),
            "cancelado": ("bg-red-100", "text-red-700"),
            "eliminado": ("bg-gray-200", "text-gray-700"),
        }
    
    # For reactive status, we use rx.cond chains
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
    
    # For static status
    colors = status_colors.get(status.lower(), ("bg-gray-100", "text-gray-700"))
    return rx.el.span(
        status.capitalize(),
        class_name=f"px-2 py-1 text-xs font-semibold rounded-full {colors[0]} {colors[1]}",
    )


def empty_state(message: str) -> rx.Component:
    """
    Creates a centered empty state message.
    
    Args:
        message: Message to display
    """
    return rx.el.p(
        message,
        class_name="text-gray-500 text-center py-8",
    )


def page_title(title: str, subtitle: str = "") -> rx.Component:
    """
    Creates a page title with optional subtitle.
    
    Args:
        title: Main title
        subtitle: Optional subtitle/description
    """
    parts = [
        rx.el.h1(title, class_name="text-2xl font-bold text-gray-800"),
    ]
    if subtitle:
        parts.append(
            rx.el.p(subtitle, class_name="text-sm text-gray-600")
        )
    
    return rx.el.div(*parts, class_name="mb-6")


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
    Creates a modal dialog container.
    
    Args:
        is_open: Reactive var controlling visibility
        on_close: Handler for closing the modal
        title: Modal title
        description: Optional description
        children: Modal body content
        footer: Footer content (usually buttons)
        max_width: Tailwind max-width class
    """
    body_parts = [
        rx.el.h3(title, class_name="text-lg font-semibold text-gray-800"),
    ]
    if description:
        body_parts.append(
            rx.el.p(description, class_name="text-sm text-gray-600")
        )
    
    if children:
        body_parts.extend(children)
    
    if footer:
        body_parts.append(footer)
    
    return rx.cond(
        is_open,
        rx.el.div(
            rx.el.div(
                on_click=on_close,
                class_name="fixed inset-0 bg-black/40",
            ),
            rx.el.div(
                *body_parts,
                class_name=f"relative z-10 w-full {max_width} rounded-xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto space-y-4",
            ),
            class_name="fixed inset-0 z-50 flex items-center justify-center px-4",
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
    Creates a standardized filter section.
    
    Args:
        filters: List of filter input components
        on_search: Handler for search button
        on_reset: Handler for reset button
        extra_buttons: Additional action buttons
        grid_cols: Tailwind grid column classes
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
    Creates a pair of date filter inputs.
    
    Args:
        start_value: Start date value
        end_value: End date value
        on_start_change: Handler for start date change
        on_end_change: Handler for end date change
        start_label: Label for start date
        end_label: Label for end date
    
    Returns:
        Tuple of (start_input, end_input) components
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
    Creates a statistics card with icon, title and value.
    
    Args:
        icon: Lucide icon name
        title: Card title/label
        value: Value to display (can be reactive var or component)
        icon_color: Tailwind color class for the icon
    
    Returns:
        A styled stat card component
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
    Creates pagination controls with prev/next buttons and page info.
    
    Args:
        current_page: Current page number (reactive var)
        total_pages: Total number of pages (reactive var)
        on_prev: Handler for previous page
        on_next: Handler for next page
    
    Returns:
        A pagination control component
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
    Creates a styled data table.
    
    Args:
        headers: List of (header_text, alignment_class) tuples
        rows: The tbody content (usually rx.foreach result)
        empty_message: Message to show when table is empty
        has_data: Whether there is data to display (reactive var for dynamic checking)
    
    Returns:
        A styled table component
    """
    header_cells = [
        rx.el.th(text, class_name=f"py-3 px-4 {align}")
        for text, align in headers
    ]
    
    # Build the empty state component
    empty_component = rx.el.p(empty_message, class_name="text-gray-500 text-center py-8")
    
    # Handle both reactive and static has_data values
    if isinstance(has_data, rx.Var):
        # For reactive vars, use rx.cond
        empty_state_section = rx.cond(
            has_data,
            rx.fragment(),
            empty_component,
        )
    else:
        # For static booleans, conditionally include the component
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
