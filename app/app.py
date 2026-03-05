import os

import reflex as rx
import app.models  # Importar modelos para que Reflex detecte las tablas

# Evitar warnings de metadata duplicada en Reflex/SQLAlchemy.
rx.ModelRegistry.models = {rx.Model}
rx.ModelRegistry._metadata = rx.Model.metadata
from app.state import State
from app.components.sidebar import sidebar
from app.pages.ingreso import ingreso_page
from app.pages.compras import compras_page
from app.pages.venta import venta_page
from app.pages.inventario import inventario_page
from app.pages.caja import cashbox_page
from app.pages.historial import historial_page
from app.pages.configuracion import configuracion_page
from app.pages.cambiar_contrasena import cambiar_contrasena_page
from app.pages.login import login_page
from app.pages.periodo_prueba_finalizado import periodo_prueba_finalizado_page
from app.pages.cuenta_suspendida import cuenta_suspendida_page
from app.pages.registro import registro_page
from app.pages.marketing import marketing_page
from app.pages.terminos import terminos_page
from app.pages.privacidad import privacidad_page
from app.pages.cookies import cookies_page
from app.pages.servicios import servicios_page
from app.pages.cuentas import cuentas_page
from app.pages.clientes import clientes_page
from app.pages.dashboard import dashboard_page
from app.pages.reportes import reportes_page
from app.pages.owner import owner_page, owner_login_page
from app.components.notification import NotificationHolder
from app.api import health_app

APP_SURFACE = (os.getenv("APP_SURFACE") or "all").strip().lower()
if APP_SURFACE not in {"all", "landing", "app", "owner"}:
    APP_SURFACE = "all"

PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "https://tuwayki.app").strip().rstrip("/")
LANDING_TITLE = "TUWAYKIAPP | Sistema de Ventas para tiendas, servicios y reservas"
LANDING_DESCRIPTION = (
    "Centraliza ventas, caja, inventario, clientes y reservas en una sola plataforma SaaS "
    "multiempresa, segura y lista para escalar."
)
LANDING_IMAGE = f"{PUBLIC_SITE_URL}/dashboard-hero-real.png"


def _landing_meta(canonical_url: str, *, indexable: bool = True) -> list[dict | rx.Component]:
    return [
        rx.el.link(rel="canonical", href=canonical_url),
        {"name": "robots", "content": "index,follow" if indexable else "noindex,follow"},
        {"property": "og:type", "content": "website"},
        {"property": "og:title", "content": LANDING_TITLE},
        {"property": "og:description", "content": LANDING_DESCRIPTION},
        {"property": "og:url", "content": canonical_url},
        {"property": "og:image", "content": LANDING_IMAGE},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": LANDING_TITLE},
        {"name": "twitter:description", "content": LANDING_DESCRIPTION},
        {"name": "twitter:image", "content": LANDING_IMAGE},
    ]


def cashbox_banner() -> rx.Component:
    """Banner de advertencia que solicita apertura de caja cuando está cerrada."""
    return rx.cond(
        State.cashbox_is_open_cached,
        rx.fragment(),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("triangle-alert", class_name="h-5 w-5 text-amber-600"),
                    rx.el.div(
                        rx.el.p(
                            "Apertura de caja requerida",
                            class_name="font-semibold text-amber-800",
                        ),
                        rx.el.p(
                            "Ingresa el monto inicial para comenzar la jornada. Sin apertura no podrás vender ni gestionar la caja.",
                            class_name="text-sm text-amber-700",
                        ),
                        class_name="flex flex-col gap-1",
                    ),
                    class_name="flex items-start gap-3",
                ),
                rx.el.form(
                    rx.el.input(
                        name="amount",
                        type="number",
                        step="0.01",
                        placeholder="Caja inicial (ej: 150.00)",
                        class_name="w-full md:w-52 h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
                    ),
                    rx.el.button(
                        rx.icon("play", class_name="h-4 w-4"),
                        "Aperturar caja",
                        type="submit",
                        class_name="flex items-center gap-2 h-10 px-4 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700",
                    ),
                    on_submit=State.handle_cashbox_form_submit,
                    class_name="flex flex-col md:flex-row items-stretch md:items-center gap-3",
                ),
                class_name="flex flex-col md:flex-row justify-between gap-4",
            ),
            class_name="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl shadow-sm",
        ),
    )


def _toast_provider() -> rx.Component:
    """Proveedor global de notificaciones toast (posición, estilos y duración)."""
    return rx.toast.provider(
        position="bottom-center",
        close_button=True,
        rich_colors=True,
        toast_options=rx.toast.options(
            duration=4000,
            style={
                "background": "#111827",
                "color": "white",
                "fontSize": "18px",
                "padding": "18px 28px",
                "borderRadius": "14px",
                "boxShadow": "0 25px 60px rgba(15,23,42,0.35)",
                "border": "1px solid rgba(255,255,255,0.15)",
                "textAlign": "center",
            },
        ),
    )


def _icon_tooltip_styles() -> str:
    """Estilo global para tooltips de iconos (solo icon-only buttons/links)."""
    return """
    #twk-global-icon-tooltip {
        position: fixed;
        z-index: 9999;
        pointer-events: none;
        background: #0f172a;
        color: #ffffff;
        padding: 6px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        line-height: 1.2;
        letter-spacing: 0.01em;
        white-space: nowrap;
        box-shadow: 0 14px 28px rgba(15, 23, 42, 0.35);
        opacity: 0;
        transform: translate3d(-9999px, -9999px, 0) scale(0.96);
        transition: opacity 0.12s ease, transform 0.12s ease;
    }
    #twk-global-icon-tooltip[data-show="true"] {
        opacity: 1;
    }
    #twk-global-icon-tooltip::after {
        content: "";
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
    }
    #twk-global-icon-tooltip[data-placement="top"]::after {
        bottom: -5px;
        border-width: 5px 5px 0 5px;
        border-style: solid;
        border-color: #0f172a transparent transparent transparent;
    }
    #twk-global-icon-tooltip[data-placement="bottom"]::after {
        top: -5px;
        border-width: 0 5px 5px 5px;
        border-style: solid;
        border-color: transparent transparent #0f172a transparent;
    }
    """


def _icon_tooltip_script() -> str:
    """Convierte title/aria-label de iconos a tooltip visual notorio y consistente."""
    return """
    (function () {
        if (window.__twkGlobalIconTooltipInit) return;
        window.__twkGlobalIconTooltipInit = true;

        const TARGET_SELECTOR = "button, a, [role='button']";
        let tooltip = null;
        let activeEl = null;
        let lastMoveAt = 0;

        function ensureTooltip() {
            if (tooltip) return tooltip;
            tooltip = document.createElement("div");
            tooltip.id = "twk-global-icon-tooltip";
            tooltip.setAttribute("data-show", "false");
            tooltip.setAttribute("data-placement", "top");
            document.body.appendChild(tooltip);
            return tooltip;
        }

        function isIconOnly(el) {
            if (!el || !el.querySelector) return false;
            if (el.hasAttribute("data-disable-global-tooltip")) return false;
            if (el.closest("[data-radix-tooltip-trigger]")) return false;
            const text = (el.textContent || "").replace(/\\s+/g, " ").trim();
            if (text.length > 0) return false;
            return Boolean(el.querySelector("svg, [class*='lucide'], i"));
        }

        function normalize(el) {
            if (!el || !el.dataset) return;
            if (el.dataset.twkTooltipReady === "1") return;
            if (!isIconOnly(el)) return;
            const rawTitle = (el.getAttribute("title") || "").trim();
            const rawAria = (el.getAttribute("aria-label") || "").trim();
            const normalizedRaw = normalizeTechnicalLabel(rawTitle || rawAria);
            const inferred = inferLabelFromIcon(el);
            const label = normalizedRaw || rawTitle || rawAria || inferred;
            if (!label) return;

            el.dataset.twkTooltip = label;
            el.dataset.twkTooltipReady = "1";
            if (!rawAria) {
                el.setAttribute("aria-label", label);
            }

            // Evita doble tooltip (nativo + custom).
            if (rawTitle) {
                el.dataset.twkNativeTitle = rawTitle;
                el.removeAttribute("title");
            }
        }

        function normalizeTechnicalLabel(rawLabel) {
            if (!rawLabel) return "";
            const canonical = String(rawLabel).toLowerCase().replace(/[^a-z0-9]/g, "");
            const labelMap = {
                trash2: "Eliminar",
                trash: "Eliminar",
                delete: "Eliminar",
                remove: "Eliminar",
                pencil: "Editar",
                edit: "Editar",
                eye: "Visualizar",
                view: "Visualizar",
                printer: "Imprimir",
                print: "Imprimir",
                download: "Descargar",
                upload: "Subir",
                search: "Buscar",
                close: "Cerrar",
                x: "Cerrar",
                refreshcw: "Actualizar",
                refreshccw: "Actualizar",
                rotateccw: "Reiniciar",
                creditcard: "Metodo de pago",
                wallet: "Caja",
                users: "Usuarios",
                user: "Usuario",
                settings: "Configurar",
                filter: "Filtrar",
                menu: "Menu",
            };
            return labelMap[canonical] || "";
        }

        function inferLabelFromIcon(el) {
            const icon = el.querySelector("svg");
            if (!icon) return "";

            const classes = Array.from(icon.classList || []);
            const iconClass = classes.find((cls) => cls.startsWith("lucide-"));
            if (!iconClass) return "";
            const iconName = iconClass.replace("lucide-", "").toLowerCase();
            const canonical = iconName.replace(/[^a-z0-9]/g, "");

            const mapByName = {
                "pencil": "Editar",
                "square-pen": "Editar",
                "trash": "Eliminar",
                "trash-2": "Eliminar",
                "eye": "Visualizar",
                "eye-off": "Ocultar",
                "file-text": "Documento",
                "file-down": "Descargar archivo",
                "printer": "Imprimir",
                "plus": "Agregar",
                "minus": "Quitar",
                "x": "Cerrar",
                "x-circle": "Cerrar",
                "chevron-left": "Anterior",
                "chevron-right": "Siguiente",
                "download": "Descargar",
                "upload": "Subir",
                "refresh-cw": "Actualizar",
                "refresh-ccw": "Actualizar",
                "rotate-ccw": "Reiniciar",
                "repeat": "Repetir",
                "settings": "Configurar",
                "sliders-horizontal": "Ajustes",
                "filter": "Filtrar",
                "search": "Buscar",
                "calendar": "Calendario",
                "calendar-check": "Confirmar",
                "calendar-plus": "Nueva reserva",
                "wallet": "Caja",
                "credit-card": "Metodo de pago",
                "users": "Usuarios",
                "user": "Usuario",
                "history": "Historial",
                "log-in": "Iniciar sesion",
                "log-out": "Cerrar sesion",
                "lock": "Bloquear",
                "unlock": "Desbloquear",
                "info": "Informacion",
                "circle-help": "Ayuda",
                "play": "Iniciar",
                "save": "Guardar",
                "check": "Confirmar",
                "circle-check": "Confirmar",
                "badge-check": "Confirmar",
                "ban": "Cancelar",
                "menu": "Menu",
                "panel-left-close": "Ocultar menu",
            };
            if (mapByName[iconName]) return mapByName[iconName];

            const mapByCanonical = {
                trash2: "Eliminar",
                refreshcw: "Actualizar",
                refreshccw: "Actualizar",
                rotateccw: "Reiniciar",
                slidershorizontal: "Ajustes",
                creditcard: "Metodo de pago",
                filetext: "Documento",
                filedown: "Descargar archivo",
                eyeoff: "Ocultar",
                xcircle: "Cerrar",
                checkcheck: "Confirmar",
                circlecheck: "Confirmar",
                badgecheck: "Confirmar",
                logout: "Cerrar sesion",
                login: "Iniciar sesion",
                panelleftclose: "Ocultar menu",
                chevronleft: "Anterior",
                chevronright: "Siguiente",
                calendarplus: "Nueva reserva",
                calendarcheck: "Confirmar",
                circlehelp: "Ayuda",
            };
            if (mapByCanonical[canonical]) return mapByCanonical[canonical];

            if (canonical.includes("trash")) return "Eliminar";
            if (canonical.includes("pencil") || canonical.includes("edit")) return "Editar";
            if (canonical.includes("print")) return "Imprimir";
            if (canonical.includes("download")) return "Descargar";
            if (canonical.includes("search")) return "Buscar";
            if (canonical.includes("close") || canonical === "x") return "Cerrar";

            return iconName
                .replace(/-/g, " ")
                .replace(/\\b\\w/g, (match) => match.toUpperCase());
        }

        function computePlacement(el, tip) {
            const rect = el.getBoundingClientRect();
            const tipRect = tip.getBoundingClientRect();
            const margin = 10;
            let left = rect.left + rect.width / 2 - tipRect.width / 2;
            left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));

            let top = rect.top - tipRect.height - margin;
            let placement = "top";
            if (top < 8) {
                top = rect.bottom + margin;
                placement = "bottom";
            }
            return { left, top, placement };
        }

        function positionTooltip(el) {
            if (!tooltip || !el) return;
            const { left, top, placement } = computePlacement(el, tooltip);
            tooltip.style.left = left + "px";
            tooltip.style.top = top + "px";
            tooltip.setAttribute("data-placement", placement);
            tooltip.style.transform = "translate3d(0,0,0) scale(1)";
        }

        function showFor(el) {
            normalize(el);
            const label = el && el.dataset ? (el.dataset.twkTooltip || "").trim() : "";
            if (!label) return;
            ensureTooltip();
            tooltip.textContent = label;
            tooltip.setAttribute("data-show", "true");
            activeEl = el;
            positionTooltip(el);
        }

        function hideTooltip() {
            if (!tooltip) return;
            tooltip.setAttribute("data-show", "false");
            tooltip.style.transform = "translate3d(-9999px,-9999px,0) scale(0.96)";
            activeEl = null;
        }

        document.addEventListener("mouseover", function (event) {
            const el = event.target && event.target.closest
                ? event.target.closest(TARGET_SELECTOR)
                : null;
            if (!el) return;
            showFor(el);
        });

        document.addEventListener("mouseout", function (event) {
            if (!activeEl) return;
            const source = event.target && event.target.closest
                ? event.target.closest(TARGET_SELECTOR)
                : null;
            if (!source || source !== activeEl) return;
            if (event.relatedTarget && source.contains(event.relatedTarget)) return;
            hideTooltip();
        });

        document.addEventListener("focusin", function (event) {
            const el = event.target && event.target.closest
                ? event.target.closest(TARGET_SELECTOR)
                : null;
            if (!el) return;
            showFor(el);
        });

        document.addEventListener("focusout", function () {
            hideTooltip();
        });

        window.addEventListener("scroll", function () {
            if (!activeEl || !tooltip) return;
            const now = Date.now();
            if (now - lastMoveAt < 16) return;
            lastMoveAt = now;
            positionTooltip(activeEl);
        }, true);

        window.addEventListener("resize", function () {
            if (!activeEl || !tooltip) return;
            positionTooltip(activeEl);
        });
    })();
    """


def _runtime_sync_script() -> str:
    """Escucha cambios cross-tab y refresca estado en pestañas activas."""
    return """
    (function(){
        if(window.__twkRuntimeSyncAttached) return;
        window.__twkRuntimeSyncAttached = true;
        const KEY = "twk_runtime_sync";
        let lastSeen = "";
        let lastRunAt = 0;

        try {
            lastSeen = localStorage.getItem(KEY) || "";
        } catch(_err) {
            lastSeen = "";
        }

        function triggerRefresh(){
            const now = Date.now();
            if ((now - lastRunAt) < 700) return;
            lastRunAt = now;
            const btn = document.querySelector('[data-twk-runtime-sync=\"1\"]');
            if (btn) btn.click();
        }

        function checkForExternalChange(){
            let current = "";
            try {
                current = localStorage.getItem(KEY) || "";
            } catch(_err) {
                current = "";
            }
            if (!current || current === lastSeen) return;
            lastSeen = current;
            triggerRefresh();
        }

        window.addEventListener("storage", function(event){
            if (!event || event.key !== KEY) return;
            lastSeen = event.newValue || "";
            triggerRefresh();
        });

        window.addEventListener("focus", checkForExternalChange);
        document.addEventListener("visibilitychange", function(){
            if (document.visibilityState === "visible") {
                checkForExternalChange();
            }
        });
    })();
    """


def _content_skeleton() -> rx.Component:
    """Skeleton solo para el área de contenido (sin sidebar)."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(class_name="h-6 w-48 rounded bg-slate-200 animate-pulse"),
            rx.el.div(class_name="h-4 w-32 rounded bg-slate-200/60 animate-pulse mt-2"),
            rx.el.div(
                *[rx.el.div(class_name="h-24 rounded-xl bg-slate-200/40 animate-pulse") for _ in range(3)],
                class_name="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6",
            ),
            rx.el.div(class_name="h-64 rounded-xl bg-slate-200/30 animate-pulse mt-6"),
            class_name="w-full max-w-5xl p-4 sm:p-6",
        ),
        class_name="flex-1 h-full overflow-y-auto",
    )


def authenticated_layout(page_content: rx.Component) -> rx.Component:
    """Layout optimizado para SPA: Sidebar fijo y persistente.

    Los elementos estáticos (sidebar, barra gradiente, toasts) viven
    FUERA de la condición is_hydrated para que React jamás los destruya
    ni recree al navegar entre rutas, eliminando el parpadeo de 3-4 s.
    """
    return rx.el.main(
        # 1. ELEMENTOS ESTÁTICOS: Fuera de la hidratación para evitar
        #    que React los destruya/recree al cambiar de ruta.
        rx.el.style(_icon_tooltip_styles()),
        rx.script(_icon_tooltip_script()),
        rx.el.button(
            "sync",
            on_click=State.handle_cross_tab_runtime_sync,
            custom_attrs={
                "data-twk-runtime-sync": "1",
                "aria-hidden": "true",
                "tabindex": "-1",
            },
            type="button",
            class_name="hidden",
        ),
        rx.script(_runtime_sync_script()),
        rx.el.div(
            class_name=(
                "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
            ),
        ),
        sidebar(),
        _toast_provider(),
        NotificationHolder(),

        # 2. ÁREA DE CONTENIDO DINÁMICO
        rx.el.div(
            rx.cond(
                State.is_hydrated,
                rx.cond(
                    State.is_authenticated,
                    rx.el.div(
                        rx.cond(State.runtime_ctx_loaded, cashbox_banner(), rx.fragment()),
                        rx.cond(
                            State.navigation_items.length() == 0,
                            rx.el.div(
                                rx.el.h1(
                                    "Acceso restringido",
                                    class_name="text-2xl font-bold text-red-600",
                                ),
                                rx.el.p(
                                    "Tu usuario no tiene modulos habilitados. Solicita permisos al administrador.",
                                    class_name="text-slate-600 mt-2 text-center",
                                ),
                                class_name="flex flex-col items-center justify-center h-full p-6",
                            ),
                            page_content,
                        ),
                        class_name="w-full h-full flex flex-col gap-4 p-4 sm:p-6",
                    ),
                    login_page(),
                ),
                # Skeleton solo en el área de contenido
                _content_skeleton(),
            ),
            class_name=rx.cond(
                State.sidebar_open,
                "h-screen bg-slate-50 overflow-y-auto overscroll-y-contain transition-[margin] duration-300 md:ml-64 xl:ml-72",
                "h-screen bg-slate-50 overflow-y-auto overscroll-y-contain transition-[margin] duration-300",
            ),
            style={"height": "100dvh"},
        ),
        # SIN 'flex' para preservar el block-model y auto-fill del ancho
        class_name="text-slate-900 w-full h-screen",
        style={
            "fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif",
            "height": "100dvh",
        },
    )


def index() -> rx.Component:
    """Página principal - landing de marketing."""
    return marketing_page()


def page_ingreso() -> rx.Component:
    return authenticated_layout(ingreso_page())


def page_compras() -> rx.Component:
    return authenticated_layout(compras_page())


def page_venta() -> rx.Component:
    return authenticated_layout(venta_page())


def page_caja() -> rx.Component:
    return authenticated_layout(cashbox_page())


def page_clientes() -> rx.Component:
    return authenticated_layout(clientes_page())


def page_cuentas() -> rx.Component:
    return authenticated_layout(cuentas_page())


def page_dashboard() -> rx.Component:
    return authenticated_layout(dashboard_page())


def page_reportes() -> rx.Component:
    return authenticated_layout(reportes_page())


def page_inventario() -> rx.Component:
    return authenticated_layout(inventario_page())


def page_historial() -> rx.Component:
    return authenticated_layout(historial_page())


def page_servicios() -> rx.Component:
    return authenticated_layout(servicios_page())


def page_configuracion() -> rx.Component:
    return authenticated_layout(configuracion_page())

def page_cambiar_contrasena() -> rx.Component:
    return cambiar_contrasena_page()

def page_periodo_prueba_finalizado() -> rx.Component:
    return periodo_prueba_finalizado_page()

def page_cuenta_suspendida() -> rx.Component:
    return cuenta_suspendida_page()

def page_registro() -> rx.Component:
    return registro_page()


def page_login() -> rx.Component:
    """Página de login del sistema (superficie app/sys)."""
    return authenticated_layout(rx.fragment())


def page_marketing() -> rx.Component:
    return marketing_page()

def page_terminos() -> rx.Component:
    return terminos_page()

def page_privacidad() -> rx.Component:
    return privacidad_page()

def page_cookies() -> rx.Component:
    return cookies_page()


def page_owner_backoffice() -> rx.Component:
    return owner_page()


app = rx.App(
    theme=rx.theme(appearance="light"),
    api_transformer=health_app,
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
        rx.el.style(
            """
            [data-sonner-toaster][data-x-position='right'][data-y-position='bottom'] {
                display: none !important;
            }

            html, body {
                overflow-x: hidden;
            }

            * {
                -webkit-tap-highlight-color: transparent;
            }

            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(6px); }
                to   { opacity: 1; transform: translateY(0); }
            }
            .fade-in-up {
                animation: fadeInUp 0.3s cubic-bezier(.16,1,.3,1) both;
            }
            """
        ),
        rx.script(
            """
            (function(){
                var K='__sb_scroll',_skip=false;
                // Guardar scroll del sidebar continuamente (fase captura, sobrevive a React)
                document.addEventListener('scroll',function(e){
                    if(!_skip&&e.target&&e.target.id==='sidebar-nav'){
                        sessionStorage.setItem(K,String(e.target.scrollTop));
                    }
                },true);
                // Restaurar al cargar
                window.addEventListener('load',function(){
                    var n=document.getElementById('sidebar-nav');
                    var s=sessionStorage.getItem(K);
                    if(n&&s) n.scrollTop=parseInt(s,10);
                });
                // Observar cuando React reemplaza el contenido del sidebar
                // y restaurar scroll si se reseteo a 0 (no si el usuario scrolleo)
                new MutationObserver(function(){
                    var n=document.getElementById('sidebar-nav');
                    var s=sessionStorage.getItem(K);
                    if(n&&s){
                        var t=parseInt(s,10);
                        if(t>5&&n.scrollTop<5){
                            _skip=true;
                            n.scrollTop=t;
                            setTimeout(function(){_skip=false;},50);
                        }
                    }
                }).observe(document.body,{childList:true,subtree:true});
            })();
            """
        ),
        rx.script(
            """
            (function() {
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        var modalOverlays = document.querySelectorAll('.modal-overlay');
                        if (modalOverlays.length > 0) {
                            modalOverlays[modalOverlays.length - 1].click();
                            return;
                        }

                        var radixOverlay = document.querySelector('[data-radix-dialog-overlay]');
                        if (radixOverlay) {
                            radixOverlay.click();
                            return;
                        }

                        var sidebarOverlay = document.querySelector('.sidebar-overlay');
                        if (sidebarOverlay) {
                            sidebarOverlay.click();
                        }
                    }
                });
            })();
            """
        ),
    ],
)

PRIVATE_META = [{"name": "robots", "content": "noindex,nofollow"}]


def page_owner_login() -> rx.Component:
    return owner_login_page()


def _add_private_page(
    component,
    *,
    route: str,
    title: str,
    on_load=None,
):
    kwargs = {
        "route": route,
        "title": title,
        "meta": PRIVATE_META,
    }
    if on_load is not None:
        kwargs["on_load"] = on_load
    app.add_page(component, **kwargs)


def _register_landing_routes():
    if APP_SURFACE == "landing":
        app.add_page(
            page_marketing,
            route="/",
            title=LANDING_TITLE,
            description=LANDING_DESCRIPTION,
            image=LANDING_IMAGE,
            meta=_landing_meta(f"{PUBLIC_SITE_URL}/", indexable=True),
        )
        # Alias temporal de compatibilidad.
        app.add_page(
            page_marketing,
            route="/home",
            title=LANDING_TITLE,
            description=LANDING_DESCRIPTION,
            image=LANDING_IMAGE,
            meta=_landing_meta(f"{PUBLIC_SITE_URL}/", indexable=False),
        )
    else:
        # Modo all: mantener landing en /home hasta completar migración de dominios.
        app.add_page(
            page_marketing,
            route="/home",
            title=LANDING_TITLE,
            description=LANDING_DESCRIPTION,
            image=LANDING_IMAGE,
            meta=_landing_meta(f"{PUBLIC_SITE_URL}/", indexable=False),
        )

    # Páginas legales públicas (indexables en todas las superficies).
    _legal_indexable = APP_SURFACE == "landing"
    app.add_page(
        page_terminos,
        route="/terminos",
        title="Términos y Condiciones - TUWAYKIAPP",
        description="Términos y condiciones de uso de TUWAYKIAPP.",
        meta=_landing_meta(f"{PUBLIC_SITE_URL}/terminos", indexable=_legal_indexable),
    )
    app.add_page(
        page_privacidad,
        route="/privacidad",
        title="Política de Privacidad - TUWAYKIAPP",
        description="Política de privacidad de TUWAYKIAPP.",
        meta=_landing_meta(f"{PUBLIC_SITE_URL}/privacidad", indexable=_legal_indexable),
    )
    app.add_page(
        page_cookies,
        route="/cookies",
        title="Política de Cookies - TUWAYKIAPP",
        description="Política de cookies de TUWAYKIAPP.",
        meta=_landing_meta(f"{PUBLIC_SITE_URL}/cookies", indexable=_legal_indexable),
    )


def _register_app_routes():
    _add_private_page(
        page_login,
        route="/login",
        title="Iniciar sesión - TUWAYKIAPP",
        on_load=State.page_init_login,
    )
    _add_private_page(
        page_cambiar_contrasena,
        route="/cambiar-clave",
        title="Cambiar Contrasena - TUWAYKIAPP",
        on_load=State.page_init_cambiar_clave,
    )
    _add_private_page(
        page_periodo_prueba_finalizado,
        route="/periodo-prueba-finalizado",
        title="Periodo de Prueba Finalizado - TUWAYKIAPP",
    )
    _add_private_page(
        page_cuenta_suspendida,
        route="/cuenta-suspendida",
        title="Cuenta Suspendida - TUWAYKIAPP",
    )
    _add_private_page(
        page_registro,
        route="/registro",
        title="Registro - TUWAYKIAPP",
    )

    _add_private_page(
        page_ingreso,
        route="/ingreso",
        title="Compras e Ingresos - TUWAYKIAPP",
        on_load=State.page_init_ingreso,
    )
    _add_private_page(
        page_compras,
        route="/compras",
        title="Compras - TUWAYKIAPP",
        on_load=State.page_init_compras,
    )
    _add_private_page(
        page_venta,
        route="/venta",
        title="Venta - TUWAYKIAPP",
        on_load=State.page_init_venta,
    )
    _add_private_page(
        page_caja,
        route="/caja",
        title="Gestión de Caja - TUWAYKIAPP",
        on_load=State.page_init_caja,
    )
    _add_private_page(
        page_clientes,
        route="/clientes",
        title="Clientes | Sistema de Ventas",
        on_load=State.page_init_clientes,
    )
    _add_private_page(
        page_cuentas,
        route="/cuentas",
        title="Cuentas Corrientes | Sistema de Ventas",
        on_load=State.page_init_cuentas,
    )
    _add_private_page(
        page_dashboard,
        route="/",
        title="Dashboard - TUWAYKIAPP",
        on_load=State.page_init_default,
    )
    _add_private_page(
        page_dashboard,
        route="/dashboard",
        title="Dashboard - TUWAYKIAPP",
        on_load=State.page_init_default,
    )
    _add_private_page(
        page_inventario,
        route="/inventario",
        title="Inventario - TUWAYKIAPP",
        on_load=State.page_init_inventario,
    )
    _add_private_page(
        page_historial,
        route="/historial",
        title="Historial - TUWAYKIAPP",
        on_load=State.page_init_historial,
    )
    _add_private_page(
        page_reportes,
        route="/reportes",
        title="Reportes - TUWAYKIAPP",
        on_load=State.page_init_reportes,
    )
    _add_private_page(
        page_servicios,
        route="/servicios",
        title="Servicios - TUWAYKIAPP",
        on_load=State.page_init_servicios,
    )
    _add_private_page(
        page_configuracion,
        route="/configuracion",
        title="Configuración - TUWAYKIAPP",
        on_load=State.page_init_configuracion,
    )


def _register_owner_routes():
    # Rutas legacy (compatibilidad) y rutas cortas para admin.tuwayki.app.
    _add_private_page(
        page_owner_backoffice,
        route="/owner",
        title="Panel Owner - TUWAYKIAPP",
        on_load=State.page_init_owner,
    )
    _add_private_page(
        page_owner_login,
        route="/owner/login",
        title="Login - Platform Admin",
        on_load=State.page_init_owner_login,
    )

    if APP_SURFACE == "owner":
        _add_private_page(
            page_owner_backoffice,
            route="/",
            title="Panel Owner - TUWAYKIAPP",
            on_load=State.page_init_owner,
        )
        _add_private_page(
            page_owner_login,
            route="/login",
            title="Login - Platform Admin",
            on_load=State.page_init_owner_login,
        )


if APP_SURFACE in {"all", "landing"}:
    _register_landing_routes()

if APP_SURFACE in {"all", "app"}:
    _register_app_routes()

if APP_SURFACE in {"all", "owner"}:
    _register_owner_routes()
