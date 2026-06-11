import reflex as rx

from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  TYPOGRAPHY,
)


def soccer_ball_icon(class_name: str = "h-5 w-5") -> rx.Component:
  """SVG simple de balón de fútbol para evitar iconos desconocidos."""
  return rx.el.svg(
    rx.el.circle(cx="12", cy="12", r="9", fill="none", stroke="currentColor", stroke_width="2"),
    rx.el.polygon(
      points="12 7 15 9 14 13 10 13 9 9",
      fill="none",
      stroke="currentColor",
      stroke_width="2",
    ),
    rx.el.line(x1="12", y1="7", x2="10", y2="4", stroke="currentColor", stroke_width="2"),
    rx.el.line(x1="12", y1="7", x2="14", y2="4", stroke="currentColor", stroke_width="2"),
    rx.el.line(x1="10", y1="13", x2="8", y2="16", stroke="currentColor", stroke_width="2"),
    rx.el.line(x1="14", y1="13", x2="16", y2="16", stroke="currentColor", stroke_width="2"),
    rx.el.line(x1="9", y1="9", x2="6", y2="9", stroke="currentColor", stroke_width="2"),
    rx.el.line(x1="15", y1="9", x2="18", y2="9", stroke="currentColor", stroke_width="2"),
    rx.el.line(x1="12", y1="7", x2="12", y2="11", stroke="currentColor", stroke_width="2"),
    viewBox="0 0 24 24",
    class_name=class_name,
    stroke="currentColor",
    fill="none",
    stroke_linecap="round",
    stroke_linejoin="round",
  )


def sport_selector() -> rx.Component:
  """Selector de deporte para reservas de canchas."""
  return rx.el.div(
    rx.el.div(
      rx.el.p("ALQUILER DE CAMPOS DE FUTBOL Y VOLEY", class_name=TYPOGRAPHY["section_title"]),
      rx.el.p(
        "Elige el deporte para gestionar reservas, pagos y cancelaciones.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="flex flex-col gap-1",
    ),
    rx.el.div(
      rx.el.button(
        rx.cond(
          State.field_rental_sport == "futbol",
          rx.fragment(
            rx.el.div(
              class_name="absolute inset-0 rounded-xl bg-[conic-gradient(from_0deg,#22d3ee,#a855f7,#f59e0b,#22d3ee)] opacity-45 blur-[0.5px] animate-[spin_18s_linear_infinite] pointer-events-none",
            ),
            rx.el.div(
              class_name="absolute inset-0 rounded-xl bg-[conic-gradient(from_0deg,transparent_0deg,transparent_30deg,rgba(34,211,238,0.25)_45deg,rgba(34,211,238,0.85)_140deg,rgba(168,85,247,1)_240deg,rgba(245,158,11,1)_320deg,rgba(34,211,238,0.95)_360deg)] blur-[1px] animate-[spin_6s_linear_infinite] pointer-events-none",
            ),
          ),
          rx.fragment(),
        ),
        rx.el.div(
          rx.el.div(
            class_name="absolute inset-0 rounded-[10px] bg-black/45 pointer-events-none",
          ),
          rx.el.div(
            rx.el.img(
              src="/balon-futbol.png",
              alt="Balon futbol",
              loading="lazy",
              decoding="async",
              class_name="h-6 w-6",
            ),
            rx.el.span(
              "CAMPOS DE FUTBOL",
              class_name="text-sm font-semibold tracking-wide text-white",
            ),
            class_name="relative z-10 flex flex-col items-start gap-2",
          ),
          style={
            "backgroundImage": "image-set(url('/campo-futbol.webp') type('image/webp'), url('/campo-futbol.png') type('image/png'))",
            "backgroundSize": "cover",
            "backgroundPosition": "center",
          },
          class_name=rx.cond(
            State.field_rental_sport == "futbol",
            "relative z-10 overflow-hidden flex flex-col items-start gap-1 rounded-[10px] px-4 py-3 text-white min-h-[140px] sm:min-h-[160px] transition-transform duration-300",
            "relative z-10 overflow-hidden flex flex-col items-start gap-1 rounded-[10px] px-4 py-3 text-white border border-white/25 min-h-[140px] sm:min-h-[160px] transition-transform duration-300 group-hover:opacity-95",
          ),
        ),
        on_click=lambda: State.set_field_rental_sport("futbol"),
        class_name=rx.cond(
          State.field_rental_sport == "futbol",
          "group relative overflow-hidden rounded-xl p-[5px] shadow-[0_0_48px_rgba(34,211,238,0.95)] ring-1 ring-white/60 transition-all duration-300",
          "group relative overflow-hidden rounded-xl p-[2px] bg-transparent transition-all duration-300",
        ),
      ),
      rx.el.button(
        rx.cond(
          State.field_rental_sport == "voley",
          rx.fragment(
            rx.el.div(
              class_name="absolute inset-0 rounded-xl bg-[conic-gradient(from_0deg,#22d3ee,#a855f7,#f59e0b,#22d3ee)] opacity-45 blur-[0.5px] animate-[spin_18s_linear_infinite] pointer-events-none",
            ),
            rx.el.div(
              class_name="absolute inset-0 rounded-xl bg-[conic-gradient(from_0deg,transparent_0deg,transparent_30deg,rgba(34,211,238,0.25)_45deg,rgba(34,211,238,0.85)_140deg,rgba(168,85,247,1)_240deg,rgba(245,158,11,1)_320deg,rgba(34,211,238,0.95)_360deg)] blur-[1px] animate-[spin_6s_linear_infinite] pointer-events-none",
            ),
          ),
          rx.fragment(),
        ),
        rx.el.div(
          rx.el.div(
            class_name="absolute inset-0 rounded-[10px] bg-black/45 pointer-events-none",
          ),
          rx.el.div(
            rx.el.img(
              src="/balon-voley.png",
              alt="Balon voley",
              loading="lazy",
              decoding="async",
              class_name="h-6 w-6",
            ),
            rx.el.span(
              "CAMPOS DE VOLEY",
              class_name="text-sm font-semibold tracking-wide text-white",
            ),
            class_name="relative z-10 flex flex-col items-start gap-2",
          ),
          style={
            "backgroundImage": "image-set(url('/campo-voley.webp') type('image/webp'), url('/campo-voley.png') type('image/png'))",
            "backgroundSize": "cover",
            "backgroundPosition": "center",
          },
          class_name=rx.cond(
            State.field_rental_sport == "voley",
            "relative z-10 overflow-hidden flex flex-col items-start gap-1 rounded-[10px] px-4 py-3 text-white min-h-[140px] sm:min-h-[160px] transition-transform duration-300",
            "relative z-10 overflow-hidden flex flex-col items-start gap-1 rounded-[10px] px-4 py-3 text-white border border-white/25 min-h-[140px] sm:min-h-[160px] transition-transform duration-300 group-hover:opacity-95",
          ),
        ),
        on_click=lambda: State.set_field_rental_sport("voley"),
        class_name=rx.cond(
          State.field_rental_sport == "voley",
          "group relative overflow-hidden rounded-xl p-[5px] shadow-[0_0_48px_rgba(34,211,238,0.95)] ring-1 ring-white/60 transition-all duration-300",
          "group relative overflow-hidden rounded-xl p-[2px] bg-transparent transition-all duration-300",
        ),
      ),
      class_name="grid grid-cols-1 sm:grid-cols-2 gap-3",
    ),
    class_name=f"{CARD_STYLES['default']} flex flex-col gap-3",
  )


def time_slot_button(slot: rx.Var[dict]) -> rx.Component:
  return rx.el.button(
    rx.cond(
      (State.field_rental_sport == "futbol") & slot["reserved"],
      rx.el.img(
        src="/balon-futbol.png",
        alt="Reserva futbol",
        loading="lazy",
        decoding="async",
        class_name="absolute right-2 top-2 h-7 w-7 rounded-full bg-white/80 p-1 shadow pointer-events-none",
      ),
      rx.fragment(),
    ),
    rx.cond(
      (State.field_rental_sport == "voley") & slot["reserved"],
      rx.el.img(
        src="/balon-voley.png",
        alt="Reserva voley",
        loading="lazy",
        decoding="async",
        class_name="absolute right-2 top-2 h-7 w-7 rounded-full bg-white/80 p-1 shadow pointer-events-none",
      ),
      rx.fragment(),
    ),
    rx.el.div(
      rx.el.span(
        slot["start"],
        " - ",
        slot["end"],
        class_name="text-sm font-semibold",
      ),
      rx.el.span(
        rx.cond(
          slot["reserved"],
          "Reservado",
          rx.cond(
            slot["selected"],
            "Seleccionado",
            "Seleccionar",
          ),
        ),
        class_name="text-xs opacity-70",
      ),
      class_name="flex flex-col items-start",
    ),
    on_click=lambda _, start=slot["start"], end=slot["end"]: State.toggle_schedule_slot(start, end),
    class_name=rx.cond(
      slot["reserved"],
      "w-full text-left rounded-lg border border-red-200 bg-red-50 text-red-700 px-3 py-2 cursor-not-allowed relative",
      rx.cond(
        slot["selected"],
        "w-full text-left rounded-lg bg-indigo-600 text-white px-3 py-2 shadow relative",
        "w-full text-left rounded-lg border px-3 py-2 hover:bg-slate-50 relative",
      ),
    ),
    disabled=slot["reserved"],
  )


def time_slots_grid() -> rx.Component:
  return rx.el.div(
    rx.foreach(State.schedule_slots, lambda slot: time_slot_button(slot)),
    class_name="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2",
  )


def mini_calendar_day(day: rx.Var[dict]) -> rx.Component:
  base_classes = (
    "h-9 w-9 rounded-full flex items-center justify-center text-sm font-semibold "
    "transition-colors"
  )
  return rx.cond(
    day["is_padding"],
    rx.el.div(class_name="h-9 w-9"),
    rx.el.button(
      day["day"],
      on_click=lambda: State.set_selected_date(day["date_str"]),
      class_name=rx.cond(
        day["is_selected"],
        f"{base_classes} bg-indigo-600 text-white shadow-sm",
        rx.cond(
          day["is_today"],
          f"{base_classes} border border-indigo-600 text-indigo-600",
          f"{base_classes} text-slate-700 hover:bg-slate-100",
        ),
      ),
    ),
  )


def mini_calendar_sidebar() -> rx.Component:
  day_headers = ["L", "M", "M", "J", "V", "S", "D"]
  return rx.el.div(
    rx.el.div(
      rx.el.span(
        State.display_month_label,
        class_name="text-sm font-semibold text-slate-800",
      ),
      rx.el.div(
        rx.el.button(
          rx.icon("chevron-left", class_name="h-4 w-4"),
          on_click=State.prev_month,
          title="Mes anterior",
          aria_label="Mes anterior",
          class_name="p-1 rounded-full text-slate-600 hover:bg-slate-100",
        ),
        rx.el.button(
          rx.icon("chevron-right", class_name="h-4 w-4"),
          on_click=State.next_month,
          title="Mes siguiente",
          aria_label="Mes siguiente",
          class_name="p-1 rounded-full text-slate-600 hover:bg-slate-100",
        ),
        class_name="flex items-center gap-1",
      ),
      class_name="flex items-center justify-between",
    ),
    rx.el.button(
      "Hoy",
      on_click=State.go_to_today,
      class_name=f"{BUTTON_STYLES['secondary']} mt-3 w-full shadow-sm font-semibold",
    ),
    rx.grid(
      *[
        rx.el.span(
          day,
          class_name="text-center text-xs font-semibold text-slate-400",
        )
        for day in day_headers
      ],
      rx.foreach(
        State.calendar_grid,
        lambda week: rx.foreach(week, mini_calendar_day),
      ),
      columns="7",
      class_name="mt-3 gap-2",
    ),
    class_name=CARD_STYLES["default"],
  )


def schedule_controls() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.span(
        "Fecha",
        class_name="text-xs uppercase tracking-wide text-slate-500",
      ),
      rx.el.div(
        rx.icon("calendar", class_name="h-4 w-4 text-slate-500"),
        rx.el.input(
          type="date",
          default_value=State.schedule_selected_date,
          on_change=State.set_selected_date,
          class_name="w-full bg-transparent outline-none",
        ),
        class_name="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm",
      ),
      class_name="flex flex-col gap-2 w-full sm:flex-1",
    ),
    rx.el.button(
      rx.icon("sun", class_name="h-4 w-4"),
      "Hoy",
      on_click=State.go_to_today,
      class_name=f"{BUTTON_STYLES['secondary']} shadow-sm sm:w-32",
    ),
    class_name="flex flex-col sm:flex-row sm:items-end gap-3 rounded-xl border border-slate-200 bg-gradient-to-r from-indigo-50 via-white to-emerald-50 p-4 lg:hidden",
  )


def schedule_planner() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.h2(
          State.selected_date_label,
          class_name="text-2xl sm:text-3xl font-bold text-slate-900",
        ),
        rx.el.span(
          "Planificador horario",
          class_name="text-sm font-semibold text-slate-700",
        ),
        rx.el.p(
          "Selecciona la fecha en el calendario y una franja horaria entre 00:00 y 23:59.",
          class_name="text-sm text-slate-600",
        ),
        class_name="flex flex-col gap-1",
      ),
      schedule_controls(),
      rx.el.div(
        rx.el.div(
          rx.el.h4("Horas del dia", class_name="text-sm font-semibold text-slate-700"),
          rx.el.span(
            "Selecciona bloques consecutivos para reservar.",
            class_name="text-xs text-slate-500",
          ),
          class_name="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1",
        ),
        time_slots_grid(),
        class_name="flex flex-col gap-3",
      ),
      rx.el.div(
        rx.el.div(
          rx.el.span("Seleccion actual", class_name="text-xs uppercase text-slate-500"),
          rx.el.span(
            State.schedule_selected_date,
            " ",
            State.schedule_selection_label,
            class_name="text-sm font-semibold text-slate-900",
          ),
          rx.el.span(
            rx.cond(
              State.schedule_selection_valid,
              "Listo para registrar la reserva en bloque.",
              rx.cond(
                State.schedule_selected_slots_count == 0,
                "Selecciona uno o varios horarios disponibles.",
                "Elige horarios consecutivos para reservar en un solo bloque.",
              ),
            ),
            class_name="text-xs text-slate-600",
          ),
          class_name="flex flex-col gap-1",
        ),
        rx.el.div(
          rx.el.button(
            rx.icon("rotate-ccw", class_name="h-4 w-4"),
            "Limpiar seleccion",
            on_click=State.clear_schedule_selection,
            disabled=rx.cond(State.schedule_selected_slots_count == 0, True, False),
            class_name=rx.cond(
              State.schedule_selected_slots_count == 0,
              f"{BUTTON_STYLES['disabled_sm']} min-h-[38px]",
              f"{BUTTON_STYLES['secondary_sm']} min-h-[38px]",
            ),
          ),
          rx.el.button(
            rx.icon("calendar-plus", class_name="h-4 w-4"),
            "Reservar seleccion",
            on_click=State.open_selected_slots_modal,
            disabled=rx.cond(State.schedule_selection_valid, False, True),
            class_name=rx.cond(
              State.schedule_selection_valid,
              f"{BUTTON_STYLES['primary_sm']} min-h-[38px]",
              f"{BUTTON_STYLES['disabled_sm']} min-h-[38px]",
            ),
          ),
          class_name="flex flex-col sm:flex-row gap-2 sm:items-center",
        ),
        class_name="rounded-lg border border-indigo-100 bg-indigo-50/70 p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3",
      ),
      class_name="p-4 sm:p-6 flex flex-col gap-5",
    ),
    class_name=f"flex-1 min-w-0 {CARD_STYLES['default']} h-fit",
  )
