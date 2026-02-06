import reflex as rx
from typing import List, Dict, Any
from .mixin_state import MixinState

# Mapeo de rutas a páginas
ROUTE_TO_PAGE = {
    "/": "Ingreso",
    "/dashboard": "Dashboard",
    "/ingreso": "Ingreso",
    "/compras": "Compras",
    "/venta": "Punto de Venta",
    "/caja": "Gestion de Caja",
    "/clientes": "Clientes",
    "/cuentas": "Cuentas Corrientes",
    "/inventario": "Inventario",
    "/historial": "Historial",
    "/reportes": "Reportes",
    "/servicios": "Servicios",
    "/configuracion": "Configuracion",
}

PAGE_TO_ROUTE = {
    "Dashboard": "/dashboard",
    "Ingreso": "/ingreso",
    "Compras": "/compras",
    "Punto de Venta": "/venta",
    "Gestion de Caja": "/caja",
    "Clientes": "/clientes",
    "Cuentas Corrientes": "/cuentas",
    "Inventario": "/inventario",
    "Historial": "/historial",
    "Reportes": "/reportes",
    "Servicios": "/servicios",
    "Configuracion": "/configuracion",
}


class UIState(MixinState):
    sidebar_open: bool = True
    current_page: str = ""  # Vacío inicialmente, se setea según privilegios
    pending_page: str = rx.SessionStorage("")  # Selección inmediata por pestaña
    config_active_tab: str = "usuarios"

    @rx.event
    def sync_page_from_route(self):
        """Sincroniza current_page basándose en la ruta actual y privilegios."""
        route = self.router.url.path
        page = ROUTE_TO_PAGE.get(route)
        
        # Si la ruta tiene una página mapeada y el usuario puede accederla
        if page and self._can_access_page(page):
            self.current_page = page
            self.pending_page = ""
        # Si no, usar el primer módulo permitido
        elif self.allowed_pages:
            self.current_page = self.allowed_pages[0]
            self.pending_page = ""
        # Fallback si no hay páginas permitidas
        else:
            self.current_page = "Ingreso"
            self.pending_page = ""

    @rx.var
    def navigation_items(self) -> List[Dict[str, str]]:
        return [
            item
            for item in self._navigation_items_config()
            if self._can_access_page(item["page"])
        ]

    @rx.var
    def allowed_pages(self) -> List[str]:
        return [item["page"] for item in self.navigation_items]

    @rx.var
    def active_page(self) -> str:
        # Prioriza selección pendiente para que el sidebar reaccione inmediatamente.
        pending = (self.pending_page or "").strip()
        route = ""
        try:
            route = self.router.url.path
        except Exception:
            route = ""
        route_page = ROUTE_TO_PAGE.get(route) if route else None
        if pending and self._can_access_page(pending) and route_page != pending:
            return pending

        # Luego prioriza la ruta actual.
        if route_page and self._can_access_page(route_page):
            return route_page

        # Fallback a current_page si es accesible.
        if self.current_page and self._can_access_page(self.current_page):
            return self.current_page

        # Si no, usar el primero permitido.
        if self.allowed_pages:
            return self.allowed_pages[0]
        return "Ingreso"

    @rx.event
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    @rx.event
    def set_page(self, page: str):
        if not self._can_access_page(page):
            return rx.toast("No tiene permisos para acceder a este modulo.", duration=3000)
        
        previous_page = self.current_page
        self.current_page = page
        self.pending_page = page
        
        # Logica entre modulos (asume metodos/attrs en el State principal)
        if page == "Punto de Venta" and previous_page != "Punto de Venta":
            if hasattr(self, "_reset_sale_form"):
                self._reset_sale_form()
            if hasattr(self, "reservation_payment_routed") and not self.reservation_payment_routed:
                if hasattr(self, "reservation_payment_id"):
                    self.reservation_payment_id = ""
                if hasattr(self, "reservation_payment_amount"):
                    self.reservation_payment_amount = ""
        
        if page != "Servicios":
            if hasattr(self, "service_active_tab"):
                self.service_active_tab = "campo"
                
        if hasattr(self, "reservation_payment_routed"):
            self.reservation_payment_routed = False

    @rx.event
    def set_pending_page(self, page: str):
        if not self._can_access_page(page):
            return
        self.pending_page = page

    @rx.event
    def set_config_active_tab(self, tab: str):
        self.config_active_tab = tab

    @rx.event
    def go_to_subscription(self):
        self.config_active_tab = "suscripcion"
        return rx.redirect("/configuracion")

    def _navigation_items_config(self) -> List[Dict[str, str]]:
        return [
            {"label": "Dashboard", "icon": "layout-dashboard", "page": "Dashboard", "route": "/dashboard"},
            {"label": "Ingreso", "icon": "arrow-down-to-line", "page": "Ingreso", "route": "/ingreso"},
            {"label": "Compras", "icon": "file-text", "page": "Compras", "route": "/compras"},
            {"label": "Punto de Venta", "icon": "arrow-up-from-line", "page": "Punto de Venta", "route": "/venta"},
            {
                "label": "Gestion de Caja",
                "icon": "wallet",
                "page": "Gestion de Caja",
                "route": "/caja",
            },
            {"label": "Clientes", "icon": "users", "page": "Clientes", "route": "/clientes"},
            {"label": "Cuentas", "icon": "banknote", "page": "Cuentas Corrientes", "route": "/cuentas"},
            {"label": "Inventario", "icon": "boxes", "page": "Inventario", "route": "/inventario"},
            {"label": "Historial", "icon": "history", "page": "Historial", "route": "/historial"},
            {"label": "Reportes", "icon": "file-chart-column", "page": "Reportes", "route": "/reportes"},
            {"label": "Servicios", "icon": "calendar-days", "page": "Servicios", "route": "/servicios"},
            {"label": "Configuracion", "icon": "settings", "page": "Configuracion", "route": "/configuracion"},
        ]

    def _page_permission_map(self) -> Dict[str, str]:
        return {
            "Dashboard": "",  # Accesible para todos
            "Ingreso": "view_ingresos",
            "Compras": "view_compras",
            "Punto de Venta": "view_ventas",
            "Gestion de Caja": "view_cashbox",
            "Clientes": "view_clientes",
            "Cuentas Corrientes": "view_cuentas",
            "Inventario": "view_inventario",
            "Historial": "view_historial",
            "Reportes": "export_data",
            "Servicios": "view_servicios",
            "Configuracion": "manage_config",
        }

    def _can_access_page(self, page: str) -> bool:
        if page == "Clientes":
            return bool(self.can_view_clientes)
        if page == "Cuentas Corrientes":
            return bool(self.can_view_cuentas)
        if page == "Servicios":
            return bool(self.can_view_servicios)
        required = self._page_permission_map().get(page)
        if not required:
            return True
        # Asume que current_user esta disponible en self (desde AuthState)
        if hasattr(self, "current_user"):
            privileges = self.current_user["privileges"]
            if required == "view_compras":
                return bool(privileges.get("view_compras") or privileges.get("view_ingresos"))
            return bool(privileges.get(required))
        return False
