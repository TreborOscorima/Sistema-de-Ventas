import reflex as rx
from typing import List, Dict, Any
from urllib.parse import parse_qs
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

CONFIG_TABS = {"empresa", "sucursales", "usuarios", "monedas", "unidades", "pagos", "suscripcion"}
CASH_TABS = {"resumen", "movimientos"}
SERVICES_TABS = {"campo", "precios_campo"}


# Valores por defecto para tabs (cuando no hay query param)
_CONFIG_DEFAULT = "usuarios"
_CASH_DEFAULT = "resumen"
_SERVICES_DEFAULT = "campo"


class UIState(MixinState):
    sidebar_open: bool = True
    current_page: str = ""  # Vacío inicialmente, se setea según privilegios
    current_active_item: str = rx.SessionStorage("")
    # Compatibilidad con sesiones previas; ya no se usa para evitar eventos extra en navegación.
    pending_page: str = rx.SessionStorage("")
    # LEGACY: solo se conservan para set programático (go_to_subscription, etc.)
    # Las páginas leen el tab del @rx.var que deriva de router.page.params
    config_active_tab: str = _CONFIG_DEFAULT

    # ---- Computed vars para tabs desde query params (sin roundtrip WS) ----
    @rx.var(cache=True)
    def config_tab(self) -> str:
        """Tab activo de Configuración, derivado de ?tab= en la URL."""
        tab = self._safe_query_tab()
        return tab if tab in CONFIG_TABS else _CONFIG_DEFAULT

    @rx.var(cache=True)
    def cash_tab(self) -> str:
        """Tab activo de Caja, derivado de ?tab= en la URL."""
        tab = self._safe_query_tab()
        return tab if tab in CASH_TABS else _CASH_DEFAULT

    @rx.var(cache=True)
    def service_tab(self) -> str:
        """Tab activo de Servicios, derivado de ?tab= en la URL."""
        tab = self._safe_query_tab()
        return tab if tab in SERVICES_TABS else _SERVICES_DEFAULT

    def _safe_query_tab(self) -> str:
        """Lee el param 'tab' de la URL actual de forma segura."""
        try:
            qp = self.router.url.query_parameters
            v = qp.get("tab", "") if isinstance(qp, dict) else ""
            return str(v or "").strip().lower()
        except Exception:
            return ""

    @rx.event
    def sync_page_from_route(self):
        """Sincroniza current_page basándose en la ruta actual y privilegios."""
        route = self._normalized_route()
        page = ROUTE_TO_PAGE.get(route)
        
        # Si la ruta tiene una página mapeada y el usuario puede accederla
        if page and self._can_access_page(page):
            self._apply_page_state(page)
        # Si no, usar el primer módulo permitido
        elif self.allowed_pages:
            self._apply_page_state(self.allowed_pages[0])
        # Fallback si no hay páginas permitidas
        else:
            self.current_page = "Ingreso"
            self.current_active_item = "Ingreso"
            self.pending_page = ""

    @rx.var(cache=True)
    def navigation_items(self) -> List[Dict[str, str]]:
        return [
            item
            for item in self._navigation_items_config()
            if self._can_access_page(item["page"])
        ]

    @rx.var(cache=True)
    def allowed_pages(self) -> List[str]:
        return [item["page"] for item in self.navigation_items]

    @rx.var(cache=True)
    def active_page(self) -> str:
        # Priorizar la ruta actual evita esperar un evento de click para pintar activo.
        route_page = ROUTE_TO_PAGE.get(self._normalized_route())
        if route_page and self._can_access_page(route_page):
            return route_page

        # Sidebar optimista: fallback al estado local.
        if self.current_active_item and self._can_access_page(self.current_active_item):
            return self.current_active_item

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
        self._apply_page_state(page)

    @rx.event
    def navigate_to_page(self, page: str, route: str):
        self.set_page(page)
        target_route = (route or "").strip() or PAGE_TO_ROUTE.get(page, "/dashboard")
        return rx.redirect(target_route)

    @rx.event
    def set_pending_page(self, page: str):
        # Conservado por compatibilidad. No-op para reducir eventos durante navegación.
        return

    @rx.event
    def set_config_active_tab(self, tab: str):
        self.config_active_tab = tab

    @rx.event
    def go_to_subscription(self):
        return rx.redirect("/configuracion?tab=suscripcion")

    def _normalized_route(self) -> str:
        route = ""
        try:
            route = getattr(self.router.url, "path", "") or ""
        except Exception:
            route = ""
        route = (route or "").strip() or "/"
        if route != "/" and route.endswith("/"):
            route = route.rstrip("/")
        return route

    def _router_query(self) -> str:
        query = ""
        try:
            query = getattr(self.router.url, "query", "") or ""
        except Exception:
            query = ""
        if not query:
            try:
                router = getattr(self, "router", None)
                raw_url = str(getattr(router, "url", ""))
                if "?" in raw_url:
                    query = raw_url.split("?", 1)[1]
            except Exception:
                query = ""
        return (query or "").strip()

    def _query_params(self) -> Dict[str, list[str]]:
        query = self._router_query()
        if not query:
            return {}
        return parse_qs(query.lstrip("?"))

    def _query_tab(self) -> str:
        params = self._query_params()
        tab = (params.get("tab") or [""])[0]
        return (tab or "").strip().lower()

    def _apply_route_tab_state(self, page: str):
        """Ejecuta side-effects basados en el tab del query param.
        
        Ya NO muta config_active_tab, cash_active_tab ni service_active_tab
        porque las páginas ahora leen el tab directamente de router.page.params
        vía computed vars (config_tab, cash_tab, service_tab).
        """
        tab = self._query_tab()
        if not tab:
            return

        if page == "Servicios" and tab == "precios_campo":
            if hasattr(self, "load_field_prices"):
                self.load_field_prices()
            return

        if page == "Gestion de Caja" and tab in CASH_TABS:
            if hasattr(self, "_refresh_cashbox_caches"):
                self._refresh_cashbox_caches()
            return

    def _apply_page_state(self, page: str):
        previous_page = self.current_page
        # Solo mutar si realmente cambió (evita deltas innecesarios)
        if self.current_page != page:
            self.current_page = page
        if self.current_active_item != page:
            self.current_active_item = page
        if self.pending_page:
            self.pending_page = ""

        # Logica entre modulos (asume metodos/attrs en el State principal).
        if page == "Punto de Venta" and previous_page != "Punto de Venta":
            if hasattr(self, "_reset_sale_form"):
                self._reset_sale_form()
            if (
                hasattr(self, "reservation_payment_routed")
                and not self.reservation_payment_routed
            ):
                if hasattr(self, "reservation_payment_id"):
                    self.reservation_payment_id = ""
                if hasattr(self, "reservation_payment_amount"):
                    self.reservation_payment_amount = ""

        if page != "Servicios" and hasattr(self, "service_active_tab"):
            self.service_active_tab = "campo"

        if hasattr(self, "reservation_payment_routed"):
            self.reservation_payment_routed = False

        self._apply_route_tab_state(page)

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
