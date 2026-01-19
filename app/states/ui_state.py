import reflex as rx
from typing import List, Dict, Any
from .mixin_state import MixinState

# Mapeo de rutas a páginas
ROUTE_TO_PAGE = {
    "/": "Ingreso",
    "/ingreso": "Ingreso",
    "/venta": "Punto de Venta",
    "/caja": "Gestion de Caja",
    "/clientes": "Clientes",
    "/cuentas": "Cuentas Corrientes",
    "/inventario": "Inventario",
    "/historial": "Historial",
    "/servicios": "Servicios",
    "/configuracion": "Configuracion",
}

PAGE_TO_ROUTE = {
    "Ingreso": "/ingreso",
    "Punto de Venta": "/venta",
    "Gestion de Caja": "/caja",
    "Clientes": "/clientes",
    "Cuentas Corrientes": "/cuentas",
    "Inventario": "/inventario",
    "Historial": "/historial",
    "Servicios": "/servicios",
    "Configuracion": "/configuracion",
}


class UIState(MixinState):
    sidebar_open: bool = True
    current_page: str = "Ingreso"
    config_active_tab: str = "usuarios"

    @rx.event
    def sync_page_from_route(self):
        """Sincroniza current_page basándose en la ruta actual."""
        route = self.router.url.path
        page = ROUTE_TO_PAGE.get(route, "Ingreso")
        if self._can_access_page(page):
            self.current_page = page
        elif self.allowed_pages:
            self.current_page = self.allowed_pages[0]

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
        if self._can_access_page(self.current_page):
            return self.current_page
        if self.allowed_pages:
            return self.allowed_pages[0]
        return self.current_page

    @rx.event
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open

    @rx.event
    def set_page(self, page: str):
        if not self._can_access_page(page):
            return rx.toast("No tiene permisos para acceder a este modulo.", duration=3000)
        
        previous_page = self.current_page
        self.current_page = page
        
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
    def set_config_active_tab(self, tab: str):
        self.config_active_tab = tab

    def _navigation_items_config(self) -> List[Dict[str, str]]:
        return [
            {"label": "Ingreso", "icon": "arrow-down-to-line", "page": "Ingreso", "route": "/ingreso"},
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
            {"label": "Servicios", "icon": "briefcase", "page": "Servicios", "route": "/servicios"},
            {"label": "Configuracion", "icon": "settings", "page": "Configuracion", "route": "/configuracion"},
        ]

    def _page_permission_map(self) -> Dict[str, str]:
        return {
            "Ingreso": "view_ingresos",
            "Punto de Venta": "view_ventas",
            "Gestion de Caja": "view_cashbox",
            "Clientes": "view_clientes",
            "Cuentas Corrientes": "view_cuentas",
            "Inventario": "view_inventario",
            "Historial": "view_historial",
            "Servicios": "view_servicios",
            "Configuracion": "manage_config",
        }

    def _can_access_page(self, page: str) -> bool:
        required = self._page_permission_map().get(page)
        if not required:
            return True
        # Asume que current_user esta disponible en self (desde AuthState)
        if hasattr(self, "current_user"):
            return bool(self.current_user["privileges"].get(required))
        return False
