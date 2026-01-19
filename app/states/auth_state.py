import os
import reflex as rx
import bcrypt
from typing import Dict, List, Optional, Any
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.models import Permission, Role, User as UserModel
from app.utils.auth import create_access_token, verify_token
from app.utils.logger import get_logger
from .types import User, Privileges, NewUser
from .mixin_state import MixinState

# Constantes
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
    "view_clientes": True,
    "manage_clientes": True,
    "view_cuentas": True,
    "manage_cuentas": False,
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
    "view_clientes": True,
    "manage_clientes": True,
    "view_cuentas": True,
    "manage_cuentas": True,
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
    "view_clientes": True,
    "manage_clientes": True,
    "view_cuentas": False,
    "manage_cuentas": False,
}

SUPERADMIN_PRIVILEGES: Privileges = {key: True for key in DEFAULT_USER_PRIVILEGES}

EMPTY_PRIVILEGES: Privileges = {key: False for key in DEFAULT_USER_PRIVILEGES}

DEFAULT_ROLE_TEMPLATES: Dict[str, Privileges] = {
    "Superadmin": SUPERADMIN_PRIVILEGES,
    "Administrador": ADMIN_PRIVILEGES,
    "Usuario": DEFAULT_USER_PRIVILEGES,
    "Cajero": CASHIER_PRIVILEGES,
}

logger = get_logger("AuthState")

class AuthState(MixinState):
    token: str = rx.LocalStorage("")
    # users: Dict[str, User] = {} # Eliminado a favor de la BD
    roles: List[str] = ["Superadmin", "Administrador", "Usuario", "Cajero"]
    role_privileges: Dict[str, Privileges] = DEFAULT_ROLE_TEMPLATES.copy()
    
    error_message: str = ""
    password_change_error: str = ""
    needs_initial_admin: bool = False
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
        user = self.current_user
        return bool(user and user.get("username") != "Invitado")


    @rx.var
    def current_user(self) -> User:
        username = verify_token(self.token)
        if not username:
            return self._guest_user()
        
        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.username == username)
                .options(selectinload(UserModel.role).selectinload(Role.permissions))
            ).first()
            
            if user and user.is_active:
                role_name = user.role.name if user.role else "Sin rol"
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": role_name,
                    "privileges": self._get_privileges_dict(user),
                    "must_change_password": bool(
                        getattr(user, "must_change_password", False)
                    ),
                }
        
        return self._guest_user()
    
    users_list: List[User] = []

    def load_users(self):
        if not self.current_user["privileges"].get("manage_users"):
            self.users_list = []
            return
        with rx.session() as session:
            users = session.exec(
                select(UserModel)
                .options(selectinload(UserModel.role).selectinload(Role.permissions))
            ).all()
            self._load_roles_cache(session)
            normalized_users = []
            for user in users:
                role_name = user.role.name if user.role else "Sin rol"
                normalized_users.append({
                    "id": user.id,
                    "username": user.username,
                    "role": role_name,
                    "privileges": self._get_privileges_dict(user),
                    "must_change_password": bool(
                        getattr(user, "must_change_password", False)
                    ),
                })
            self.users_list = sorted(normalized_users, key=lambda u: u["username"])

    def _guest_user(self) -> User:
        return {
            "id": None,
            "username": "Invitado",
            "role": "Invitado",
            "privileges": EMPTY_PRIVILEGES.copy(),
            "must_change_password": False,
        }

    def _normalize_privileges(self, privileges: Dict[str, bool]) -> Privileges:
        normalized = EMPTY_PRIVILEGES.copy()
        normalized.update(privileges)
        return normalized

    def _get_privileges_dict(self, user: UserModel | None) -> Privileges:
        if not user or not user.role:
            return EMPTY_PRIVILEGES.copy()
        permissions = {
            perm.codename: True
            for perm in (user.role.permissions or [])
            if perm.codename
        }
        role_name = (user.role.name or "").strip().lower()
        if role_name == "superadmin":
            all_privileges = {key: True for key in DEFAULT_USER_PRIVILEGES}
            all_privileges.update(permissions)
            return self._normalize_privileges(all_privileges)
        return self._normalize_privileges(permissions)

    def _load_roles_cache(self, session):
        roles = session.exec(
            select(Role).options(selectinload(Role.permissions))
        ).all()
        if not roles:
            self.roles = list(DEFAULT_ROLE_TEMPLATES)
            self.role_privileges = DEFAULT_ROLE_TEMPLATES.copy()
            return
        self.roles = [role.name for role in roles]
        self.role_privileges = {
            role.name: self._normalize_privileges(
                {
                    perm.codename: True
                    for perm in (role.permissions or [])
                    if perm.codename
                }
            )
            for role in roles
        }

    def _ensure_permissions(self, session, codenames: list[str]) -> Dict[str, Permission]:
        if not codenames:
            return {}
        existing = session.exec(
            select(Permission).where(Permission.codename.in_(codenames))
        ).all()
        by_code = {perm.codename: perm for perm in existing if perm.codename}
        for code in codenames:
            if code not in by_code:
                perm = Permission(codename=code, description="")
                session.add(perm)
                by_code[code] = perm
        session.flush()
        return by_code

    def _get_role_by_name(self, session, role_name: str) -> Role | None:
        target = (role_name or "").strip().lower()
        if not target:
            return None
        return session.exec(
            select(Role)
            .where(func.lower(Role.name) == target)
            .options(selectinload(Role.permissions))
        ).first()

    def _ensure_role(
        self,
        session,
        role_name: str,
        privileges: Privileges,
        overwrite: bool = False,
    ) -> Role:
        role = self._get_role_by_name(session, role_name)
        if not role:
            role = Role(name=role_name, description="")
            session.add(role)
            session.flush()
        if overwrite or not role.permissions:
            permission_map = self._ensure_permissions(
                session, list(privileges.keys())
            )
            role.permissions = [
                permission_map[code]
                for code, enabled in privileges.items()
                if enabled
            ]
            session.add(role)
        return role

    def _bootstrap_default_roles(self, session):
        role_count = session.exec(select(func.count(Role.id))).one()
        if role_count and role_count > 0:
            self._load_roles_cache(session)
            return
        permission_map = self._ensure_permissions(
            session, list(DEFAULT_USER_PRIVILEGES.keys())
        )
        for role_name, privileges in DEFAULT_ROLE_TEMPLATES.items():
            role = Role(name=role_name, description="")
            role.permissions = [
                permission_map[code]
                for code, enabled in privileges.items()
                if enabled
            ]
            session.add(role)
        session.commit()
        self._load_roles_cache(session)

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

    def _resolve_env(self) -> str:
        value = (os.getenv("ENV") or "dev").strip().lower()
        if value in {"prod", "production"}:
            return "prod"
        return "dev"

    def _initial_admin_password(self) -> str | None:
        value = (os.getenv("INITIAL_ADMIN_PASSWORD") or "").strip()
        return value or None

    def _default_route_for_privileges(self, privileges: Dict[str, bool]) -> str:
        if privileges.get("view_ingresos"):
            return "/"
        if privileges.get("view_ventas"):
            return "/venta"
        if privileges.get("view_cashbox"):
            return "/caja"
        if privileges.get("view_inventario"):
            return "/inventario"
        if privileges.get("view_historial"):
            return "/historial"
        if privileges.get("view_servicios"):
            return "/servicios"
        if privileges.get("view_clientes"):
            return "/clientes"
        if privileges.get("view_cuentas"):
            return "/cuentas"
        if privileges.get("manage_config"):
            return "/configuracion"
        return "/"

    @rx.event
    def ensure_roles_and_permissions(self):
        with rx.session() as session:
            self._bootstrap_default_roles(session)
            user_count = session.exec(select(func.count(UserModel.id))).one()
            self.needs_initial_admin = not user_count or user_count == 0

    @rx.event
    def ensure_view_ingresos(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_ingresos"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Ingresos.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_ventas(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_ventas"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Ventas.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_cashbox(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_cashbox"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Caja.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_inventario(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_inventario"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Inventario.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_historial(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_historial"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Historial.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_servicios(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_servicios"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Servicios.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_clientes(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_clientes"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Clientes.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_view_cuentas(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if not self.current_user["privileges"].get("view_cuentas"):
            return rx.chain(
                rx.toast(
                    "Acceso denegado: No tienes permiso para ver Cuentas.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_admin_access(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        # Verifica roles exactos segun tu DB (Mayusculas importan)
        if self.current_user["role"] not in ["Superadmin", "Administrador"]:
            return rx.chain(
                rx.toast(
                    "Acceso denegado: Se requiere nivel de Administrador.",
                    status="error",
                ),
                rx.redirect("/"),
            )

    @rx.event
    def ensure_password_change(self):
        if not self.is_authenticated:
            if self.router.url.path != "/":
                return rx.redirect("/")
            return
        must_change = self.current_user.get("must_change_password", False)
        current_path = self.router.url.path
        if must_change and current_path != "/cambiar-clave":
            return rx.redirect("/cambiar-clave")
        if not must_change and current_path == "/cambiar-clave":
            return rx.redirect(
                self._default_route_for_privileges(
                    self.current_user["privileges"]
                )
            )

    @rx.event
    def login(self, form_data: dict):
        username = (form_data.get("username") or "").strip().lower()
        raw_password = form_data.get("password") or ""
        password = raw_password.encode("utf-8")

        with rx.session() as session:
            admin_user = session.exec(
                select(UserModel).where(UserModel.username == "admin")
            ).first()
            if admin_user and self.needs_initial_admin:
                self.needs_initial_admin = False

            if self.needs_initial_admin and not admin_user:
                env = self._resolve_env()
                initial_password = self._initial_admin_password()
                if not initial_password:
                    if env == "dev":
                        initial_password = "admin"
                        logger.warning(
                            "WARNING: usando credenciales inseguras por defecto para desarrollo."
                        )
                    else:
                        self.error_message = (
                            "Sistema no inicializado. Configure INITIAL_ADMIN_PASSWORD."
                        )
                        return

                if username == "admin" and raw_password == initial_password:
                    # Crear superadmin
                    password_hash = bcrypt.hashpw(
                        password, bcrypt.gensalt()
                    ).decode()
                    role = self._get_role_by_name(session, "Superadmin")
                    if not role:
                        role = self._ensure_role(
                            session,
                            "Superadmin",
                            self._normalize_privileges(SUPERADMIN_PRIVILEGES),
                            overwrite=True,
                        )
                    must_change_password = env == "prod"
                    admin_user = UserModel(
                        username="admin",
                        password_hash=password_hash,
                        role_id=role.id,
                        must_change_password=must_change_password,
                    )
                    session.add(admin_user)
                    session.commit()

                    self.token = create_access_token("admin")
                    self.error_message = ""
                    self.password_change_error = ""
                    self.needs_initial_admin = False
                    if must_change_password:
                        return rx.redirect("/cambiar-clave")
                    return rx.redirect("/")

                self.error_message = (
                    "Sistema no inicializado. Ingrese la contraseña inicial."
                )
                return

            user = session.exec(
                select(UserModel).where(UserModel.username == username)
            ).first()

            if user and bcrypt.checkpw(password, user.password_hash.encode("utf-8")):
                if not user.is_active:
                    self.error_message = "Usuario inactivo. Contacte al administrador."
                    return
                if not user.role_id:
                    fallback_role = (
                        "Superadmin" if username == "admin" else "Usuario"
                    )
                    role = self._get_role_by_name(session, fallback_role)
                    if not role:
                        default_privileges = (
                            SUPERADMIN_PRIVILEGES
                            if fallback_role == "Superadmin"
                            else DEFAULT_USER_PRIVILEGES
                        )
                        role = self._ensure_role(
                            session,
                            fallback_role,
                            self._normalize_privileges(default_privileges),
                            overwrite=True,
                        )
                    user.role_id = role.id
                    session.add(user)
                    session.commit()
                self.token = create_access_token(username)
                self.error_message = ""
                self.password_change_error = ""
                self._load_roles_cache(session)
                privileges = self._get_privileges_dict(user) or {}
                if getattr(user, "must_change_password", False):
                    return rx.redirect("/cambiar-clave")
                return rx.redirect(self._default_route_for_privileges(privileges))

        self.error_message = "Usuario o contraseña incorrectos."

    @rx.event
    def change_password(self, form_data: dict):
        if not self.is_authenticated:
            return rx.redirect("/")
        new_password = (form_data.get("password") or "").strip()
        confirm_password = (form_data.get("confirm_password") or "").strip()
        username = (self.current_user.get("username") or "").strip()

        if not new_password:
            self.password_change_error = "La contraseña no puede estar vacía."
            return
        if len(new_password) < 6:
            self.password_change_error = (
                "La contraseña debe tener al menos 6 caracteres."
            )
            return
        if username and new_password.lower() == username.lower():
            self.password_change_error = (
                "La contraseña no puede ser igual al usuario."
            )
            return
        if new_password != confirm_password:
            self.password_change_error = "Las contraseñas no coinciden."
            return

        with rx.session() as session:
            user = session.exec(
                select(UserModel).where(UserModel.username == username)
            ).first()
            if not user:
                self.password_change_error = "Usuario no encontrado."
                return
            password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), bcrypt.gensalt()
            ).decode()
            user.password_hash = password_hash
            user.must_change_password = False
            session.add(user)
            session.commit()

        self.password_change_error = ""
        return rx.chain(
            rx.toast("Contraseña actualizada.", duration=3000),
            rx.redirect(
                self._default_route_for_privileges(
                    self.current_user["privileges"]
                )
            ),
        )
    @rx.event
    def logout(self):
        self.token = ""
        self.password_change_error = ""
        return rx.redirect("/")

    @rx.event
    def show_create_user_form(self):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        self._reset_new_user_form()
        self.show_user_form = True

    def _open_user_editor(self, user: User):
        merged_privileges = self._normalize_privileges(user.get("privileges", {}))
        role_key = self._find_role_key(user["role"]) or user["role"]
        
        # Asegurar que el rol exista en nuestro registro
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
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        self._open_user_editor(user)

    @rx.event
    def show_edit_user_form_by_username(self, username: str):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        key = (username or "").strip().lower()
        
        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.username == key)
                .options(selectinload(UserModel.role).selectinload(Role.permissions))
            ).first()
            
            if not user:
                return rx.toast("Usuario a editar no encontrado.", duration=3000)
            
            # Convertir a dict
            role_name = user.role.name if user.role else "Sin rol"
            user_dict = {
                "username": user.username,
                "role": role_name,
                "privileges": self._get_privileges_dict(user),
                "must_change_password": bool(
                    getattr(user, "must_change_password", False)
                ),
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
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        name = (self.new_role_name or "").strip()
        if not name:
            return rx.toast("Ingrese un nombre para el rol nuevo.", duration=3000)
        if name.lower() == "superadmin":
            return rx.toast("Superadmin ya existe como rol principal.", duration=3000)
        existing = self._find_role_key(name)
        if existing:
            return rx.toast("Ese rol ya existe.", duration=3000)
        
        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        with rx.session() as session:
            if self._get_role_by_name(session, name):
                return rx.toast("Ese rol ya existe.", duration=3000)
            self._ensure_role(session, name, privileges, overwrite=True)
            session.commit()
            self._load_roles_cache(session)
            
        self.new_role_name = ""
        self.new_user_data["role"] = name
        self.new_user_data["privileges"] = privileges.copy()
        return rx.toast(f"Rol {name} creado con los privilegios actuales.", duration=3000)

    @rx.event
    def save_role_template(self):
        if not self.current_user["privileges"].get("manage_users"):
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
        role = (self.new_user_data.get("role") or "").strip()
        if not role:
            return rx.toast("Seleccione un rol para guardar sus privilegios.", duration=3000)
        if role.lower() == "superadmin":
            return rx.toast("No se puede modificar los privilegios de Superadmin.", duration=3000)
            
        privileges = self._normalize_privileges(self.new_user_data["privileges"])
        with rx.session() as session:
            self._ensure_role(session, role, privileges, overwrite=True)
            session.commit()
            self._load_roles_cache(session)
            
        return rx.toast(f"Plantilla de rol {role} actualizada.", duration=3000)

    @rx.event
    def save_user(self):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para gestionar usuarios.", duration=3000)
            
        username = self.new_user_data["username"].lower().strip()
        if not username:
            return rx.toast("El nombre de usuario no puede estar vac¡o.", duration=3000)
        role_name = (self.new_user_data.get("role") or "").strip()
        if not role_name:
            return rx.toast("Debe asignar un rol al usuario.", duration=3000)
            
        self.new_user_data["privileges"] = self._normalize_privileges(
            self.new_user_data["privileges"]
        )

        with rx.session() as session:
            role = self._get_role_by_name(session, role_name)
            # CASO 1: El rol no existe -> Lo creamos nuevo con los permisos del form
            if not role:
                role = self._ensure_role(
                    session,
                    role_name,
                    self.new_user_data["privileges"],
                    overwrite=True,
                )
            # CASO 2: El rol YA existe y NO es Superadmin -> Actualizamos sus permisos
            # Esto permite redefinir qué puede hacer un 'Cajero' o 'Admin' desde la UI
            elif role.name != "Superadmin":
                role = self._ensure_role(
                    session,
                    role_name,
                    self.new_user_data["privileges"],
                    overwrite=True, # <--- La clave: fuerza la actualización en la DB
                )
            if self.editing_user:
                # Actualizar usuario existente
                user_to_update = session.exec(
                    select(UserModel).where(UserModel.username == self.editing_user["username"])
                ).first()
                
                if not user_to_update:
                    return rx.toast("Usuario a editar no encontrado.", duration=3000)
                    
                if self.new_user_data["password"]:
                    password = self.new_user_data["password"]
                    if len(password) < 6:
                        return rx.toast(
                            "La contraseña debe tener al menos 6 caracteres.",
                            duration=3000,
                        )
                    if password.lower() == username:
                        return rx.toast(
                            "La contraseña no puede ser igual al usuario.",
                            duration=3000,
                        )
                    if password != self.new_user_data["confirm_password"]:
                        return rx.toast(
                            "Las contrase¤as no coinciden.", duration=3000
                        )
                    password_hash = bcrypt.hashpw(
                        password.encode(), bcrypt.gensalt()
                    ).decode()
                    user_to_update.password_hash = password_hash
                    
                user_to_update.role_id = role.id
                
                session.add(user_to_update)
                session.commit()
                self._load_roles_cache(session)
                
                self.hide_user_form()
                self.load_users()
                return rx.toast(f"Usuario {username} actualizado.", duration=3000)
            else:
                # Crear nuevo usuario
                existing_user = session.exec(
                    select(UserModel).where(UserModel.username == username)
                ).first()
                
                if existing_user:
                    return rx.toast("El nombre de usuario ya existe.", duration=3000)
                password = self.new_user_data["password"]
                if not password:
                    return rx.toast(
                        "La contrase¤a no puede estar vac¡a.", duration=3000
                    )
                if len(password) < 6:
                    return rx.toast(
                        "La contraseña debe tener al menos 6 caracteres.",
                        duration=3000,
                    )
                if password.lower() == username:
                    return rx.toast(
                        "La contraseña no puede ser igual al usuario.",
                        duration=3000,
                    )
                if password != self.new_user_data["confirm_password"]:
                    return rx.toast("Las contrase¤as no coinciden.", duration=3000)

                password_hash = bcrypt.hashpw(
                    password.encode(), bcrypt.gensalt()
                ).decode()
                
                new_user = UserModel(
                    username=username,
                    password_hash=password_hash,
                    role_id=role.id,
                )
                session.add(new_user)
                session.commit()
                self._load_roles_cache(session)
                
                self.hide_user_form()
                self.load_users()
                return rx.toast(f"Usuario {username} creado.", duration=3000)

    @rx.event
    def delete_user(self, username: str):
        if not self.current_user["privileges"]["manage_users"]:
            return rx.toast("No tiene permisos para eliminar usuarios.", duration=3000)
        if username == self.current_user["username"]:
            return rx.toast("No puedes eliminar tu propio usuario.", duration=3000)
            
        with rx.session() as session:
            user = session.exec(
                select(UserModel)
                .where(UserModel.username == username)
                .options(selectinload(UserModel.role))
            ).first()
            
            if not user:
                return rx.toast(f"Usuario {username} no encontrado.", duration=3000)
            role_name = (user.role.name if user.role else "").strip().lower()
            if role_name == "superadmin":
                return rx.toast("No se puede eliminar al superadmin.", duration=3000)
            session.delete(user)
            session.commit()
            self.load_users()
            return rx.toast(f"Usuario {username} eliminado.", duration=3000)
                
        return rx.toast(f"Usuario {username} no encontrado.", duration=3000)
