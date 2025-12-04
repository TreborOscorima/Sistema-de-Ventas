import reflex as rx
from typing import List, Dict, Any
from .mixin_state import MixinState

class UIState(MixinState):
    sidebar_open: bool = True
    current_page: str = "Ingreso"
    config_active_tab: str = "usuarios"

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
        
        # Cross-module logic (assumes methods/attrs exist on the main State)
        if page == "Venta" and previous_page != "Venta":
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
            {"label": "Ingreso", "icon": "arrow-down-to-line", "page": "Ingreso"},
            {"label": "Venta", "icon": "arrow-up-from-line", "page": "Venta"},
            {
                "label": "Gestion de Caja",
                "icon": "wallet",
                "page": "Gestion de Caja",
            },
            {"label": "Inventario", "icon": "boxes", "page": "Inventario"},
            {"label": "Historial", "icon": "history", "page": "Historial"},
            {"label": "Servicios", "icon": "briefcase", "page": "Servicios"},
            {"label": "Configuracion", "icon": "settings", "page": "Configuracion"},
        ]

    def _page_permission_map(self) -> Dict[str, str]:
        return {
            "Ingreso": "view_ingresos",
            "Venta": "view_ventas",
            "Gestion de Caja": "view_cashbox",
            "Inventario": "view_inventario",
            "Historial": "view_historial",
            "Servicios": "view_servicios",
            "Configuracion": "manage_users",
        }

    def _can_access_page(self, page: str) -> bool:
        required = self._page_permission_map().get(page)
        if not required:
            return True
        # Assumes current_user is available on self (from AuthState)
        if hasattr(self, "current_user"):
            return bool(self.current_user["privileges"].get(required))
        return False
