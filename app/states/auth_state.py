import reflex as rx
from typing import TypedDict
import bcrypt


class Privileges(TypedDict):
    view_ingresos: bool
    create_ingresos: bool
    view_ventas: bool
    create_ventas: bool
    view_inventario: bool
    edit_inventario: bool
    view_historial: bool
    export_data: bool
    view_cashbox: bool
    manage_users: bool


class User(TypedDict):
    username: str
    password_hash: str
    role: str
    privileges: Privileges

EMPTY_PRIVILEGES: Privileges = {
    "view_ingresos": False,
    "create_ingresos": False,
    "view_ventas": False,
    "create_ventas": False,
    "view_inventario": False,
    "edit_inventario": False,
    "view_historial": False,
    "export_data": False,
    "view_cashbox": False,
    "manage_users": False,
}


SUPERADMIN_PRIVILEGES: Privileges = {key: True for key in EMPTY_PRIVILEGES}


class AuthState(rx.State):
    token: str = rx.LocalStorage("")
    users: dict[str, User] = {
        "admin": {
            "username": "admin",
            "password_hash": bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode(),
            "role": "Superadmin",
            "privileges": SUPERADMIN_PRIVILEGES.copy(),
        }
    }
    error_message: str = ""

    @rx.var
    def is_authenticated(self) -> bool:
        return self.token in self.users

    @rx.var
    def get_current_user(self) -> User:
        if not self.token:
            return self._guest_user()
        user = self.users.get(self.token)
        if user:
            return user
        return self._guest_user()

    def _guest_user(self) -> User:
        return {
            "username": "Invitado",
            "password_hash": "",
            "role": "Invitado",
            "privileges": EMPTY_PRIVILEGES.copy(),
        }

    @rx.event
    def login(self, form_data: dict):
        username = form_data["username"].lower()
        password = form_data["password"].encode("utf-8")
        user = self.users.get(username)
        if user and bcrypt.checkpw(password, user["password_hash"].encode("utf-8")):
            self.token = username
            self.error_message = ""
            return rx.redirect("/")
        self.error_message = "Usuario o contraseña incorrectos."

    @rx.event
    def logout(self):
        self.token = ""
        return rx.redirect("/")
