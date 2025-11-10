import reflex as rx
from app.state import State


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


def user_form() -> rx.Component:
    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.trigger(
            rx.el.button(
                "Crear Nuevo Usuario",
                on_click=State.show_create_user_form,
                class_name="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 font-semibold mb-6",
            )
        ),
        rx.cond(
            State.show_user_form,
            rx.radix.primitives.dialog.content(
                rx.radix.primitives.dialog.title(
                    rx.cond(State.editing_user, "Editar Usuario", "Crear Nuevo Usuario")
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.label("Nombre de Usuario", class_name="font-medium"),
                        rx.el.input(
                            default_value=State.new_user_data["username"],
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
                            rx.el.option("Usuario", value="Usuario"),
                            rx.el.option("Superadmin", value="Superadmin"),
                            value=State.new_user_data["role"],
                            on_change=lambda v: State.handle_new_user_change("role", v),
                            class_name="w-full p-2 border rounded-md mt-1",
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
                            on_change=lambda v: State.handle_new_user_change(
                                "confirm_password", v
                            ),
                            class_name="w-full p-2 border rounded-md mt-1",
                        ),
                        class_name="mb-4",
                    ),
                    rx.el.h3(
                        "Privilegios", class_name="text-lg font-semibold mb-2 mt-4"
                    ),
                    rx.el.div(
                        privilege_switch("Ver Ingresos", "view_ingresos"),
                        privilege_switch("Crear Ingresos", "create_ingresos"),
                        privilege_switch("Ver Ventas", "view_ventas"),
                        privilege_switch("Crear Ventas", "create_ventas"),
                        privilege_switch("Ver Inventario", "view_inventario"),
                        privilege_switch("Editar Inventario", "edit_inventario"),
                        privilege_switch("Ver Historial", "view_historial"),
                        privilege_switch("Exportar Datos", "export_data"),
                        privilege_switch("Gestionar Usuarios", "manage_users"),
                        class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
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
            ),
            rx.fragment(),
        ),
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
                                        rx.el.div(
                                            rx.el.button(
                                                rx.icon("copy", class_name="h-4 w-4"),
                                                on_click=lambda: State.show_edit_user_form(
                                                    user
                                                ),
                                                class_name="p-2 text-blue-500 hover:bg-blue-100 rounded-full",
                                            ),
                                            rx.el.button(
                                                rx.icon(
                                                    "trash-2", class_name="h-4 w-4"
                                                ),
                                                on_click=lambda: State.delete_user(
                                                    user["username"]
                                                ),
                                                class_name="p-2 text-red-500 hover:bg-red-100 rounded-full",
                                            ),
                                            class_name="flex justify-center gap-2",
                                        )
                                    ),
                                    class_name="border-b",
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