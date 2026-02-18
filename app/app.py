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
from app.pages.servicios import servicios_page
from app.pages.cuentas import cuentas_page
from app.pages.clientes import clientes_page
from app.pages.dashboard import dashboard_page
from app.pages.reportes import reportes_page
from app.components.notification import NotificationHolder


def cashbox_banner() -> rx.Component:
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


def currency_selector() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("coins", class_name="h-5 w-5 text-amber-600"),
            rx.el.span("Moneda de trabajo", class_name="text-sm font-semibold text-slate-800"),
            class_name="flex items-center gap-2",
        ),
        rx.el.select(
            rx.foreach(
                State.available_currencies,
                lambda currency: rx.el.option(currency["name"], value=currency["code"]),
            ),
            value=State.selected_currency_code,
            on_change=State.set_currency,
            class_name="w-full sm:w-auto h-10 px-3 text-sm bg-white border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500",
        ),
        rx.el.span(
            "Mostrando importes en ",
            rx.el.span(State.currency_name, class_name="font-semibold"),
            class_name="text-sm text-slate-600",
        ),
        class_name="flex flex-col sm:flex-row sm:items-center gap-3 bg-white border border-slate-200 rounded-xl shadow-sm p-4",
    )


def _toast_provider() -> rx.Component:
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


# Mapeo de rutas a páginas
ROUTE_TO_PAGE = {
    "/": "Ingreso",
    "/ingreso": "Ingreso",
    "/compras": "Compras",
    "/venta": "Venta",
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
    "Compras": "/compras",
    "Venta": "/venta",
    "Gestion de Caja": "/caja",
    "Clientes": "/clientes",
    "Cuentas Corrientes": "/cuentas",
    "Inventario": "/inventario",
    "Historial": "/historial",
    "Servicios": "/servicios",
    "Configuracion": "/configuracion",
}


def _loading_skeleton() -> rx.Component:
    """Skeleton que se muestra mientras el estado hidrata (nueva pestaña)."""
    return rx.el.div(
        # Barra superior gradiente
        rx.el.div(
            class_name=(
                "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
            ),
        ),
        rx.el.div(
            # Sidebar skeleton
            rx.el.div(
                rx.el.div(
                    rx.el.div(class_name="h-8 w-8 rounded-lg bg-slate-200 animate-pulse"),
                    rx.el.div(class_name="h-4 w-24 rounded bg-slate-200 animate-pulse"),
                    class_name="flex items-center gap-3 px-4 pt-5 pb-4",
                ),
                rx.el.div(
                    *[rx.el.div(class_name="h-9 w-full rounded-lg bg-slate-200/60 animate-pulse") for _ in range(6)],
                    class_name="flex flex-col gap-2 px-3 mt-4",
                ),
                class_name="hidden lg:flex flex-col w-56 border-r border-slate-200 bg-white h-screen flex-shrink-0",
            ),
            # Content skeleton
            _content_skeleton(),
            class_name="flex h-screen w-full bg-slate-50 overflow-hidden",
        ),
        class_name="text-slate-900 w-full h-screen",
        style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
    )


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
    """Layout wrapper para páginas autenticadas.

    El sidebar es PERSISTENTE — nunca desaparece durante la navegación.
    Solo el área de contenido muestra skeleton durante la hidratación inicial.
    """
    return rx.cond(
        State.is_hydrated,
        # --- Ya hidratado: decidir entre login o contenido ---
        rx.cond(
            State.is_authenticated,
            rx.el.main(
                rx.el.div(
                    class_name=(
                        "fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r "
                        "from-amber-400 via-rose-500 to-indigo-500 z-[60]"
                    ),
                ),
                _toast_provider(),
                NotificationHolder(),
                rx.el.div(
                    sidebar(),
                    rx.el.div(
                        rx.el.div(
                            rx.cond(
                                State._runtime_ctx_loaded,
                                cashbox_banner(),
                                rx.fragment(),
                            ),
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
                        class_name="flex-1 h-full overflow-y-auto",
                    ),
                    class_name="flex h-screen w-full bg-slate-50 overflow-hidden",
                ),
                class_name="text-slate-900 w-full h-screen fade-in-up",
                style={"fontFamily": "'Plus Jakarta Sans', 'Inter', sans-serif"},
            ),
            rx.fragment(NotificationHolder(), login_page()),
        ),
        # --- Aún no hidratado: skeleton de carga ---
        _loading_skeleton(),
    )


def index() -> rx.Component:
    """Página principal - redirige a Ingreso."""
    return authenticated_layout(ingreso_page())


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

def page_marketing() -> rx.Component:
    return marketing_page()


app = rx.App(
    theme=rx.theme(appearance="light"),
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

# Página principal (redirige a ingreso)
app.add_page(
    index,
    route="/",
    on_load=[State.refresh_runtime_context, State.page_init_default],
)

# Cambio de contrasena (solo cuando aplica)
app.add_page(
    page_cambiar_contrasena,
    route="/cambiar-clave",
    title="Cambiar Contrasena - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_cambiar_clave],
)

app.add_page(
    page_periodo_prueba_finalizado,
    route="/periodo-prueba-finalizado",
    title="Periodo de Prueba Finalizado - TUWAYKIAPP",
)

app.add_page(
    page_cuenta_suspendida,
    route="/cuenta-suspendida",
    title="Cuenta Suspendida - TUWAYKIAPP",
)

app.add_page(
    page_registro,
    route="/registro",
    title="Registro - TUWAYKIAPP",
)
app.add_page(
    page_marketing,
    route="/sitio",
    title="TUWAYKIAPP | Sistema de Ventas para tiendas, servicios y reservas",
)

# Páginas individuales con rutas separadas
app.add_page(
    page_ingreso,
    route="/ingreso",
    title="Ingreso - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_ingreso],
)
app.add_page(
    page_compras,
    route="/compras",
    title="Compras - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_compras],
)
app.add_page(
    page_venta,
    route="/venta",
    title="Venta - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_venta],
)
app.add_page(
    page_caja,
    route="/caja",
    title="Gestión de Caja - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_caja],
)
app.add_page(
    page_clientes,
    route="/clientes",
    title="Clientes | Sistema de Ventas",
    on_load=[State.refresh_runtime_context, State.page_init_clientes],
)
app.add_page(
    page_cuentas,
    route="/cuentas",
    title="Cuentas Corrientes | Sistema de Ventas",
    on_load=[State.refresh_runtime_context, State.page_init_cuentas],
)
app.add_page(
    page_dashboard,
    route="/dashboard",
    title="Dashboard - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_default],
)
app.add_page(
    page_inventario,
    route="/inventario",
    title="Inventario - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_inventario],
)
app.add_page(
    page_historial,
    route="/historial",
    title="Historial - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_historial],
)
app.add_page(
    page_reportes,
    route="/reportes",
    title="Reportes - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_reportes],
)
app.add_page(
    page_servicios,
    route="/servicios",
    title="Servicios - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_servicios],
)
app.add_page(
    page_configuracion,
    route="/configuracion",
    title="Configuración - TUWAYKIAPP",
    on_load=[State.refresh_runtime_context, State.page_init_configuracion],
)
