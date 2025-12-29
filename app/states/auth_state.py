import reflex as rx
import bcrypt
from typing import Dict, List, Optional, Any
from sqlmodel import select
from sqlalchemy import func
from app.models import User as UserModel
from app.utils.auth import create_access_token, verify_token
from .types import User, Privileges, NewUser
from .mixin_state import MixinState

# Constants
DEFAULT_USER_PRIVILEGES: Privileges = {
    "view_ingresos": True,
    "create_ingresos": True,
    "view_ventas": True,
    "create_ventas": True,
    "view_inventario": True,
    "edit_inventario": True,
    "view_historial": True,
    "export_data": False,
    "view_cashbox": True,
    "manage_cashbox": True,
    "delete_sales": False,
    "manage_users": False,
    "view_servicios": True,
    "manage_reservations": True,
    "manage_config": False,
}

ADMIN_PRIVILEGES: Privileges = {
    "view_ingresos": True,
    "create_ingresos": True,
    "view_ventas": True,
    "create_ventas": True,
    "view_inventario": True,
    "edit_inventario": True,
    "view_historial": True,
    "export_data": True,
    "view_cashbox": True,
    "manage_cashbox": True,
    "delete_sales": True,
    "manage_users": True,
    "view_servicios": True,
    "manage_reservations": True,
    "manage_config": True,
}

CASHIER_PRIVILEGES: Privileges = {
    "view_ingresos": False,
    "create_ingresos": False,
    "view_ventas": True,
    "create_ventas": True,
    "view_inventario": True,
    "edit_inventario": False,
    "view_historial": False,
    "export_data": False,
    "view_cashbox": True,
    "manage_cashbox": True,
    "delete_sales": False,
    "manage_users": False,
    "view_servicios": False,
    "manage_reservations": False,
    "manage_config": False,
}

SUPERADMIN_PRIVILEGES: Privileges = {key: True for key in DEFAULT_USER_PRIVILEGES}

EMPTY_PRIVILEGES: Privileges = {key: False for key in DEFAULT_USER_PRIVILEGES}

DEFAULT_ROLE_TEMPLATES: Dict[str, Privileges] = {
    "Superadmin": SUPERADMIN_PRIVILEGES,
    "Administrador": ADMIN_PRIVILEGES,
    "Usuario": DEFAULT_USER_PRIVILEGES,
    "Cajero": CASHIER_PRIVILEGES,
}

class AuthState(MixinState):
    token: str = rx.LocalStorage("")
    # users: Dict[str, User] = {} # Removed in favor of DB
    roles: List[str] = ["Superadmin", "Administrador", "Usuario", "Cajero"]
    role_privileges: Dict[str, Privileges] = DEFAULT_ROLE_TEMPLATES.copy()
    
    error_message: str = ""
    show_user_form: bool = False
    new_user_data: NewUser = {
        "username": "",
        "password": "",
        "confirm_password": "",
        "role": "Usuario",
        "privileges": DEFAULT_USER_PRIVILEGES.copy(),
    }
    editing_user: Optional[Dict[str, Any]] = None
    new_role_name: str = ""

    @rx.var
    def is_authenticated(self) -> bool:
        return bool(verify_token(self.token))


    @rx.var
    def current_user(self) -> User:
        username = verify_token(self.token)
        if not username:
            return self._guest_user()
        
        with rx.session() as session:
            user = session.exec(
                select(UserModel).where(UserModel.username == username)
            ).first()
            
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "privileges": self._normalize_privileges(user.privileges or {}),
                    "password_hash": user.password_hash,
                }
        
        return self._guest_user()
    
    users_list: List[User] = []

    def load_users(self):
        with rx.session() as session:
            users = session.exec(select(UserModel)).all()
            normalized_users = []
            for user in users:
                normalized_users.append({
                    "username": user.username,
                    "role": user.role,
                    "privileges": self._normalize_privileges(user.privileges or {}),
                    "password_hash": user.password_hash,
                })
            self.users_list = sorted(normalized_users, key=lambda u: u["username"])

    def _guest_user(self) -> User:
        return {
            "username": "Invitado",
            "password_hash": "",
            "role": "Invitado",
            "privileges": EMPTY_PRIVILEGES.copy(),
        }

    def _normalize_privileges(self, privileges: Dict[str, bool]) -> Privileges:
        normalized = EMPTY_PRIVILEGES.copy()
        normalized.update(privileges)
        return normalized

    def _role_privileges(self, role: str) -> Privileges:
        role_key = self._find_role_key(role)
        if role_key and role_key in self.role_privileges:
            return self._normalize_privileges(self.role_privileges[role_key])
        return self._normalize_privileges(DEFAULT_USER_PRIVILEGES)

    def _find_role_key(self, role_name: str) -> str | None:
        target = (role_name or "").lower().strip()
        for r in self.roles:
            if r.lower() == target:
                return r
        return None

    def _reset_new_user_form(self):
        self.new_user_data = {
            "username": "",
            "password": "",
            "confirm_password": "",
            "role": "Usuario",
            "privileges": self._role_privileges("Usuario"),
        }
        self.editing_user = None
        self.new_role_name = ""

    @rx.event
    def login(self, form_data: dict):
        username = form_data["username"].lower()
        password = form_data["password"].encode("utf-8")
        
        with rx.session() as session:
            # Check if any users exist (Bootstrap Admin)
            user_count = session.exec(select(func.count(UserModel.id))).one()
            
            if user_count == 0:
                if username == "admin" and form_data["password"] == "admin":
                    # Create superadmin
                    password_hash = bcrypt.hashpw(
                        password, bcrypt.gensalt()
                    ).decode()
                    
                    admin_user = UserModel(
                        username="admin",
                        password_hash=password_hash,
                        role="Superadmin",
                        privileges=self._role_privileges("Superadmin")
                    )
                    session.add(admin_user)
                    session.commit()
                    
                    self.token = create_access_token("admin")
                    self.error_message = ""
                    return rx.redirect("/")
                else:
                    self.error_message = "Sistema no inicializado. Ingrese como admin/admin."
                    return

            user = session.exec(
                select(UserModel).where(UserModel.username == username)
            ).first()
            
            if user and bcrypt.checkpw(password, user.password_hash.encode("utf-8")):
                self.token = create_access_token(username)
                self.error_message = ""
                return rx.redirect("/")
            
        self.error_message = "Usuario o contraseña incorrectos."

    @rx.event
    def logout(self):
        self.token = ""
        return rx.redirect("/")

    @rx.event
    def show_create_user_form(self):
        self._reset_new_user_form()
        self.show_user_form = True

    def _open_user_editor(self, user: User):
        merged_privileges = self._normalize_privileges(user.get("privileges", {}))
        role_key = self._find_role_key(user["role"]) or user["role"]
        
        # Ensure role exists in our tracking
        if role_key not in self.role_privileges:
            self.role_privileges[role_key] = merged_privileges.copy()
            if role_key not in self.roles:
                self.roles.append(role_key)
                
        self.new_user_data = {
            "username": user["username"],
            "password": "",
            "confirm_password": "",
            "role": role_key,
            "privileges": merged_privileges,
        }
        self.editing_user = user
        self.show_user_form = True

    @rx.event
    def show_edit_user_form(self, user: User):
        self._open_user_editor(user)

    @rx.event
    def show_edit_user_form_by_username(self, username: str):
        key = (username or "").strip().lower()
        
        with rx.session() as session:
            user = session.exec(
                select(UserModel).where(UserModel.username == key)
            ).first()
            
            if not user:
                return rx.toast("Usuario a editar no encontrado.", duration=3000)
            
            # Convert to dict
            user_dict = {
                "username": user.username,
                "role": user.role,
                "privileges": user.privileges or {},
                "password_hash": user.password_hash,
            }
            self._open_user_editor(user_dict)

    @rx.event
    def set_user_form_open(self, is_open: bool):
        self.show_user_form = bool(is_open)
        if not is_open:
            self._reset_new_user_form()

    @rx.event
    def hide_user_form(self):
        self.show_user_form = False
        self._reset_new_user_form()

    @rx.event
    def handle_new_user_change(self, field: str, value: str):
        if field == "role":
            self.new_user_data["role"] = value
            self.new_user_data["privileges"] = self._role_privileges(value)
            return
        if field == "username":
            self.new_user_data["username"] = value.lower()
            return
        self.new_user_data[field] = value

    @rx.event
    def toggle_privilege(self, privilege: str):
        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        privileges[privilege] = not privileges[privilege]
        self.new_user_data["privileges"] = privileges

    @rx.event
    def apply_role_privileges(self):
        role = self.new_user_data.get("role") or "Usuario"
        self.new_user_data["privileges"] = self._role_privileges(role)

    @rx.event
    def update_new_role_name(self, value: str):
        self.new_role_name = value.strip()

    @rx.event
    def create_role_from_current_privileges(self):
        name = (self.new_role_name or "").strip()
        if not name:
            return rx.toast("Ingrese un nombre para el rol nuevo.", duration=3000)
        if name.lower() == "superadmin":
            return rx.toast("Superadmin ya existe como rol principal.", duration=3000)
        existing = self._find_role_key(name)
        if existing:
            return rx.toast("Ese rol ya existe.", duration=3000)
        
        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        self.role_privileges[name] = privileges.copy()
        if name not in self.roles:
            self.roles.append(name)
            
        self.new_role_name = ""
        self.new_user_data["role"] = name
        self.new_user_data["privileges"] = privileges.copy()
        return rx.toast(f"Rol {name} creado con los privilegios actuales.", duration=3000)

    @rx.event
    def save_role_template(self):
        role = (self.new_user_data.get("role") or "").strip()
        if not role:
            return rx.toast("Seleccione un rol para guardar sus privilegios.", duration=3000)
        if role.lower() == "superadmin":
            return rx.toast("No se puede modificar los privilegios de Superadmin.", duration=3000)
            
        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        role_key = self._find_role_key(role) or role
        
        self.role_privileges[role_key] = privileges.copy()
        if role_key not in self.roles:
            self.roles.append(role_key)
            
        return rx.toast(f"Plantilla de rol {role_key} actualizada.", duration=3000)

    @rx.event
    def save_user(self):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
            
        username = self.new_user_data["username"].lower().strip()
        if not username:
            return rx.toast("El nombre de usuario no puede estar vacío.", duration=3000)
            
        self.new_user_data["privileges"] = self._normalize_privileges(
            self.new_user_data["privileges"]
        )

        with rx.session() as session:
            if self.editing_user:
                # Update existing user
                user_to_update = session.exec(
                    select(UserModel).where(UserModel.username == self.editing_user["username"])
                ).first()
                
                if not user_to_update:
                    return rx.toast("Usuario a editar no encontrado.", duration=3000)
                    
                if self.new_user_data["password"]:
                    if (
                        self.new_user_data["password"]
                        != self.new_user_data["confirm_password"]
                    ):
                        return rx.toast("Las contraseñas no coinciden.", duration=3000)
                    password_hash = bcrypt.hashpw(
                        self.new_user_data["password"].encode(), bcrypt.gensalt()
                    ).decode()
                    user_to_update.password_hash = password_hash
                    
                user_to_update.role = self.new_user_data["role"]
                user_to_update.privileges = self.new_user_data["privileges"].copy()
                
                session.add(user_to_update)
                session.commit()
                
                self.hide_user_form()
                self.load_users()
                return rx.toast(f"Usuario {username} actualizado.", duration=3000)
            else:
                # Create new user
                existing_user = session.exec(
                    select(UserModel).where(UserModel.username == username)
                ).first()
                
                if existing_user:
                    return rx.toast("El nombre de usuario ya existe.", duration=3000)
                if not self.new_user_data["password"]:
                    return rx.toast("La contraseña no puede estar vacía.", duration=3000)
                if self.new_user_data["password"] != self.new_user_data["confirm_password"]:
                    return rx.toast("Las contraseñas no coinciden.", duration=3000)
                    
                password_hash = bcrypt.hashpw(
                    self.new_user_data["password"].encode(), bcrypt.gensalt()
                ).decode()
                
                new_user = UserModel(
                    username=username,
                    password_hash=password_hash,
                    role=self.new_user_data["role"],
                    privileges=self.new_user_data["privileges"].copy(),
                )
                session.add(new_user)
                session.commit()
                
                self.hide_user_form()
                self.load_users()
                return rx.toast(f"Usuario {username} creado.", duration=3000)

    @rx.event
    def delete_user(self, username: str):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para eliminar usuarios.", duration=3000)
        if username == "admin":
            return rx.toast("No se puede eliminar al superadmin.", duration=3000)
        if username == self.current_user["username"]:
            return rx.toast("No puedes eliminar tu propio usuario.", duration=3000)
            
        with rx.session() as session:
            user = session.exec(
                select(UserModel).where(UserModel.username == username)
            ).first()
            
            if user:
                session.delete(user)
                session.commit()
                self.load_users()
                return rx.toast(f"Usuario {username} eliminado.", duration=3000)
                
        return rx.toast(f"Usuario {username} no encontrado.", duration=3000)
