import reflex as rx
from app.state import State
from app.components.ui import toggle_switch, page_title, permission_guard

CONFIG_SECTIONS: list[dict[str, str]] = [
    {
        "key": "empresa",
        "label": "Datos de Empresa",
        "description": "Informacion fiscal y de contacto",
        "icon": "building",
    },
    {
        "key": "usuarios",
        "label": "Gestion de Usuarios",
        "description": "Roles, accesos y credenciales",
        "icon": "users",
    },
    {
        "key": "monedas",
        "label": "Selector de Monedas",
        "description": "Moneda activa y lista disponible",
        "icon": "coins",
    },
    {
        "key": "unidades",
        "label": "Unidades de Medida",
        "description": "Unidades visibles en inventario y ventas",
        "icon": "ruler",
    },
    {
        "key": "pagos",
        "label": "Metodos de Pago",
        "description": "Botones y opciones que veras en Venta",
        "icon": "credit-card",
    },
]

PAYMENT_KIND_LABELS: dict[str, str] = {
    "cash": "Efectivo",
    "debit": "Tarjeta de Débito",
    "credit": "Tarjeta de Crédito",
    "yape": "Billetera Digital (Yape)",
    "plin": "Billetera Digital (Plin)",
    "transfer": "Transferencia Bancaria",
    "mixed": "Pago Mixto",
    "other": "Otro",
    "card": "Tarjeta de Crédito",
    "wallet": "Billetera Digital (Yape)",
}

PRIVILEGE_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Ingresos",
        [
            ("Ver Ingresos", "view_ingresos"),
            ("Crear Ingresos", "create_ingresos"),
        ],
    ),
    (
        "Ventas y Caja",
        [
            ("Ver Ventas", "view_ventas"),
            ("Crear Ventas", "create_ventas"),
            ("Ver Gestion de Caja", "view_cashbox"),
            ("Abrir/Cerrar Caja", "manage_cashbox"),
            ("Eliminar Ventas", "delete_sales"),
        ],
    ),
    (
        "Inventario",
        [
            ("Ver Inventario", "view_inventario"),
            ("Editar Inventario", "edit_inventario"),
        ],
    ),
    (
        "Historial y Reportes",
        [
            ("Ver Historial", "view_historial"),
            ("Exportar Datos", "export_data"),
        ],
    ),
    (
        "Servicios",
        [
            ("Ver Servicios", "view_servicios"),
            ("Gestionar Reservas", "manage_reservations"),
        ],
    ),
    (
        "Clientes y Cuentas",
        [
            ("Ver Clientes", "view_clientes"),
            ("Gestionar Clientes", "manage_clientes"),
            ("Ver Cuentas Ctes.", "view_cuentas"),
            ("Gestionar Deudas", "manage_cuentas"),
        ],
    ),
    (
        "Administracion",
        [
            ("Gestionar Usuarios", "manage_users"),
            ("Configuracion Global", "manage_config"),
        ],
    ),
]

PRIVILEGE_LABELS: list[tuple[str, str]] = [
    (label, key) for _, items in PRIVILEGE_SECTIONS for label, key in items
]


def privilege_switch(label: str, privilege: str) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="font-medium text-gray-700"),
        rx.el.div(
            toggle_switch(
                checked=State.new_user_data["privileges"][privilege],
                on_change=lambda value: State.toggle_privilege(privilege),
            ),
        ),
        class_name="flex items-center justify-between bg-gray-50 p-3 rounded-lg",
    )


def privilege_section(title: str, privileges: list[tuple[str, str]]) -> rx.Component:
    return rx.el.div(
        rx.el.p(title, class_name="text-sm font-semibold text-gray-600"),
        rx.el.div(
            *[privilege_switch(label, key) for label, key in privileges],
            class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
        ),
        class_name="p-3 rounded-lg bg-gray-50 space-y-2 border border-gray-100",
    )


def privilege_badges(user: rx.Var[dict]) -> rx.Component:
    return rx.el.div(
        *[
            rx.cond(
                user["privileges"][key],
                rx.el.span(
                    label,
                    class_name="px-2 py-1 text-xs font-semibold rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                ),
                rx.fragment(),
            )
            for label, key in PRIVILEGE_LABELS
        ],
        class_name="flex flex-wrap gap-2 max-w-xl",
    )


def config_nav() -> rx.Component:
    return rx.el.div(
        rx.el.p(
            "Submenus de configuracion",
            class_name="text-sm font-semibold text-gray-700",
        ),
        rx.el.div(
            *[
                rx.el.button(
                    rx.el.div(
                        rx.icon(section["icon"], class_name="h-5 w-5"),
                        rx.el.div(
                            rx.el.span(section["label"], class_name="font-semibold"),
                            rx.el.span(
                                section["description"],
                                class_name="text-xs text-gray-500",
                            ),
                            class_name="flex flex-col items-start",
                        ),
                        class_name="flex items-center gap-3",
                    ),
                    on_click=lambda _, key=section["key"]: State.set_config_active_tab(key),
                    class_name=rx.cond(
                        State.config_active_tab == section["key"],
                        "w-full text-left bg-indigo-100 text-indigo-700 border border-indigo-200 px-3 py-2 rounded-lg shadow-sm",
                        "w-full text-left bg-white text-gray-700 border px-3 py-2 rounded-lg hover:bg-gray-50",
                    ),
                )
                for section in CONFIG_SECTIONS
            ],
            class_name="flex flex-col gap-2",
        ),
        class_name="bg-white rounded-lg shadow-sm border p-4 space-y-3",
    )


def company_settings_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Datos de mi Empresa", class_name="text-xl font-semibold text-gray-700"
            ),
            rx.el.p(
                "Actualiza la informacion que aparece en recibos y reportes.",
                class_name="text-sm text-gray-500",
            ),
            class_name="space-y-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.label(
                        "Razón Social / Nombre", class_name="text-sm font-medium"
                    ),
                    rx.el.input(
                        default_value=State.company_name,
                        on_change=State.set_company_name,
                        placeholder="Ej: Tu Empresa SAC",
                        key=State.company_form_key.to_string() + "-company_name",
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label(State.tax_id_label, class_name="text-sm font-medium"),
                    rx.el.input(
                        default_value=State.ruc,
                        on_change=State.set_ruc,
                        placeholder=State.tax_id_placeholder,
                        key=State.company_form_key.to_string() + "-ruc",
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label("Dirección Fiscal", class_name="text-sm font-medium"),
                    rx.el.input(
                        default_value=State.address,
                        on_change=State.set_address,
                        placeholder="Ej: Av. Principal 123",
                        key=State.company_form_key.to_string() + "-address",
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1 md:col-span-2",
                ),
                rx.el.div(
                    rx.el.label("Teléfono / Celular", class_name="text-sm font-medium"),
                    rx.el.input(
                        default_value=State.phone,
                        on_change=State.set_phone,
                        placeholder="Ej: 999 999 999",
                        key=State.company_form_key.to_string() + "-phone",
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Mensaje en Recibo/Ticket", class_name="text-sm font-medium"
                    ),
                    rx.el.input(
                        default_value=State.footer_message,
                        on_change=State.set_footer_message,
                        placeholder="Ej: Gracias por su compra",
                        key=State.company_form_key.to_string() + "-footer_message",
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1 md:col-span-2",
                ),
                rx.el.div(
                    rx.el.label("Papel de Impresion", class_name="text-sm font-medium"),
                    rx.el.select(
                        rx.el.option("80 mm (default)", value="80"),
                        rx.el.option("58 mm", value="58"),
                        value=State.receipt_paper,
                        on_change=State.set_receipt_paper,
                        class_name="w-full p-2 border rounded-md",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                rx.el.div(
                    rx.el.label(
                        "Ancho de Recibo (opcional)", class_name="text-sm font-medium"
                    ),
                    rx.el.input(
                        default_value=State.receipt_width,
                        on_change=State.set_receipt_width,
                        placeholder="Ej: 42",
                        type_="number",
                        min="24",
                        max="64",
                        key=State.company_form_key.to_string() + "-receipt_width",
                        class_name="w-full p-2 border rounded-md",
                    ),
                    rx.el.p(
                        "Deja en blanco para usar el ancho automatico.",
                        class_name="text-xs text-gray-500",
                    ),
                    class_name="flex flex-col gap-1",
                ),
                class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            rx.el.div(
                rx.el.p(
                    "Estos datos se muestran en recibos y reportes.",
                    class_name="text-xs text-gray-500",
                ),
                rx.el.div(
                    rx.el.button(
                        "Guardar Configuracion",
                        on_click=State.save_settings,
                        class_name="w-full sm:w-auto bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 min-h-[44px]",
                    ),
                    class_name="flex justify-end sm:justify-start",
                ),
                class_name="flex flex-col sm:flex-row sm:items-center justify-between gap-3",
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md border border-gray-100 space-y-4",
        ),
        class_name="space-y-4",
    )


def user_form() -> rx.Component:
    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.trigger(
            rx.el.button(
                "Crear Nuevo Usuario",
                on_click=State.show_create_user_form,
                class_name="w-full sm:w-auto bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 font-semibold mb-6 text-center min-h-[44px]",
            )
        ),
        rx.radix.primitives.dialog.portal(
            rx.radix.primitives.dialog.overlay(
                class_name="fixed inset-0 bg-black/40 modal-overlay"
            ),
            rx.radix.primitives.dialog.content(
                rx.radix.primitives.dialog.title(
                    rx.cond(State.editing_user, "Editar Usuario", "Crear Nuevo Usuario"),
                    class_name="text-xl font-semibold text-gray-800 pb-2 border-b border-gray-100 flex-shrink-0",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Nombre de Usuario", class_name="font-medium"),
                        rx.el.input(
                            value=State.new_user_data["username"],
                            on_change=lambda v: State.handle_new_user_change(
                                "username", v
                            ),
                            is_disabled=rx.cond(State.editing_user, True, False),
                            class_name="w-full p-2 border rounded-md mt-1",
                        ),
                        class_name="mb-4",
                    ),
                    rx.el.div(
                        rx.el.label("Rol", class_name="font-medium"),
                        rx.el.select(
                            rx.foreach(
                                State.roles,
                                lambda role: rx.el.option(role, value=role),
                            ),
                            value=State.new_user_data["role"],
                            on_change=lambda v: State.handle_new_user_change("role", v),
                            class_name="w-full p-2 border rounded-md mt-1",
                        ),
                        rx.el.p(
                            "Los privilegios se cargan de acuerdo al rol seleccionado. Puedes afinar y guardar nuevos roles debajo.",
                            class_name="text-sm text-gray-500 mt-2",
                        ),
                        class_name="mb-4",
                    ),
                    rx.el.div(
                        rx.el.label("Crear nuevo rol", class_name="font-medium"),
                        rx.el.div(
                            rx.el.input(
                                placeholder="Ej: Administrador, Cajero, Auditor",
                                value=State.new_role_name,
                                on_change=State.update_new_role_name,
                                class_name="flex-1 p-2 border rounded-md",
                            ),
                            rx.el.button(
                                "Crear rol con estos privilegios",
                                on_click=State.create_role_from_current_privileges,
                                class_name="bg-indigo-600 text-white px-3 py-2 rounded-md hover:bg-indigo-700",
                            ),
                            class_name="flex flex-col sm:flex-row sm:items-center gap-3 mt-2",
                        ),
                        class_name="mb-4",
                    ),
                    rx.el.div(
                        rx.el.label("Contraseña", class_name="font-medium"),
                        rx.el.input(
                            type="password",
                            placeholder=rx.cond(
                                State.editing_user,
                                "Dejar en blanco para no cambiar",
                                "",
                            ),
                            value=State.new_user_data["password"],
                            on_change=lambda v: State.handle_new_user_change(
                                "password", v
                            ),
                            class_name="w-full p-2 border rounded-md mt-1",
                        ),
                        class_name="mb-4",
                    ),
                    rx.el.div(
                        rx.el.label("Confirmar Contraseña", class_name="font-medium"),
                        rx.el.input(
                            type="password",
                            value=State.new_user_data["confirm_password"],
                            on_change=lambda v: State.handle_new_user_change(
                                "confirm_password", v
                            ),
                            class_name="w-full p-2 border rounded-md mt-1",
                        ),
                        class_name="mb-4",
                    ),
                    rx.el.div(
                        rx.el.div(
                            rx.el.h3(
                                "Privilegios", class_name="text-lg font-semibold"
                            ),
                            rx.el.p(
                                "Asigna los accesos para el rol elegido. Si necesitas volver a los permisos sugeridos del rol, usa el boton.",
                                class_name="text-sm text-gray-500",
                            ),
                            class_name="flex flex-col gap-1",
                        ),
                        rx.el.div(
                            rx.el.button(
                                "Restaurar privilegios del rol",
                                on_click=State.apply_role_privileges,
                                class_name="text-sm text-indigo-700 border border-indigo-200 px-3 py-1 rounded-md hover:bg-indigo-50 min-h-[38px]",
                            ),
                            rx.el.button(
                                "Guardar como plantilla de rol",
                                on_click=State.save_role_template,
                                class_name="text-sm text-green-700 border border-green-200 px-3 py-1 rounded-md hover:bg-green-50 min-h-[38px]",
                            ),
                            class_name="flex flex-col sm:flex-row sm:items-center gap-2",
                        ),
                        class_name="flex flex-wrap justify-between items-start gap-3 mt-4 mb-2",
                    ),
                    rx.el.div(
                        *[
                            privilege_section(title, items)
                            for title, items in PRIVILEGE_SECTIONS
                        ],
                        class_name="space-y-3",
                    ),
                    class_name="flex-1 overflow-y-auto min-h-0 p-1 scroll-smooth",
                    style={"scroll-behavior": "auto"},
                    id="user-form-content",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.hide_user_form,
                        class_name="w-full sm:w-auto bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300 min-h-[44px]",
                    ),
                    rx.el.button(
                        "Guardar",
                        on_click=State.save_user,
                        class_name="w-full sm:w-auto bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 min-h-[44px]",
                    ),
                    class_name="flex flex-col sm:flex-row justify-end items-stretch sm:items-center gap-3 sm:gap-4 flex-shrink-0 pt-3 border-t border-gray-100",
                ),
                class_name="fixed left-1/2 top-1/2 w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-5 sm:p-6 shadow-xl focus:outline-none max-h-[90vh] flex flex-col gap-4",
            ),
        ),
        open=State.show_user_form,
        on_open_change=State.set_user_form_open,
    )



def user_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Gestion de Usuarios", class_name="text-xl font-semibold text-gray-700"
                ),
                rx.el.p(
                    "Crea usuarios, roles y ajusta sus privilegios.",
                    class_name="text-sm text-gray-500",
                ),
                class_name="flex flex-col",
            ),
            user_form(),
            class_name="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-2",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Usuario", class_name="py-3 px-4 text-left"),
                        rx.el.th("Rol", class_name="py-3 px-4 text-left"),
                        rx.el.th("Privilegios", class_name="py-3 px-4 text-left"),
                        rx.el.th("Acciones", class_name="py-3 px-4 text-center"),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.users_list,
                        lambda user: rx.el.tr(
                            rx.el.td(user["username"], class_name="py-3 px-4"),
                            rx.el.td(user["role"], class_name="py-3 px-4"),
                            rx.el.td(
                                privilege_badges(user),
                                class_name="py-3 px-4",
                            ),
                            rx.el.td(
                                rx.el.div(
                                    rx.el.button(
                                        rx.icon("pencil", class_name="h-4 w-4"),
                                        on_click=lambda _,
                                        username=user["username"]: State.show_edit_user_form_by_username(
                                            username
                                        ),
                                        class_name="p-2 text-blue-500 hover:bg-blue-100 rounded-full",
                                    ),
                                    rx.el.button(
                                        rx.icon("trash-2", class_name="h-4 w-4"),
                                        on_click=lambda _,
                                        username=user["username"]: State.delete_user(
                                            username
                                        ),
                                        class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                                    ),
                                    class_name="flex justify-center gap-2",
                                )
                            ),
                            class_name="border-b",
                            key=user["username"],
                        ),
                    )
                ),
            ),
            class_name="bg-white p-4 sm:p-6 rounded-lg shadow-md overflow-x-auto",
        ),
        class_name="space-y-4",
    )


def currency_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Selector de Monedas", class_name="text-xl font-semibold text-gray-700"
            ),
            rx.el.p(
                "Configura las monedas disponibles y el simbolo que se muestra en los modulos.",
                class_name="text-sm text-gray-500",
            ),
            class_name="space-y-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label("Codigo", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.new_currency_code,
                    on_change=State.set_new_currency_code,
                    placeholder="PEN, USD, EUR",
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Nombre", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.new_currency_name,
                    on_change=State.set_new_currency_name,
                    placeholder="Sol peruano, Dolar, Peso",
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Simbolo", class_name="text-sm font-medium text-gray-700"),
                rx.el.input(
                    value=State.new_currency_symbol,
                    on_change=State.set_new_currency_symbol,
                    placeholder="S/, $, EUR",
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            class_name="grid grid-cols-1 md:grid-cols-3 gap-3 bg-white p-4 rounded-lg shadow-sm border",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Agregar moneda",
                    on_click=State.add_currency,
                    class_name="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 flex items-center justify-center gap-2 min-h-[44px]",
                ),
                class_name="flex items-center gap-3",
            ),
            rx.el.div(
                rx.el.span("Moneda activa:", class_name="text-sm text-gray-600"),
                rx.el.span(
                    State.currency_name,
                    class_name="text-sm font-semibold text-indigo-700",
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border rounded-lg p-4 shadow-sm",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Codigo", class_name="py-2 px-4 text-left"),
                        rx.el.th("Nombre", class_name="py-2 px-4 text-left"),
                        rx.el.th("Simbolo", class_name="py-2 px-4 text-left"),
                        rx.el.th("Acciones", class_name="py-2 px-4 text-right"),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.available_currencies,
                        lambda currency: rx.el.tr(
                            rx.el.td(currency["code"], class_name="py-2 px-4 font-semibold"),
                            rx.el.td(currency["name"], class_name="py-2 px-4"),
                            rx.el.td(currency["symbol"], class_name="py-2 px-4"),
                            rx.el.td(
                                rx.el.div(
                                    rx.el.button(
                                        "Seleccionar",
                                        on_click=lambda _,
                                        code=currency["code"]: State.set_currency(code),
                                        class_name="px-3 py-1 rounded-md border text-sm hover:bg-gray-50",
                                    ),
                                    rx.el.button(
                                        rx.icon("trash-2", class_name="h-4 w-4"),
                                        on_click=lambda _,
                                        code=currency["code"]: State.remove_currency(code),
                                        class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                                    ),
                                    class_name="flex items-center justify-end gap-2",
                                ),
                                class_name="py-2 px-4 text-right",
                            ),
                            class_name=rx.cond(
                                State.selected_currency_code == currency["code"],
                                "bg-indigo-50",
                                "bg-white",
                            ),
                            key=currency["code"],
                        ),
                    )
                ),
            ),
            class_name="bg-white p-4 rounded-lg shadow-md overflow-x-auto",
        ),
        class_name="space-y-4",
    )


def unit_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Unidades de Medida", class_name="text-xl font-semibold text-gray-700"
            ),
            rx.el.p(
                "Define las unidades que podras seleccionar en inventario, ingresos y ventas.",
                class_name="text-sm text-gray-500",
            ),
            class_name="space-y-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label("Nombre de la unidad", class_name="text-sm font-medium"),
                rx.el.input(
                    placeholder="Ej: Caja, Paquete, Docena",
                    value=State.new_unit_name,
                    on_change=State.set_new_unit_name,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Permite decimales", class_name="text-sm font-medium"),
                toggle_switch(
                    checked=State.new_unit_allows_decimal,
                    on_change=State.set_new_unit_allows_decimal,
                ),
                class_name="flex items-center gap-2 mt-1",
            ),
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar unidad",
                on_click=State.add_unit,
                class_name="w-full md:w-auto bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 flex items-center justify-center gap-2 min-h-[44px]",
            ),
            class_name="grid grid-cols-1 md:grid-cols-3 gap-2 bg-white p-3 rounded-lg shadow-sm border items-end",
        ),
        rx.el.div(
            rx.foreach(
                State.unit_rows,
                lambda unit: rx.el.div(
                    rx.el.div(
                        rx.el.div(
                            rx.el.span(
                                unit["name"],
                                class_name="text-sm font-semibold text-gray-900",
                            ),
                            rx.cond(
                                unit["allows_decimal"],
                                rx.el.span(
                                    "Si",
                                    class_name="px-2 py-0.5 text-[10px] rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                                ),
                                rx.el.span(
                                    "No",
                                    class_name="px-2 py-0.5 text-[10px] rounded-md bg-gray-100 text-gray-600 border border-gray-200",
                                ),
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        rx.el.div(
                            rx.el.span(
                                "Decimales",
                                class_name="text-[10px] text-gray-500 hidden sm:inline",
                            ),
                            toggle_switch(
                                checked=unit["allows_decimal"].bool(),
                                on_change=lambda value,
                                name=unit["name"]: State.set_unit_decimal(
                                    name, value
                                ),
                            ),
                            rx.el.button(
                                rx.icon("trash-2", class_name="h-4 w-4"),
                                on_click=lambda _,
                                name=unit["name"]: State.remove_unit(name),
                                is_disabled=rx.cond(
                                    unit["name"] == "Unidad", True, False
                                ),
                                class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        class_name="flex items-center justify-between gap-2",
                    ),
                    class_name="border border-gray-200 rounded-md p-2 shadow-sm",
                ),
            ),
            class_name="bg-white p-2 sm:p-3 rounded-lg shadow-md grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2",
        ),
        class_name="space-y-3",
    )


def payment_methods_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Metodos de Pago", class_name="text-xl font-semibold text-gray-700"
            ),
            rx.el.p(
                "Activa, crea o elimina los botones que veras en el modulo de Venta.",
                class_name="text-sm text-gray-500",
            ),
            class_name="space-y-1",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label("Nombre", class_name="text-sm font-medium"),
                rx.el.input(
                    placeholder="Ej: Transferencia, Deposito",
                    value=State.new_payment_method_name,
                    on_change=State.set_new_payment_method_name,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Descripcion", class_name="text-sm font-medium"),
                rx.el.input(
                    placeholder="Breve detalle del metodo",
                    value=State.new_payment_method_description,
                    on_change=State.set_new_payment_method_description,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.div(
                rx.el.label("Tipo", class_name="text-sm font-medium"),
                rx.el.select(
                    *[
                        rx.el.option(PAYMENT_KIND_LABELS[kind], value=kind)
                        for kind in [
                            "cash",
                            "debit",
                            "credit",
                            "yape",
                            "plin",
                            "transfer",
                            "mixed",
                            "other",
                        ]
                    ],
                    value=State.new_payment_method_kind,
                    on_change=State.set_new_payment_method_kind,
                    class_name="w-full p-2 border rounded-md",
                ),
                class_name="flex flex-col gap-1",
            ),
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar metodo",
                on_click=State.add_payment_method,
                class_name="w-full md:w-auto bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 flex items-center justify-center gap-2 min-h-[44px]",
            ),
            class_name="grid grid-cols-1 md:grid-cols-4 gap-3 bg-white p-4 rounded-lg shadow-sm border items-end",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Metodo", class_name="py-2 px-3 text-left"),
                        rx.el.th("Tipo", class_name="py-2 px-3 text-left"),
                        rx.el.th("Estado", class_name="py-2 px-3 text-left"),
                        rx.el.th("Acciones", class_name="py-2 px-3 text-right"),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.payment_methods,
                        lambda method: rx.el.tr(
                            rx.el.td(
                                rx.el.div(
                                    rx.el.span(method["name"], class_name="font-semibold"),
                                    rx.cond(
                                        State.payment_method == method["name"],
                                        rx.el.span(
                                            "En uso",
                                            class_name="text-xs px-2 py-1 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100",
                                        ),
                                        rx.fragment(),
                                    ),
                                    class_name="flex items-center gap-2",
                                ),
                                class_name="py-2 px-3",
                            ),
                            rx.el.td(
                                PAYMENT_KIND_LABELS.get(method["kind"], "Otro"),
                                class_name="py-2 px-3",
                            ),
                            rx.el.td(
                                rx.el.span(
                                    rx.cond(
                                        method["enabled"],
                                        "Activo",
                                        "Inactivo",
                                    ),
                                    class_name="text-sm font-medium",
                                ),
                                class_name="py-2 px-3",
                            ),
                            rx.el.td(
                                rx.el.div(
                                    rx.el.div(
                                        rx.el.label(
                                            "Visible en Venta",
                                            class_name="text-xs text-gray-500",
                                        ),
                                        toggle_switch(
                                            checked=method["enabled"],
                                            on_change=lambda value,
                                            mid=method["id"]: State.toggle_payment_method_enabled(
                                                mid, value
                                            ),
                                        ),
                                        class_name="flex items-center gap-2",
                                    ),
                                    rx.el.button(
                                        rx.icon("trash-2", class_name="h-4 w-4"),
                                        on_click=lambda _,
                                        mid=method["id"]: State.remove_payment_method(mid),
                                        class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                                    ),
                                    class_name="flex items-center justify-end gap-3",
                                ),
                                class_name="py-2 px-3 text-right",
                            ),
                            key=method["id"],
                            class_name="border-b",
                        ),
                    )
                ),
            ),
            class_name="bg-white p-4 rounded-lg shadow-md overflow-x-auto",
        ),
        class_name="space-y-4",
    )


def field_prices_section() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2(
                "Precios de Campo", class_name="text-xl font-semibold text-gray-700"
            ),
            rx.el.p(
                "Configura los precios por deporte y modalidad (Futbol, Voley).",
                class_name="text-sm text-gray-500",
            ),
            class_name="space-y-1",
        ),
        rx.el.div(
            rx.el.input(
                placeholder="Deporte (ej: Futbol, Voley)",
                value=State.new_field_price_sport,
                on_change=State.set_new_field_price_sport,
                class_name="p-2 border rounded-md",
            ),
            rx.el.input(
                placeholder="Nombre del campo (ej: Futbol 5)",
                value=State.new_field_price_name,
                on_change=State.set_new_field_price_name,
                class_name="p-2 border rounded-md",
            ),
            rx.el.input(
                type="number",
                step="0.01",
                placeholder="Precio por hora",
                value=State.new_field_price_amount,
                on_change=State.set_new_field_price_amount,
                class_name="p-2 border rounded-md",
            ),
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Agregar",
                on_click=State.add_field_price,
                class_name="flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 min-h-[44px]",
            ),
            rx.el.button(
                rx.icon("refresh-ccw", class_name="h-4 w-4"),
                "Actualizar",
                on_click=State.update_field_price,
                is_disabled=rx.cond(State.editing_field_price_id == "", True, False),
                class_name=rx.cond(
                    State.editing_field_price_id == "",
                    "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-gray-200 text-gray-500 cursor-not-allowed min-h-[44px]",
                    "flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-amber-500 text-white hover:bg-amber-600 min-h-[44px]",
                ),
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr,2fr,1fr,auto,auto] gap-3 items-center bg-white p-4 rounded-lg shadow-sm border",
        ),
        rx.cond(
            State.editing_field_price_id != "",
            rx.el.div(
                "Editando un precio existente. Ajusta los campos y presiona Actualizar.",
                class_name="text-sm text-amber-700 bg-amber-50 border border-amber-100 px-3 py-2 rounded-md",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Deporte", class_name="py-2 px-3 text-left"),
                        rx.el.th("Campo", class_name="py-2 px-3 text-left"),
                        rx.el.th("Precio (por hora)", class_name="py-2 px-3 text-left"),
                        rx.el.th("Acciones", class_name="py-2 px-3 text-center"),
                        class_name="bg-gray-100",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        State.field_prices,
                        lambda price: rx.el.tr(
                            rx.el.td(
                                price["sport"],
                                class_name="py-2 px-3",
                            ),
                            rx.el.td(price["name"], class_name="py-2 px-3"),
                            rx.el.td(
                                rx.el.input(
                                    type="number",
                                    step="0.01",
                                    value=price["price"].to_string(),
                                    on_change=lambda value, pid=price["id"]: State.update_field_price_amount(
                                        pid, value
                                    ),
                                    class_name="w-full sm:w-32 p-2 border rounded-md",
                                ),
                                class_name="py-2 px-3",
                            ),
                            rx.el.td(
                                rx.el.button(
                                    rx.icon("pencil", class_name="h-4 w-4"),
                                    on_click=lambda _, pid=price["id"]: State.edit_field_price(pid),
                                    class_name="p-2 text-indigo-500 hover:bg-indigo-100 rounded-full",
                                ),
                                rx.el.button(
                                    rx.icon("trash-2", class_name="h-4 w-4"),
                                    on_click=lambda _, pid=price["id"]: State.remove_field_price(
                                        pid
                                    ),
                                    class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                                ),
                                class_name="py-2 px-3 text-center flex items-center justify-center gap-2",
                            ),
                            class_name="border-b",
                        ),
                    )
                ),
                class_name="min-w-full",
            ),
            class_name="bg-white p-4 rounded-lg shadow-md overflow-x-auto",
        ),
        class_name="space-y-4",
    )


def configuracion_page() -> rx.Component:
    content = rx.fragment(
        rx.el.div(
            page_title(
                "Configuracion del Sistema",
                "Gestiona usuarios, monedas, unidades, metodos de pago y precios de campo desde un solo lugar.",
            ),
            rx.el.div(
                    rx.match(
                        State.config_active_tab,
                        ("empresa", company_settings_section()),
                        ("usuarios", user_section()),
                        ("monedas", currency_section()),
                        ("unidades", unit_section()),
                        ("pagos", payment_methods_section()),
                        ("precios_campo", field_prices_section()),
                        user_section(),
                    ),
                    class_name="space-y-4",
                ),
            class_name="p-4 sm:p-6 pb-4 w-full max-w-6xl mx-auto flex flex-col gap-5",
        ),
        on_mount=State.load_settings,
    )
    return permission_guard(
        has_permission=State.is_admin,
        content=content,
        redirect_message="Acceso denegado a Configuración",
    )
