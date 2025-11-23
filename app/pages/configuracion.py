import reflex as rx
from app.state import State

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
    ("Administracion", [("Gestionar Usuarios", "manage_users")]),
]

PRIVILEGE_LABELS: list[tuple[str, str]] = [
    (label, key) for _, items in PRIVILEGE_SECTIONS for label, key in items
]


def privilege_switch(label: str, privilege: str) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, class_name="font-medium text-gray-700"),
        rx.el.div(
            rx.el.button(
                rx.el.span(
                    class_name=rx.cond(
                        State.new_user_data["privileges"][privilege],
                        "translate-x-5",
                        "translate-x-0",
                    )
                    + " pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out"
                ),
                on_click=lambda: State.toggle_privilege(privilege),
                class_name=rx.cond(
                    State.new_user_data["privileges"][privilege],
                    "bg-indigo-600",
                    "bg-gray-200",
                )
                + " relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2",
            )
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


def user_form() -> rx.Component:
    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.trigger(
            rx.el.button(
                "Crear Nuevo Usuario",
                on_click=State.show_create_user_form,
                class_name="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 font-semibold mb-6",
            )
        ),
        rx.radix.primitives.dialog.portal(
            rx.radix.primitives.dialog.overlay(
                class_name="fixed inset-0 bg-black/40"
            ),
            rx.radix.primitives.dialog.content(
                rx.radix.primitives.dialog.title(
                    rx.cond(State.editing_user, "Editar Usuario", "Crear Nuevo Usuario")
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
                            class_name="flex items-center gap-3 mt-2",
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
                                class_name="text-sm text-indigo-700 border border-indigo-200 px-3 py-1 rounded-md hover:bg-indigo-50",
                            ),
                            rx.el.button(
                                "Guardar como plantilla de rol",
                                on_click=State.save_role_template,
                                class_name="text-sm text-green-700 border border-green-200 px-3 py-1 rounded-md hover:bg-green-50",
                            ),
                            class_name="flex items-center gap-2",
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
                    class_name="max-h-[60vh] overflow-y-auto p-1",
                ),
                rx.el.div(
                    rx.el.button(
                        "Cancelar",
                        on_click=State.hide_user_form,
                        class_name="bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300",
                    ),
                    rx.el.button(
                        "Guardar",
                        on_click=State.save_user,
                        class_name="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700",
                    ),
                    class_name="flex justify-end gap-4 mt-6",
                ),
                class_name="fixed left-1/2 top-1/2 w-full max-w-3xl -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl focus:outline-none",
            ),
        ),
        open=State.show_user_form,
        on_open_change=State.set_user_form_open,
    )


def configuracion_page() -> rx.Component:
    return rx.cond(
        State.current_user["privileges"]["manage_users"],
        rx.el.div(
            rx.el.h1(
                "Configuración del Sistema",
                class_name="text-2xl font-bold text-gray-800 mb-6",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.h2(
                        "Gestión de Usuarios",
                        class_name="text-xl font-semibold text-gray-700",
                    ),
                    user_form(),
                    class_name="flex justify-between items-center mb-4",
                ),
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                        rx.el.th("Usuario", class_name="py-3 px-4 text-left"),
                        rx.el.th("Rol", class_name="py-3 px-4 text-left"),
                        rx.el.th("Privilegios", class_name="py-3 px-4 text-left"),
                        rx.el.th(
                            "Acciones", class_name="py-3 px-4 text-center"
                                ),
                                class_name="bg-gray-100",
                            )
                        ),
                        rx.el.tbody(
                                rx.foreach(
                                    State.user_list,
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
                                                rx.icon(
                                                    "trash-2", class_name="h-4 w-4"
                                                ),
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
                    class_name="bg-white p-6 rounded-lg shadow-md overflow-x-auto",
                ),
                class_name="w-full",
            ),
            class_name="p-6",
        ),
        rx.el.div(
            rx.el.h1("Acceso Denegado", class_name="text-2xl font-bold text-red-600"),
            rx.el.p(
                "No tienes los privilegios necesarios para acceder a esta sección.",
                class_name="text-gray-600 mt-2",
            ),
            class_name="flex flex-col items-center justify-center h-full p-6",
        ),
    )
