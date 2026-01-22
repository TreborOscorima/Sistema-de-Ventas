import reflex as rx

from app.state import State
from app.components.ui import BUTTON_STYLES, INPUT_STYLES, empty_state, modal_container, permission_guard


def client_row(client: rx.Var[dict]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(client["name"], class_name="py-3 px-4 font-medium text-gray-900"),
        rx.el.td(client["dni"], class_name="py-3 px-4"),
        rx.el.td(
            rx.cond(
                (client["phone"] == None) | (client["phone"] == ""),
                rx.el.span("-", class_name="text-gray-400"),
                client["phone"],
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            rx.cond(
                (client["address"] == None) | (client["address"] == ""),
                rx.el.span("-", class_name="text-gray-400"),
                client["address"],
            ),
            class_name="py-3 px-4",
        ),
        rx.el.td(
            State.currency_symbol,
            client["credit_available"].to_string(),
            class_name="py-3 px-4 text-right font-semibold text-emerald-700",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda _, c=client: State.open_modal(c),
                    class_name="p-2 text-indigo-600 hover:bg-indigo-50 rounded-full",
                    title="Editar",
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, c_id=client["id"]: State.delete_client(c_id),
                    class_name="p-2 text-red-600 hover:bg-red-50 rounded-full",
                    title="Eliminar",
                ),
                class_name="flex items-center justify-center gap-2",
            ),
            class_name="py-3 px-4 text-center",
        ),
        class_name="border-b hover:bg-gray-50 transition-colors",
    )


def client_form_modal() -> rx.Component:
    return modal_container(
        is_open=State.show_modal,
        on_close=State.close_modal,
        title=rx.cond(
            State.current_client["id"] == None,
            "Nuevo Cliente",
            "Editar Cliente",
        ),
        description="Completa los datos del cliente para ventas a credito.",
        children=[
            rx.el.div(
                rx.el.div(
                    rx.el.label("Nombre", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.current_client["name"],
                        on_change=lambda v: State.update_current_client("name", v),
                        placeholder="Nombre completo",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label(State.personal_id_label, class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.current_client["dni"],
                        on_change=lambda v: State.update_current_client("dni", v),
                        placeholder=State.personal_id_placeholder,
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Telefono", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.current_client["phone"],
                        on_change=lambda v: State.update_current_client("phone", v),
                        placeholder="Numero de contacto",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Direccion", class_name="text-sm font-medium text-gray-700"),
                    rx.el.input(
                        value=State.current_client["address"],
                        on_change=lambda v: State.update_current_client("address", v),
                        placeholder="Direccion del cliente",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Limite de credito", class_name="text-sm font-medium text-gray-700"
                    ),
                    rx.el.input(
                        type="number",
                        step="0.01",
                        min="0",
                        value=State.current_client["credit_limit"],
                        on_change=lambda v: State.update_current_client("credit_limit", v),
                        placeholder="0.00",
                        class_name=INPUT_STYLES["default"],
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
            )
        ],
        footer=rx.el.div(
            rx.el.button(
                "Cancelar",
                on_click=State.close_modal,
                class_name=BUTTON_STYLES["secondary"],
            ),
            rx.el.button(
                rx.icon("save", class_name="h-4 w-4"),
                "Guardar",
                on_click=State.save_client,
                class_name=BUTTON_STYLES["primary"],
            ),
            class_name="flex justify-end gap-3 pt-2",
        ),
        max_width="max-w-2xl",
    )


def clientes_page() -> rx.Component:
    content = rx.fragment(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h1(
                        "Clientes",
                        class_name="text-2xl font-bold text-gray-800",
                    ),
                    rx.el.p(
                        "Administra los clientes y su linea de credito.",
                        class_name="text-sm text-gray-600",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Nuevo Cliente",
                    on_click=lambda: State.open_modal(None),
                    class_name=BUTTON_STYLES["primary"],
                ),
                class_name="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between",
            ),
            rx.el.div(
                rx.el.input(
                    placeholder=rx.cond(
                        State.personal_id_label == "DNI",
                        "Buscar por nombre, DNI o teléfono...",
                        "Buscar por nombre, documento o teléfono..."
                    ),
                    value=State.search_query,
                    on_change=State.set_search_query,
                    class_name=INPUT_STYLES["search"],
                ),
                class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md",
            ),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("Nombre", class_name="py-3 px-4 text-left"),
                            rx.el.th(State.personal_id_label, class_name="py-3 px-4 text-left"),
                            rx.el.th("Teléfono", class_name="py-3 px-4 text-left"),
                            rx.el.th("Direccion", class_name="py-3 px-4 text-left"),
                            rx.el.th(
                                "Credito Disp.",
                                class_name="py-3 px-4 text-right",
                            ),
                            rx.el.th(
                                "Acciones",
                                class_name="py-3 px-4 text-center",
                            ),
                            class_name="bg-gray-100",
                        )
                    ),
                    rx.el.tbody(rx.foreach(State.clients_view, client_row)),
                    class_name="min-w-full text-sm",
                ),
                rx.cond(
                    State.clients_view.length() == 0,
                    empty_state("No hay clientes registrados."),
                    rx.fragment(),
                ),
                class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto flex flex-col gap-4",
            ),
            class_name="flex flex-col gap-6 p-4 sm:p-6 w-full max-w-7xl mx-auto",
        ),
        client_form_modal(),
        on_mount=State.load_clients,
    )
    return permission_guard(
        has_permission=State.can_view_clientes,
        content=content,
        redirect_message="Acceso denegado a Clientes",
    )
