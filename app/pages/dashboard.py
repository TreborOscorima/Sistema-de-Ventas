"""
Página de Dashboard con métricas y KPIs.
"""
import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  RADIUS,
  SHADOWS,
  TRANSITIONS,
  page_header,
  stat_card,
  empty_state,
  action_button,
)


def _plan_summary_card() -> rx.Component:
  return rx.card(
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.match(
            State.subscription_snapshot["plan_type"],
            ("trial", rx.icon("clock_3", class_name="w-5 h-5 text-amber-700")),
            ("standard", rx.icon("sparkles", class_name="w-5 h-5 text-amber-600")),
            ("professional", rx.icon("crown", class_name="w-5 h-5 text-amber-600")),
            ("enterprise", rx.icon("rocket", class_name="w-5 h-5 text-emerald-600")),
            rx.icon("badge_check", class_name="w-5 h-5 text-indigo-600"),
          ),
          class_name=rx.match(
            State.subscription_snapshot["plan_type"],
            ("trial", f"p-2 {RADIUS['lg']} bg-amber-50"),
            ("professional", f"p-2 {RADIUS['lg']} bg-amber-50"),
            ("enterprise", f"p-2 {RADIUS['lg']} bg-emerald-50"),
            f"p-2 {RADIUS['lg']} bg-indigo-50",
          ),
        ),
        rx.el.div(
          rx.el.p(
            State.subscription_snapshot["plan_display"],
            class_name="text-sm font-semibold text-slate-800",
          ),
          rx.el.p(
            "Estado de suscripción",
            class_name="text-xs text-slate-500",
          ),
          class_name="flex flex-col",
        ),
        rx.el.div(
          rx.badge(
            State.subscription_snapshot["status_label"],
            color_scheme=State.subscription_snapshot["status_tone"],
          ),
          class_name="ml-auto",
        ),
        class_name="flex items-center gap-3",
      ),
      rx.el.div(
        rx.cond(
          State.subscription_snapshot["is_trial"],
          rx.el.div(
            rx.icon("clock-3", class_name="w-4 h-4 text-amber-600"),
            rx.el.span(
              State.subscription_snapshot["trial_days_left"],
              " días restantes",
              class_name="text-sm text-amber-700 font-medium",
            ),
            class_name="flex items-center gap-2",
          ),
          rx.el.div(
            rx.icon("circle_check", class_name="w-4 h-4 text-emerald-600"),
            rx.el.span(
              "Plan activo",
              class_name="text-sm text-emerald-700 font-medium",
            ),
            class_name="flex items-center gap-2",
          ),
        ),
        rx.cond(
          State.subscription_snapshot["is_trial"],
          rx.el.span(
            "Vence: ",
            State.subscription_snapshot["trial_ends_on"],
            class_name="text-xs text-slate-500",
          ),
          rx.fragment(),
        ),
        class_name="mt-3 flex items-center justify-between",
      ),
      rx.cond(
        State.subscription_snapshot["is_trial"],
        rx.fragment(),
        rx.fragment(),
      ),
      rx.el.div(
        rx.el.button(
          rx.icon("settings", class_name="h-4 w-4"),
          rx.el.span("Gestionar Suscripción"),
          on_click=State.go_to_subscription,
          class_name=f"{BUTTON_STYLES['link_primary']} inline-flex",
        ),
        class_name="flex justify-end",
      ),
      class_name="space-y-2",
    ),
    class_name="bg-white p-4 rounded-xl border border-slate-200 shadow-sm",
  )


def _payment_alert_banner() -> rx.Component:
  return rx.cond(
    State.payment_alert_info["show"],
    rx.callout.root(
      rx.callout.icon(
        rx.cond(
          State.payment_alert_info["color"] == "red",
          rx.icon("circle_alert", class_name="h-4 w-4 text-red-600"),
          rx.icon("triangle_alert", class_name="h-4 w-4 text-amber-700"),
        ),
      ),
      rx.callout.text(
        State.payment_alert_info["message"],
        class_name=rx.cond(
          State.payment_alert_info["color"] == "red",
          "font-semibold text-red-950",
          "font-semibold text-amber-950",
        ),
      ),
      color=State.payment_alert_info["color"],
      class_name=rx.cond(
        State.payment_alert_info["color"] == "red",
        "mt-4 border border-red-300 bg-red-100 text-red-950",
        "mt-4 border border-amber-400 bg-amber-200 text-amber-950",
      ),
    ),
    rx.fragment(),
  )


def _stat_card(
  title: str, 
  value: rx.Var, 
  subtitle: str = "", 
  icon: str = "bar-chart-2", 
  color: str = "blue",
  link: str = "",
) -> rx.Component:
  """Tarjeta de estadística clickeable."""
  color_classes = {
    "blue": "bg-blue-50 text-blue-600",
    "green": "bg-emerald-50 text-emerald-600",
    "purple": "bg-purple-50 text-purple-600",
    "amber": "bg-amber-50 text-amber-600",
    "red": "bg-red-50 text-red-600",
  }
  icon_bg = color_classes.get(color, color_classes["blue"])
  
  card_content = rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.icon(icon, class_name="w-5 h-5"),
        class_name=f"p-2 {RADIUS['lg']} {icon_bg}",
      ),
      rx.el.div(
        rx.el.p(title, class_name="text-sm text-slate-500"),
        rx.el.p(value, class_name="text-2xl font-bold text-slate-900 tabular-nums"),
        rx.cond(
          subtitle != "",
          rx.el.p(subtitle, class_name="text-xs text-slate-400"),
          rx.fragment(),
        ),
        class_name="ml-auto text-right",
      ),
      class_name="flex items-start justify-between",
    ),
    class_name=f"bg-white {RADIUS['xl']} border border-slate-200 p-4 {SHADOWS['sm']} {TRANSITIONS['fast']} hover:shadow-md {'cursor-pointer hover:border-indigo-300' if link else ''}",
  )
  
  if link:
    return rx.link(card_content, href=link, class_name="block")
  return card_content


def _period_selector() -> rx.Component:
  """Selector de período de tiempo."""
  def period_btn(label: str, period: str) -> rx.Component:
    return rx.el.button(
      label,
      on_click=lambda: State.set_period(period),
      class_name=rx.cond(
        State.selected_period == period,
        f"px-3 py-1.5 text-sm font-medium {RADIUS['lg']} bg-indigo-600 text-white {TRANSITIONS['fast']}",
        f"px-3 py-1.5 text-sm font-medium {RADIUS['lg']} bg-slate-100 text-slate-600 hover:bg-slate-200 {TRANSITIONS['fast']}",
      ),
    )
  
  return rx.el.div(
    period_btn("Hoy", "today"),
    period_btn("Semana", "week"),
    period_btn("Mes", "month"),
    class_name="flex gap-2",
  )


def _alert_item(alert: dict) -> rx.Component:
  """Item de alerta."""
  severity_styles = {
    "critical": ("bg-red-100 border-red-300 text-red-800", "circle_alert", "text-red-600"),
    "error": ("bg-red-50 border-red-200 text-red-700", "triangle_alert", "text-red-500"),
    "warning": ("bg-amber-50 border-amber-200 text-amber-700", "triangle_alert", "text-amber-500"),
    "info": ("bg-blue-50 border-blue-200 text-blue-700", "info", "text-blue-500"),
  }
  
  severity = alert.get("severity", "info")
  styles = severity_styles.get(severity, severity_styles["info"])
  
  return rx.el.div(
    rx.el.div(
      rx.icon(styles[1], class_name=f"w-5 h-5 {styles[2]} flex-shrink-0"),
      rx.el.div(
        rx.el.p(alert.get("title", ""), class_name="font-medium"),
        rx.el.p(alert.get("message", ""), class_name="text-sm opacity-80"),
        class_name="ml-3",
      ),
      class_name="flex items-start",
    ),
    class_name=f"p-3 {RADIUS['lg']} border {styles[0]}",
  )


def _sales_chart() -> rx.Component:
  """Gráfico de ventas de los últimos 7 días."""
  return rx.el.div(
    rx.el.h3("VENTAS - ÚLTIMOS 7 DÍAS", class_name="text-lg font-semibold text-slate-900 mb-4"),
    rx.recharts.bar_chart(
      rx.recharts.bar(
        data_key="total",
        fill="#4f46e5",
        radius=[6, 6, 0, 0],
      ),
      rx.recharts.x_axis(data_key="day"),
      rx.recharts.y_axis(),
      rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
      rx.recharts.graphing_tooltip(),
      data=State.dash_sales_by_day,
      width="100%",
      height=250,
    ),
    class_name=CARD_STYLES["bordered"],
  )


def _top_products_list() -> rx.Component:
  """Lista de productos más vendidos."""
  list_body = rx.cond(
    State.dash_top_products.length() > 0,
    rx.el.div(
      rx.foreach(
        State.dash_top_products,
        lambda p: rx.el.div(
          rx.el.div(
            rx.el.p(p["name"], class_name="font-medium text-slate-900 truncate"),
            rx.el.p(
              rx.text(f"{p['quantity']} vendidos"),
              class_name="text-sm text-slate-500",
            ),
            class_name="flex-1 min-w-0",
          ),
          rx.el.p(
            rx.el.span(
              State.currency_symbol,
              rx.text(f"{p['revenue']:.2f}"),
            ),
            class_name="font-semibold text-slate-900 tabular-nums",
          ),
          class_name=f"flex items-center justify-between py-3 border-b border-slate-100 last:border-0 {TRANSITIONS['fast']} hover:bg-slate-50 px-2 -mx-2 {RADIUS['md']}",
        ),
      ),
      class_name="space-y-1 pr-2",
    ),
    rx.el.div(
      rx.icon("package", class_name="w-10 h-10 text-slate-300 mx-auto mb-2"),
      rx.el.p("Sin datos para este período", class_name="text-slate-400 text-center"),
      class_name="py-8",
    ),
  )
  return rx.el.div(
    rx.el.h3(
      rx.text(f"TOP PRODUCTOS - {State.period_label}"),
      class_name="text-lg font-semibold text-slate-900 mb-4",
    ),
    rx.el.div(
      list_body,
      class_name="flex-1 overflow-y-auto",
    ),
    class_name=f"{CARD_STYLES['bordered']} flex flex-col h-full",
  )


def _category_chart() -> rx.Component:
  """Gráfico y tabla de ventas por categoría."""
  return rx.el.div(
    # Header con título y botón exportar
    rx.el.div(
      rx.el.h3(
        rx.text(f"VENTAS POR CATEGORÍA - {State.period_label}"),
        class_name="text-lg font-semibold text-slate-900",
      ),
      rx.el.button(
        rx.icon("file-spreadsheet", class_name="w-4 h-4 mr-1.5"),
        "Exportar Excel",
        on_click=State.export_categories_excel,
        class_name=BUTTON_STYLES["success"] + " !py-1.5 !px-3 text-sm",
      ),
      class_name="flex items-center justify-between mb-4",
    ),
    # Gráfico de torta
    rx.el.div(
      rx.recharts.pie_chart(
        rx.recharts.pie(
          data=State.dash_sales_by_category,
          data_key="total",
          name_key="category",
          cx="50%",
          cy="50%",
          inner_radius=40,
          outer_radius=80,
          padding_angle=2,
          fill="#6366f1",
          label=True,
        ),
        rx.recharts.graphing_tooltip(),
        rx.recharts.legend(),
        width="100%",
        height=240,
      ),
      class_name="flex-shrink-0",
    ),
    # Tabla detallada
    rx.el.div(
      rx.cond(
        State.dash_sales_by_category.length() > 0,
        rx.el.div(
          # Header
          rx.el.div(
            rx.el.span("Categoría", class_name="flex-1 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider"),
            rx.el.span("Ventas", class_name="w-28 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider"),
            rx.el.span("%", class_name="w-16 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider"),
            class_name="flex items-center py-2.5 px-3 border-b border-slate-200 bg-slate-50",
          ),
          # Body con scroll
          rx.el.div(
            rx.foreach(
              State.dash_sales_by_category,
              lambda cat: rx.el.div(
                rx.el.span(cat["category"], class_name="flex-1 text-sm text-slate-900 truncate"),
                rx.el.span(
                  State.currency_symbol,
                  rx.text(f"{cat['total']:.2f}"),
                  class_name="w-28 text-sm text-slate-900 font-medium text-right tabular-nums",
                ),
                rx.el.span(
                  rx.text(f"{cat['percentage']}%"),
                  class_name="w-16 text-sm text-slate-500 text-right tabular-nums",
                ),
                class_name=f"flex items-center py-2.5 px-3 border-b border-slate-100 {TRANSITIONS['fast']} hover:bg-slate-50",
              ),
            ),
            class_name="flex-1 min-h-0 overflow-y-auto",
          ),
          # Footer
          rx.el.div(
            rx.el.span("Total", class_name="flex-1 text-sm font-bold text-slate-900"),
            rx.el.span(State.formatted_category_total, class_name="w-28 text-sm font-bold text-slate-900 text-right tabular-nums"),
            rx.el.span("100%", class_name="w-16 text-sm font-bold text-slate-500 text-right"),
            class_name="flex items-center py-2.5 px-3 border-t-2 border-slate-200 bg-slate-50",
          ),
          class_name=f"flex flex-col h-full overflow-hidden {RADIUS['lg']} border border-slate-200",
        ),
        rx.el.div(
          rx.icon("pie-chart", class_name="w-10 h-10 text-slate-300 mx-auto mb-2"),
          rx.el.p("Sin datos para este período", class_name="text-slate-400 text-center"),
          class_name="py-8",
        ),
      ),
      class_name="mt-4",
    ),
    class_name=f"{CARD_STYLES['bordered']} flex flex-col h-full",
  )


def _alerts_panel() -> rx.Component:
  """Panel de alertas del sistema."""
  return rx.el.div(
    rx.el.div(
      rx.el.h3("ALERTAS DEL SISTEMA", class_name="text-lg font-semibold text-slate-900"),
      rx.cond(
        State.alert_count > 0,
        rx.el.span(
          State.alert_count,
          class_name=f"ml-2 px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 {RADIUS['full']}",
        ),
        rx.fragment(),
      ),
      class_name="flex items-center mb-4",
    ),
    rx.cond(
      State.alert_count > 0,
      rx.el.div(
        rx.foreach(State.alerts, _alert_item),
        class_name="space-y-2 max-h-64 overflow-y-auto",
      ),
      rx.el.div(
        rx.icon("circle-check", class_name="w-12 h-12 text-emerald-400 mx-auto mb-2"),
        rx.el.p("Sin alertas pendientes", class_name="text-slate-500 text-center"),
        class_name="py-8",
      ),
    ),
    class_name=CARD_STYLES["bordered"],
  )


def _kpis_grid() -> rx.Component:
  """Grid de KPIs principales con tarjeta de período seleccionado."""
  return rx.el.div(
    # Tarjeta principal del período seleccionado
    rx.el.div(
      rx.el.div(
        rx.el.div(
          rx.el.div(
            rx.icon("trending-up", class_name="w-6 h-6"),
            class_name=f"p-3 {RADIUS['lg']} bg-indigo-100 text-indigo-600",
          ),
          rx.el.div(
            rx.el.p(State.period_label, class_name="text-sm text-slate-500"),
            rx.el.p(State.formatted_period_sales, class_name="text-3xl font-bold text-slate-900 tabular-nums tracking-tight"),
            rx.el.div(
              rx.el.span(
                rx.cond(
                  State.sales_trend_up,
                  rx.icon("arrow-up", class_name="w-4 h-4 inline"),
                  rx.icon("arrow-down", class_name="w-4 h-4 inline"),
                ),
              ),
              rx.el.span(
                State.formatted_sales_change,
                class_name=rx.cond(
                  State.sales_trend_up,
                  "text-emerald-600 font-medium",
                  "text-red-600 font-medium",
                ),
              ),
              rx.el.span(" vs período anterior", class_name="text-slate-400 ml-1"),
              class_name="flex items-center text-sm mt-1",
            ),
            class_name="ml-4",
          ),
          class_name="flex items-center",
        ),
        class_name="p-6",
      ),
      class_name=f"bg-gradient-to-br from-white to-indigo-50 {RADIUS['xl']} border border-slate-200 {SHADOWS['sm']} col-span-1 sm:col-span-2",
    ),
    # Ticket Promedio con período dinámico
    rx.link(
      rx.el.div(
        rx.el.div(
          rx.el.div(
            rx.icon("receipt", class_name="w-5 h-5"),
            class_name=f"p-2 {RADIUS['lg']} bg-amber-50 text-amber-600",
          ),
          rx.el.div(
            rx.el.p("Ticket Promedio", class_name="text-sm text-slate-500"),
            rx.el.p(State.formatted_avg_ticket, class_name="text-2xl font-bold text-slate-900 tabular-nums"),
            rx.el.p(State.period_label, class_name="text-xs text-slate-400"),
            class_name="ml-auto text-right",
          ),
          class_name="flex items-start justify-between",
        ),
        class_name=f"bg-white {RADIUS['xl']} border border-slate-200 p-4 {SHADOWS['sm']} {TRANSITIONS['fast']} hover:shadow-md cursor-pointer hover:border-indigo-300",
      ),
      href="/historial",
      class_name="block",
    ),
    # Cantidad de ventas del período
    rx.link(
      rx.el.div(
        rx.el.div(
          rx.el.div(
            rx.icon("shopping-bag", class_name="w-5 h-5"),
            class_name=f"p-2 {RADIUS['lg']} bg-emerald-50 text-emerald-600",
          ),
          rx.el.div(
            rx.el.p("Transacciones", class_name="text-sm text-slate-500"),
            rx.el.p(State.period_sales_count, class_name="text-2xl font-bold text-slate-900 tabular-nums"),
            rx.el.p(State.period_label, class_name="text-xs text-slate-400"),
            class_name="ml-auto text-right",
          ),
          class_name="flex items-start justify-between",
        ),
        class_name=f"bg-white {RADIUS['xl']} border border-slate-200 p-4 {SHADOWS['sm']} {TRANSITIONS['fast']} hover:shadow-md cursor-pointer hover:border-indigo-300",
      ),
      href="/historial",
      class_name="block",
    ),
    class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
  )


def _secondary_kpis() -> rx.Component:
  """KPIs secundarios con links a secciones."""
  return rx.el.div(
    _stat_card(
      "Clientes",
      State.total_clients,
      "Total registrados",
      "users",
      "blue",
      link="/clientes",
    ),
    _stat_card(
      "Créditos Activos",
      State.active_credits,
      "Con cuotas pendientes",
      "credit-card",
      "purple",
      link="/cuentas",
    ),
    _stat_card(
      "Deuda Pendiente",
      State.formatted_pending_debt,
      "Por cobrar",
      "wallet",
      "amber",
      link="/cuentas",
    ),
    _stat_card(
      "Stock Bajo",
      State.low_stock_count,
      "Productos a reponer",
      "package",
      "red",
      link="/inventario",
    ),
    class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
  )


def dashboard_page() -> rx.Component:
  """Página principal del dashboard."""
  return rx.el.div(
    # Header
    page_header(
      "DASHBOARD",
      rx.cond(
        State.last_refresh != "",
        rx.text(f"Última actualización: {State.last_refresh}"),
        rx.text("Cargando..."),
      ),
      actions=[
        # Selector de período
        _period_selector(),
        # Botón actualizar
        rx.el.button(
          rx.cond(
            State.dashboard_loading,
            rx.icon("loader-circle", class_name="w-4 h-4 animate-spin"),
            rx.icon("refresh-cw", class_name="w-4 h-4"),
          ),
          rx.el.span("Actualizar", class_name="ml-2"),
          on_click=State.load_dashboard,
          disabled=State.dashboard_loading,
          class_name=rx.cond(
            State.dashboard_loading,
            BUTTON_STYLES["disabled"],
            BUTTON_STYLES["primary"],
          ),
        ),
      ],
    ),

    _payment_alert_banner(),

    rx.el.div(
      _plan_summary_card(),
      class_name="mt-4 flex-1 min-h-0",
    ),
    
    # KPIs principales
    _kpis_grid(),
    
    # KPIs secundarios
    rx.el.div(_secondary_kpis(), class_name="mt-4"),
    
    # Gráficos y alertas
    rx.el.div(
      rx.el.div(
        _sales_chart(),
        class_name="lg:col-span-2",
      ),
      rx.el.div(
        _alerts_panel(),
      ),
      class_name="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6",
    ),
    
    # Segunda fila de gráficos
    rx.el.div(
      rx.el.div(_top_products_list(), class_name="h-full"),
      rx.el.div(_category_chart(), class_name="h-full"),
      class_name="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6 items-stretch",
    ),
    
    on_mount=State.load_dashboard,
    class_name="p-6 ",
  )
