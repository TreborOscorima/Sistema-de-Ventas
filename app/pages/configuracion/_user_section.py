import reflex as rx
from app.state import State
from app.components.ui import (
  BUTTON_STYLES,
  CARD_STYLES,
  INPUT_STYLES,
  SELECT_STYLES,
  TABLE_STYLES,
  TYPOGRAPHY,
  toggle_switch,
)

PRIVILEGE_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
  (
    "Ingresos",
    [
      ("Ver Ingresos", "view_ingresos"),
      ("Crear Ingresos", "create_ingresos"),
    ],
  ),
  (
    "Compras y Proveedores",
    [
      ("Ver Compras", "view_compras"),
      ("Gestionar Proveedores", "manage_proveedores"),
    ],
  ),
  (
    "Ventas y Caja",
    [
      ("Ver Ventas", "view_ventas"),
      ("Crear Ventas", "create_ventas"),
      ("Ver Presupuestos", "view_presupuestos"),
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
      ("Ver Etiquetas", "view_etiquetas"),
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
    "Comercial",
    [
      ("Gestionar Promociones", "manage_promociones"),
      ("Gestionar Listas de Precios", "manage_listas_precios"),
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
    rx.el.label(label, class_name=f"{TYPOGRAPHY['label']} flex-1 min-w-0"),
    rx.el.div(
      toggle_switch(
        checked=State.new_user_data["privileges"][privilege],
        on_change=lambda value: State.toggle_privilege(privilege),
      ),
    ),
    class_name=(
      "flex items-center justify-between rounded-md border border-slate-200 "
      "bg-white px-3 py-2"
    ),
  )


def privilege_section(title: str, privileges: list[tuple[str, str]]) -> rx.Component:
  return rx.el.div(
    rx.el.p(title, class_name=TYPOGRAPHY["label_secondary"]),
    rx.el.div(
      *[privilege_switch(label, key) for label, key in privileges],
      class_name="grid grid-cols-1 md:grid-cols-2 gap-3",
    ),
    class_name="p-4 rounded-xl bg-white space-y-3 border border-slate-200",
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
    class_name="flex flex-wrap gap-2 w-full",
  )


def user_form() -> rx.Component:
  return rx.radix.primitives.dialog.root(
    rx.radix.primitives.dialog.trigger(
      rx.el.button(
        "Crear Nuevo Usuario",
        on_click=State.show_create_user_form,
        class_name=f"{BUTTON_STYLES['primary']} w-full sm:w-auto mb-6",
      ),
      as_child=True,
    ),
    rx.radix.primitives.dialog.portal(
      rx.radix.primitives.dialog.overlay(
        class_name="fixed inset-0 bg-black/40 backdrop-blur-sm modal-overlay"
      ),
        rx.radix.primitives.dialog.content(
          rx.radix.primitives.dialog.title(
            rx.cond(State.editing_user, "Editar Usuario", "Crear Nuevo Usuario"),
            class_name=f"{TYPOGRAPHY['section_title']} flex-shrink-0",
          ),
          rx.divider(color="slate-100"),
          rx.el.div(
          rx.el.div(
            rx.el.label("Nombre de Usuario", class_name=TYPOGRAPHY["label"]),
            rx.el.input(
              default_value=State.new_user_data["username"],
              on_blur=lambda v: State.handle_new_user_change(
                "username", v
              ),
              disabled=rx.cond(State.editing_user, True, False),
              class_name=f"{INPUT_STYLES['default']} mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Correo", class_name=TYPOGRAPHY["label"]),
            rx.el.input(
              type="email",
              placeholder="usuario@empresa.com",
              default_value=State.new_user_data["email"],
              on_blur=lambda v: State.handle_new_user_change(
                "email", v
              ),
              class_name=f"{INPUT_STYLES['default']} mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Rol", class_name=TYPOGRAPHY["label"]),
            rx.el.select(
              rx.foreach(
                State.roles,
                lambda role: rx.el.option(role, value=role),
              ),
              value=State.new_user_data["role"],
              on_change=lambda v: State.handle_new_user_change("role", v),
              class_name=f"{SELECT_STYLES['default']} mt-1",
            ),
            rx.el.p(
              "Los privilegios se cargan de acuerdo al rol seleccionado. Puedes afinar y guardar nuevos roles debajo.",
              class_name=f"{TYPOGRAPHY['caption']} mt-2",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Crear nuevo rol", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.input(
                placeholder="Ej: Administrador, Cajero, Auditor",
                default_value=State.new_role_name,
                on_blur=lambda v: State.update_new_role_name(v),
                class_name=f"flex-1 {INPUT_STYLES['default']}",
              ),
              rx.el.button(
                "Crear rol con estos privilegios",
                on_click=State.create_role_from_current_privileges,
                class_name=f"{BUTTON_STYLES['secondary']} whitespace-nowrap",
              ),
              class_name="flex flex-col sm:flex-row sm:items-center gap-3 mt-2",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Contraseña", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.input(
                type=rx.cond(
                  State.show_user_form_password,
                  "text",
                  "password",
                ),
                placeholder=rx.cond(
                  State.editing_user,
                  "Dejar en blanco para no cambiar",
                  "",
                ),
                default_value=State.new_user_data["password"],
                on_blur=lambda v: State.handle_new_user_change(
                  "password", v
                ),
                class_name=f"{INPUT_STYLES['default']} pr-11",
              ),
              rx.el.button(
                rx.cond(
                  State.show_user_form_password,
                  rx.icon("eye-off", class_name="h-4 w-4"),
                  rx.icon("eye", class_name="h-4 w-4"),
                ),
                type="button",
                on_click=State.toggle_user_form_password_visibility,
                class_name=(
                  "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                  "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                  "hover:text-slate-700 transition-colors duration-150"
                ),
                aria_label=rx.cond(
                  State.show_user_form_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
                title=rx.cond(
                  State.show_user_form_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
              ),
              class_name="relative mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.label("Confirmar Contraseña", class_name=TYPOGRAPHY["label"]),
            rx.el.div(
              rx.el.input(
                type=rx.cond(
                  State.show_user_form_confirm_password,
                  "text",
                  "password",
                ),
                default_value=State.new_user_data["confirm_password"],
                on_blur=lambda v: State.handle_new_user_change(
                  "confirm_password", v
                ),
                class_name=f"{INPUT_STYLES['default']} pr-11",
              ),
              rx.el.button(
                rx.cond(
                  State.show_user_form_confirm_password,
                  rx.icon("eye-off", class_name="h-4 w-4"),
                  rx.icon("eye", class_name="h-4 w-4"),
                ),
                type="button",
                on_click=State.toggle_user_form_confirm_password_visibility,
                class_name=(
                  "absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 "
                  "items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 "
                  "hover:text-slate-700 transition-colors duration-150"
                ),
                aria_label=rx.cond(
                  State.show_user_form_confirm_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
                title=rx.cond(
                  State.show_user_form_confirm_password,
                  "Ocultar contraseña",
                  "Mostrar contraseña",
                ),
              ),
              class_name="relative mt-1",
            ),
            class_name="mb-4",
          ),
          rx.el.div(
            rx.el.div(
              rx.el.h3(
                "Privilegios", class_name=TYPOGRAPHY["card_title"]
              ),
              rx.el.p(
                "Asigna los accesos para el rol elegido. Si necesitas volver a los permisos sugeridos del rol, usa el boton.",
                class_name=TYPOGRAPHY["body_secondary"],
              ),
              class_name="flex flex-col gap-1",
            ),
            rx.el.div(
              rx.el.button(
                "Restaurar privilegios del rol",
                on_click=State.apply_role_privileges,
                class_name=BUTTON_STYLES["secondary_sm"],
              ),
              rx.el.button(
                "Guardar como plantilla de rol",
                on_click=State.save_role_template,
                class_name=BUTTON_STYLES["secondary_sm"],
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
          key=State.user_form_key.to_string(),
        ),
        rx.divider(color="slate-100"),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=State.hide_user_form,
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.el.button(
            "Guardar",
            on_click=State.save_user,
            class_name=BUTTON_STYLES["success"],
          ),
          class_name="flex flex-col sm:flex-row justify-end items-stretch sm:items-center gap-3 sm:gap-4 flex-shrink-0 pt-3 border-t border-slate-100",
        ),
        class_name=(
          "fixed left-1/2 top-1/2 w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 "
          "-translate-y-1/2 rounded-xl bg-white p-5 sm:p-6 shadow-xl focus:outline-none "
          "max-h-[90vh] flex flex-col gap-4 border border-slate-200"
        ),
      ),
    ),
    open=State.show_user_form,
    on_open_change=State.set_user_form_open,
  )


def _user_card(user: rx.Var[dict]) -> rx.Component:
  """Card de usuario para vista móvil (visible solo < md)."""
  return rx.el.div(
    # Nombre + Rol
    rx.el.div(
      rx.el.span(user["username"], class_name="font-semibold text-slate-800 text-sm"),
      rx.el.span(user["role"], class_name="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full"),
      class_name="flex items-center justify-between gap-2",
    ),
    # Privilegios
    privilege_badges(user),
    # Acciones
    rx.el.div(
      rx.el.button(
        rx.icon("pencil", class_name="h-4 w-4"),
        on_click=lambda _, username=user["username"]: State.show_edit_user_form_by_username(username),
        title="Editar usuario",
        aria_label="Editar usuario",
        class_name=BUTTON_STYLES["icon_primary"],
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        on_click=lambda _, username=user["username"]: State.delete_user(username),
        title="Eliminar usuario",
        aria_label="Eliminar usuario",
        class_name=BUTTON_STYLES["icon_danger"],
      ),
      class_name="flex gap-2 pt-2 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3",
    key=user["username"],
  )


def user_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.div(
        rx.el.h2(
          "GESTION DE USUARIOS", class_name="text-xl font-semibold text-slate-700"
        ),
        rx.el.p(
          "Crea usuarios, roles y ajusta sus privilegios.",
          class_name=TYPOGRAPHY["body_secondary"],
        ),
        class_name="flex flex-col",
      ),
      user_form(),
      class_name="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-2",
    ),
    # Vista móvil: cards (visible solo < md)
    rx.el.div(
      rx.foreach(State.users_list, _user_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Vista escritorio: tabla (visible solo >= md)
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Usuario", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-32"),
            rx.el.th("Rol", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-28"),
            rx.el.th("Privilegios", scope="col", class_name=f"{TABLE_STYLES['header_cell']} w-full"),
            rx.el.th(
              "Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center w-24"
            ),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(

          rx.foreach(
            State.users_list,
            lambda user: rx.el.tr(
              rx.el.td(user["username"], class_name="py-3 px-4 w-32 truncate"),
              rx.el.td(user["role"], class_name="py-3 px-4 w-28 truncate"),
              rx.el.td(
                privilege_badges(user),
                class_name="py-3 px-4 w-full",
              ),
              rx.el.td(
                rx.el.div(
                  rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda _,
                    username=user["username"]: State.show_edit_user_form_by_username(
                      username
                    ),
                    title="Editar usuario",
                    aria_label="Editar usuario",
                    class_name=BUTTON_STYLES["icon_primary"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _,
                    username=user["username"]: State.delete_user(
                      username
                    ),
                    title="Eliminar usuario",
                    aria_label="Eliminar usuario",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="flex justify-center gap-2",
                )
              ),
              class_name="border-b",
              key=user["username"],
            ),
          )
        ),
        class_name="w-full min-w-[600px]",
      ),
      class_name=f"hidden md:block {CARD_STYLES['default']} overflow-x-auto",
    ),
    class_name="space-y-4",
  )


def branch_users_modal() -> rx.Component:
  return rx.dialog.root(
    rx.dialog.content(
      rx.el.div(
        rx.el.div(
          rx.el.h3(
            rx.el.span("Acceso por Sucursal", class_name="text-xl font-semibold text-slate-800"),
            rx.el.span(
              State.branch_users_branch_name,
              class_name="text-sm font-medium text-slate-500",
            ),
            class_name="flex flex-col gap-1",
          ),
          rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=State.close_branch_users,
            title="Cerrar",
            aria_label="Cerrar",
            class_name=BUTTON_STYLES["icon_ghost"],
          ),
          class_name="flex items-start justify-between",
        ),
        rx.el.div(
          rx.el.div(
            rx.foreach(
              State.branch_users_rows,
              lambda user: rx.el.div(
                rx.el.div(
                  rx.el.div(
                    rx.el.span(user["username"], class_name="font-semibold text-slate-800"),
                    rx.el.span(
                      user["role"],
                      class_name=TYPOGRAPHY["caption"],
                    ),
                    class_name="flex flex-col",
                  ),
                  rx.el.span(user["email"], class_name="text-xs text-slate-400"),
                  class_name="flex flex-col",
                ),
                rx.el.div(
                  toggle_switch(
                    checked=user["has_access"],
                    on_change=lambda value, uid=user["id"]: State.set_branch_user_access(uid, value),
                  ),
                ),
                class_name="flex items-center justify-between gap-4 p-3 border border-slate-200 rounded-lg bg-white",
              ),
            ),
            class_name="space-y-3",
          ),
          class_name="max-h-[55vh] overflow-y-auto",
        ),
        rx.el.div(
          rx.el.button(
            "Cancelar",
            on_click=State.close_branch_users,
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.el.button(
            "Guardar",
            on_click=State.save_branch_users,
            class_name=BUTTON_STYLES["success"],
          ),
          class_name="flex flex-col sm:flex-row justify-end gap-3 pt-3 border-t border-slate-100",
        ),
        class_name="flex flex-col gap-4",
      ),
      class_name="bg-white rounded-xl shadow-xl border border-slate-200 p-5 w-[calc(100%-2rem)] max-w-2xl",
    ),
    open=State.branch_users_modal_open,
    on_open_change=State.close_branch_users,
  )


def _branch_card(branch: rx.Var[dict]) -> rx.Component:
  """Card de sucursal para vista móvil (visible solo < md)."""
  return rx.el.div(
    # Nombre + contador de usuarios
    rx.el.div(
      rx.el.span(branch["name"], class_name="font-semibold text-slate-800 text-sm"),
      rx.el.span(
        branch["users_count"].to_string(), " usuario(s)",
        class_name="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full whitespace-nowrap",
      ),
    ),
    # Dirección
    rx.el.p(
      branch["address"],
      class_name="text-xs text-slate-500",
    ),
    # Acciones
    rx.el.div(
      rx.el.button(
        rx.icon("users", class_name="h-4 w-4"),
        on_click=lambda _, bid=branch["id"]: State.open_branch_users(bid),
        title="Gestionar usuarios por sucursal",
        aria_label="Gestionar usuarios por sucursal",
        class_name=BUTTON_STYLES["icon_primary"],
      ),
      rx.el.button(
        rx.icon("pencil", class_name="h-4 w-4"),
        on_click=lambda _, bid=branch["id"]: State.start_edit_branch(bid),
        title="Editar sucursal",
        aria_label="Editar sucursal",
        class_name=BUTTON_STYLES["icon_primary"],
      ),
      rx.el.button(
        rx.icon("trash-2", class_name="h-4 w-4"),
        on_click=lambda _, bid=branch["id"]: State.delete_branch(bid),
        title="Eliminar sucursal",
        aria_label="Eliminar sucursal",
        class_name=BUTTON_STYLES["icon_danger"],
      ),
      class_name="flex gap-2 pt-2 border-t border-slate-100",
    ),
    class_name="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3",
    key=branch["id"],
  )


def branch_section() -> rx.Component:
  return rx.el.div(
    rx.el.div(
      rx.el.h2(
        "SUCURSALES", class_name="text-xl font-semibold text-slate-700"
      ),
      rx.el.p(
        "Crea sucursales y asigna usuarios por empresa.",
        class_name=TYPOGRAPHY["body_secondary"],
      ),
      class_name="space-y-1",
    ),
    branch_users_modal(),
    rx.el.div(
      rx.el.div(
        rx.el.label("Nombre de Sucursal", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=rx.cond(
            State.editing_branch_id != "",
            State.editing_branch_name,
            State.new_branch_name,
          ),
          on_blur=State.handle_branch_name_change,
          placeholder="Ej: Casa Matriz, Sucursal Centro",
          key=State.editing_branch_id + "-branch-name",
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.label("Dirección", class_name=TYPOGRAPHY["label"]),
        rx.el.input(
          default_value=rx.cond(
            State.editing_branch_id != "",
            State.editing_branch_address,
            State.new_branch_address,
          ),
          on_blur=State.handle_branch_address_change,
          placeholder="Ej: Av. Principal 123",
          key=State.editing_branch_id + "-branch-address",
          class_name=INPUT_STYLES["default"],
        ),
        class_name="flex flex-col gap-1",
      ),
      rx.el.div(
        rx.el.button(
          rx.cond(State.editing_branch_id != "", "Actualizar", "Crear"),
          on_click=rx.cond(State.editing_branch_id != "", State.save_branch, State.create_branch),
          class_name=BUTTON_STYLES["success"],
        ),
        rx.cond(
          State.editing_branch_id != "",
          rx.el.button(
            "Cancelar",
            on_click=State.cancel_edit_branch,
            class_name=BUTTON_STYLES["secondary"],
          ),
          rx.fragment(),
        ),
        class_name="flex flex-col sm:flex-row gap-2 items-stretch sm:items-end",
      ),
      class_name=f"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 {CARD_STYLES['compact']}",
    ),
    # Vista móvil: cards (visible solo < md)
    rx.el.div(
      rx.foreach(State.branches_list, _branch_card),
      class_name="flex flex-col gap-3 md:hidden",
    ),
    # Vista escritorio: tabla (visible solo >= md)
    rx.el.div(
      rx.el.table(
        rx.el.thead(
          rx.el.tr(
            rx.el.th("Sucursal", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Dirección", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Usuarios", scope="col", class_name=TABLE_STYLES["header_cell"]),
            rx.el.th("Acciones", scope="col", class_name=f"{TABLE_STYLES['header_cell']} text-center"),
            class_name=TABLE_STYLES["header"],
          )
        ),
        rx.el.tbody(
          rx.foreach(
            State.branches_list,
            lambda branch: rx.el.tr(
              rx.el.td(branch["name"], class_name=TABLE_STYLES["cell"]),
              rx.el.td(branch["address"], class_name=f"{TABLE_STYLES['cell']} break-words"),
              rx.el.td(branch["users_count"].to_string(), class_name=TABLE_STYLES["cell"]),
              rx.el.td(
                rx.el.div(
                  rx.el.button(
                    rx.icon("users", class_name="h-4 w-4"),
                    on_click=lambda _, bid=branch["id"]: State.open_branch_users(bid),
                    title="Gestionar usuarios por sucursal",
                    aria_label="Gestionar usuarios por sucursal",
                    class_name=BUTTON_STYLES["icon_primary"],
                  ),
                  rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda _, bid=branch["id"]: State.start_edit_branch(bid),
                    title="Editar sucursal",
                    aria_label="Editar sucursal",
                    class_name=BUTTON_STYLES["icon_primary"],
                  ),
                  rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda _, bid=branch["id"]: State.delete_branch(bid),
                    title="Eliminar sucursal",
                    aria_label="Eliminar sucursal",
                    class_name=BUTTON_STYLES["icon_danger"],
                  ),
                  class_name="flex justify-center gap-2",
                ),
                class_name=TABLE_STYLES["cell"],
              ),
              class_name=TABLE_STYLES["row"],
              key=branch["id"],
            ),
          )
        ),
        class_name="w-full min-w-[500px]",
      ),
      class_name=f"hidden md:block {CARD_STYLES['default']} overflow-x-auto",
    ),
    class_name="space-y-4",
  )
