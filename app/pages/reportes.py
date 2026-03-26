"""
Página de Reportes Contables y Financieros.

Proporciona una interfaz para generar reportes profesionales
para evaluaciones administrativas, contables y financieras.
"""
import reflex as rx

from app.state import State
from app.components.ui import (
    BUTTON_STYLES,
    CARD_STYLES,
    INPUT_STYLES,
    SPACING,
    TYPOGRAPHY,
    page_title,
    permission_guard,
)


def _report_type_card(report_type: dict) -> rx.Component:
    """Tarjeta de tipo de reporte — responsive y accesible."""
    is_selected = State.report_type == report_type["value"]

    return rx.el.button(
        rx.el.div(
            rx.icon(report_type["icon"], class_name="w-7 h-7 sm:w-8 sm:h-8 mb-2"),
            rx.el.p(report_type["label"], class_name="text-sm font-medium text-center"),
            class_name="flex flex-col items-center p-3 sm:p-4",
        ),
        on_click=State.set_report_type(report_type["value"]),
        title=report_type["label"],
        aria_label=report_type["label"],
        class_name=rx.cond(
            is_selected,
            "bg-indigo-50 border-2 border-indigo-500 rounded-xl text-indigo-700 transition-all",
            "bg-white border-2 border-slate-200 rounded-xl text-slate-600 hover:border-slate-300 hover:bg-slate-50 transition-all",
        ),
    )


def _period_button(period: dict) -> rx.Component:
    """Botón de período — accesible."""
    is_selected = State.report_period == period["value"]

    return rx.el.button(
        period["label"],
        on_click=State.set_report_period(period["value"]),
        title=period["label"],
        aria_label=period["label"],
        class_name=rx.cond(
            is_selected,
            "px-3 sm:px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-md",
            "px-3 sm:px-4 py-2 text-sm font-medium bg-slate-100 text-slate-600 rounded-md hover:bg-slate-200",
        ),
    )


def _custom_date_picker() -> rx.Component:
    """Selector de fechas personalizadas."""
    return rx.cond(
        State.report_period == "custom",
        rx.el.div(
            rx.el.div(
                rx.el.label("Desde:", class_name=TYPOGRAPHY["label"]),
                rx.el.input(
                    type="date",
                    value=State.custom_start_date,
                    on_change=State.set_custom_start,
                    aria_label="Fecha de inicio del periodo",
                    class_name=f"mt-1 {INPUT_STYLES['default']}",
                ),
                class_name="flex-1",
            ),
            rx.el.div(
                rx.el.label("Hasta:", class_name=TYPOGRAPHY["label"]),
                rx.el.input(
                    type="date",
                    value=State.custom_end_date,
                    on_change=State.set_custom_end,
                    aria_label="Fecha de fin del periodo",
                    class_name=f"mt-1 {INPUT_STYLES['default']}",
                ),
                class_name="flex-1",
            ),
            class_name="flex flex-col sm:flex-row gap-3 sm:gap-4 mt-4 p-4 bg-slate-50 rounded-xl",
        ),
        rx.fragment(),
    )


def _report_options() -> rx.Component:
    """Opciones adicionales del reporte."""
    return rx.el.div(
        rx.el.h4("Opciones", class_name="text-sm font-semibold text-slate-700 mb-3"),
        
        # Opción para ventas: incluir anuladas
        rx.cond(
            State.report_type == "ventas",
            rx.el.div(
                rx.el.div(
                    rx.el.span("Incluir ventas anuladas", class_name="text-sm text-slate-600"),
                    rx.switch(
                        checked=State.include_cancelled,
                        on_change=State.toggle_include_cancelled,
                    ),
                    class_name="flex items-center justify-between",
                ),
                class_name="py-2",
            ),
            rx.fragment(),
        ),
        
        # Opción para inventario: incluir sin stock
        rx.cond(
            State.report_type == "inventario",
            rx.el.div(
                rx.el.div(
                    rx.el.span("Incluir productos sin stock", class_name="text-sm text-slate-600"),
                    rx.switch(
                        checked=State.include_zero_stock,
                        on_change=State.toggle_include_zero_stock,
                    ),
                    class_name="flex items-center justify-between",
                ),
                class_name="py-2",
            ),
            rx.fragment(),
        ),
        
        class_name="p-4 bg-slate-50 rounded-xl",
    )


def _report_description() -> rx.Component:
    """Descripción del reporte seleccionado."""
    descriptions = {
        "ventas": rx.fragment(
            rx.el.p("📊 ", rx.el.strong("Reporte de Ventas Consolidado"), class_name="font-medium text-slate-800"),
            rx.el.ul(
                rx.el.li("✓ Resumen ejecutivo con indicadores clave"),
                rx.el.li("✓ Ventas diarias con utilidad y margen"),
                rx.el.li("✓ Análisis por categoría de producto"),
                rx.el.li("✓ Desglose por método de pago"),
                rx.el.li("✓ Ventas por vendedor"),
                rx.el.li("✓ Detalle completo de transacciones"),
                class_name="text-sm text-slate-600 mt-2 space-y-1 list-none",
            ),
        ),
        "inventario": rx.fragment(
            rx.el.p("📦 ", rx.el.strong("Inventario Valorizado"), class_name="font-medium text-slate-800"),
            rx.el.ul(
                rx.el.li("✓ Valorización total al costo y precio venta"),
                rx.el.li("✓ Utilidad potencial del inventario"),
                rx.el.li("✓ Análisis por categoría"),
                rx.el.li("✓ Detalle con márgenes por producto"),
                rx.el.li("✓ Productos con stock crítico"),
                rx.el.li("✓ Estado del stock con colores"),
                class_name="text-sm text-slate-600 mt-2 space-y-1 list-none",
            ),
        ),
        "cuentas": rx.fragment(
            rx.el.p("💳 ", rx.el.strong("Cuentas por Cobrar"), class_name="font-medium text-slate-800"),
            rx.el.ul(
                rx.el.li("✓ Antigüedad de cartera (0-30, 31-60, 61-90, >90 días)"),
                rx.el.li("✓ Provisión sugerida para cobranza dudosa"),
                rx.el.li("✓ Deuda por cliente"),
                rx.el.li("✓ Detalle de cuotas pendientes"),
                rx.el.li("✓ Días de mora por cuota"),
                rx.el.li("✓ Indicadores visuales de riesgo"),
                class_name="text-sm text-slate-600 mt-2 space-y-1 list-none",
            ),
        ),
        "caja": rx.fragment(
            rx.el.p("💰 ", rx.el.strong("Gestión de Caja"), class_name="font-medium text-slate-800"),
            rx.el.ul(
                rx.el.li("✓ Resumen de aperturas y cierres"),
                rx.el.li("✓ Recaudación por método de pago"),
                rx.el.li("✓ Detalle de movimientos"),
                rx.el.li("✓ Totales del período"),
                class_name="text-sm text-slate-600 mt-2 space-y-1 list-none",
            ),
        ),
    }
    
    return rx.el.div(
        rx.match(
            State.report_type,
            ("ventas", descriptions["ventas"]),
            ("inventario", descriptions["inventario"]),
            ("cuentas", descriptions["cuentas"]),
            ("caja", descriptions["caja"]),
            descriptions["ventas"],
        ),
        class_name="p-4 bg-indigo-50 border border-indigo-100 rounded-xl",
    )


def _generate_button() -> rx.Component:
    """Botón para generar el reporte — accesible."""
    return rx.el.button(
        rx.cond(
            State.report_loading,
            rx.fragment(
                rx.icon("loader-circle", class_name="w-5 h-5 mr-2 animate-spin"),
                "Generando...",
            ),
            rx.fragment(
                rx.icon("file-down", class_name="w-5 h-5 mr-2"),
                "Generar Reporte",
            ),
        ),
        on_click=State.generate_report,
        disabled=State.report_loading,
        title="Generar reporte en formato Excel",
        aria_label="Generar reporte en formato Excel",
        class_name=f"{BUTTON_STYLES['success']} w-full disabled:opacity-50 disabled:cursor-not-allowed",
    )


def _download_button() -> rx.Component:
    """Botón para descargar el reporte generado — accesible."""
    return rx.el.button(
        rx.fragment(
            rx.icon("download", class_name="w-5 h-5 mr-2"),
            "Descargar Reporte",
        ),
        on_click=State.download_report,
        title="Descargar reporte generado",
        aria_label="Descargar reporte generado en Excel",
        class_name=f"{BUTTON_STYLES['primary']} w-full",
    )


def _error_message() -> rx.Component:
    """Mensaje de error si hay."""
    return rx.cond(
        State.report_error != "",
        rx.el.div(
            rx.icon("circle-alert", class_name="w-5 h-5 mr-2"),
            State.report_error,
            role="alert",
            class_name="flex items-center p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl",
        ),
        rx.fragment(),
    )


def reportes_page() -> rx.Component:
    """Página principal de reportes."""
    content = rx.el.div(
        # Header
        page_title(
            "REPORTES CONTABLES Y FINANCIEROS",
            "Genera reportes profesionales para evaluaciones administrativas",
        ),
        
        rx.el.div(
            # Columna izquierda: Selección
            rx.el.div(
                # Tipo de reporte
                rx.el.div(
                    rx.el.h3("1. SELECCIONA EL TIPO DE REPORTE", class_name=f"{TYPOGRAPHY['section_title']} mb-4"),
                    rx.el.div(
                        rx.foreach(State.report_types, _report_type_card),
                        class_name="grid grid-cols-2 sm:grid-cols-2 gap-3",
                    ),
                    class_name=f"{CARD_STYLES['default']} mb-4",
                ),
                
                # Período (solo para ventas y caja)
                rx.cond(
                    (State.report_type == "ventas") | (State.report_type == "caja"),
                    rx.el.div(
                        rx.el.h3("2. SELECCIONA EL PERIODO", class_name=f"{TYPOGRAPHY['section_title']} mb-4"),
                        rx.el.div(
                            rx.foreach(State.period_options, _period_button),
                            class_name="flex flex-wrap gap-2",
                        ),
                        _custom_date_picker(),
                        class_name=f"{CARD_STYLES['default']} mb-4",
                    ),
                    rx.fragment(),
                ),
                
                # Opciones
                rx.cond(
                    (State.report_type == "ventas") | (State.report_type == "inventario"),
                    rx.el.div(
                        rx.el.h3(
                            rx.cond(
                                (State.report_type == "ventas") | (State.report_type == "caja"),
                                "3. OPCIONES ADICIONALES",
                                "2. OPCIONES ADICIONALES",
                            ),
                            class_name="text-lg font-semibold text-slate-800 mb-4",
                        ),
                        _report_options(),
                        class_name="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 shadow-sm",
                    ),
                    rx.fragment(),
                ),
                
                class_name="flex-1 min-w-0",
            ),
            
            # Columna derecha: Descripción y generar
            rx.el.div(
                rx.el.div(
                    rx.el.h3("CONTENIDO DEL REPORTE", class_name=f"{TYPOGRAPHY['section_title']} mb-4"),
                    _report_description(),
                    rx.el.div(
                        rx.el.p(
                            rx.icon("info", class_name="w-4 h-4 mr-2 inline"),
                            "El reporte se generará en formato Excel (.xlsx) con múltiples hojas para facilitar el análisis.",
                            class_name="text-sm text-slate-500",
                        ),
                        class_name="mt-4",
                    ),
                    class_name=f"{CARD_STYLES['default']} mb-4",
                ),
                
                # Resumen de selección
                rx.el.div(
                    rx.el.h3("RESUMEN", class_name=f"{TYPOGRAPHY['section_title']} mb-4"),
                    rx.el.div(
                        rx.el.div(
                            rx.el.span("Reporte:", class_name="text-slate-500"),
                            rx.el.span(State.selected_report_label, class_name="font-medium text-slate-800 ml-2 text-right"),
                            class_name="flex items-start justify-between gap-3 py-2 border-b border-slate-100",
                        ),
                        rx.cond(
                            (State.report_type == "ventas") | (State.report_type == "caja"),
                            rx.el.div(
                                rx.el.span("Período:", class_name="text-slate-500"),
                                rx.el.span(State.report_period_label, class_name="font-medium text-slate-800 ml-2 text-right"),
                                class_name="flex items-start justify-between gap-3 py-2 border-b border-slate-100",
                            ),
                            rx.fragment(),
                        ),
                        rx.el.div(
                            rx.el.span("Formato:", class_name="text-slate-500"),
                            rx.el.span("Excel (.xlsx)", class_name="font-medium text-slate-800 ml-2 text-right"),
                            class_name="flex items-start justify-between gap-3 py-2",
                        ),
                        class_name="mb-6",
                    ),
                    _error_message(),
                    rx.cond(
                        State.report_ready,
                        rx.el.div(
                            rx.el.div(
                                rx.icon("circle-check", class_name="w-4 h-4 mr-2 text-emerald-600"),
                                "Reporte listo para descargar.",
                                class_name="flex items-center text-sm text-emerald-700 mb-3",
                            ),
                            _download_button(),
                            class_name="mb-4",
                        ),
                        rx.fragment(),
                    ),
                    _generate_button(),
                    class_name="bg-white rounded-xl border border-slate-200 p-4 sm:p-6 shadow-sm",
                ),
                
                class_name="w-full xl:w-[23rem] 2xl:w-[25rem] shrink-0",
            ),
            
            class_name="flex flex-col xl:flex-row gap-4 lg:gap-6",
        ),
        
        class_name="p-3 sm:p-4 lg:p-6",
    )
    return permission_guard(
        has_permission=State.can_export_data,
        content=content,
        redirect_message="Acceso denegado a Reportes",
    )
