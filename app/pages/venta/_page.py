import reflex as rx
from app.state import State
from app.components.ui import permission_guard
from app.pages.clientes import client_form_modal
from ._cart_section import recent_moves_modal, sale_receipt_modal
from ._variants_section import batch_picker_modal, variant_picker_modal
from ._products_section import client_selector, sale_products_card
from ._reservation_section import (
    reservation_info_card,
    _presupuesto_banner,
    _reservation_products_breakdown,
)
from ._payment_form import (
    payment_sidebar,
    payment_mobile_section,
    _quot_save_modal,
    _quot_load_drawer,
)


def _venta_keyboard_shortcuts() -> rx.Component:
    """Atajos de teclado para Punto de Venta.

    F11           → Abrir modal Movimientos Recientes
    Enter         → Añadir producto (quick-add-bar, autocomplete cerrado)
                    o Confirmar Venta (desde campo numérico de monto, sin modal abierto)
    Arrow Up/Down → Navegar sugerencias de autocomplete (preventDefault + scrollIntoView)
    """
    return rx.script(
        """
        (function(){
            if(window.__ventaKbAttached) return;
            window.__ventaKbAttached = true;
            document.addEventListener('keydown', function(e){
                // F11 → abrir modal Movimientos Recientes
                if(e.key === 'F11'){
                    e.preventDefault();
                    e.stopPropagation();
                    var btn = document.querySelector('[data-venta-recent-btn]');
                    if(btn) btn.click();
                    return;
                }

                // Arrow Up/Down → navegar sugerencias de autocomplete
                if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
                    var el = document.activeElement;
                    if(!el) return;
                    var searchDiv = el.closest('[data-product-search]');
                    if(!searchDiv) return;
                    var dropdown = searchDiv.querySelector('[data-autocomplete-dropdown]');
                    if(!dropdown || dropdown.children.length === 0) return;
                    // Prevenir que el cursor del input se mueva
                    e.preventDefault();
                    // Scroll al elemento seleccionado después del re-render de Reflex
                    setTimeout(function(){
                        if(!dropdown) return;
                        var items = dropdown.querySelectorAll('button');
                        for(var i = 0; i < items.length; i++){
                            // El item seleccionado tiene clase 'bg-indigo-50' (sin hover:)
                            var cls = ' ' + items[i].className + ' ';
                            if(cls.indexOf(' bg-indigo-50 ') > -1){
                                items[i].scrollIntoView({block:'nearest'});
                                break;
                            }
                        }
                    }, 80);
                    return;
                }

                // Enter → añadir producto (quick-add-bar) o confirmar venta (área de pago)
                if(e.key === 'Enter'){
                    var el = document.activeElement;
                    if(!el) return;

                    // Rama 1: foco dentro de la barra de búsqueda rápida
                    var bar = el.closest('[data-quick-add-bar]');
                    if(bar){
                        // No interferir con el form de barcode (tiene su propio on_submit)
                        if(el.id === 'venta_barcode_input') return;
                        // Si el autocomplete está abierto, dejar que Reflex on_key_down
                        // maneje la selección — NO hacer click en añadir
                        var searchDiv = el.closest('[data-product-search]');
                        if(searchDiv){
                            var dropdown = searchDiv.querySelector('[data-autocomplete-dropdown]');
                            if(dropdown && dropdown.children.length > 0) return;
                        }
                        e.preventDefault();
                        var addBtn = document.querySelector('[data-venta-add-btn]');
                        if(addBtn) addBtn.click();
                        return;
                    }

                    // Rama 2: confirmar venta desde campo de monto (type=number) o sin foco en texto
                    var tag = el.tagName.toLowerCase();
                    var inputType = (el.type || '').toLowerCase();
                    if(tag === 'textarea' || tag === 'select') return;
                    if(tag === 'input' && inputType !== 'number') return;
                    // No disparar si hay un modal abierto encima
                    if(document.querySelector('.modal-overlay')) return;
                    // Buscar el botón confirmar visible y habilitado
                    var btns = document.querySelectorAll('[data-venta-confirm-btn]');
                    var confirmBtn = null;
                    for(var i = 0; i < btns.length; i++){
                        if(!btns[i].disabled && btns[i].offsetParent !== null){
                            confirmBtn = btns[i]; break;
                        }
                    }
                    if(!confirmBtn) return;
                    e.preventDefault();
                    confirmBtn.click();
                }
            });
        })();
        """
    )


def venta_page() -> rx.Component:
    """Página principal del punto de venta (POS)."""
    content = rx.el.div(
        _venta_keyboard_shortcuts(),
        # Contenido principal
        rx.el.div(
            rx.cond(
                State.reservation_payment_id != "",
                rx.fragment(),
                rx.el.div(
                    rx.el.div(
                        rx.el.h1(
                            "PUNTO DE VENTA",
                            class_name="text-2xl font-bold text-slate-900 tracking-tight",
                        ),
                        rx.el.div(
                            rx.match(
                                State.selected_business_vertical,
                                ("bodega", rx.el.span(
                                    rx.icon("zap", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Bodega / Kiosko",
                                    class_name="inline-flex items-center text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-0.5",
                                )),
                                ("ferreteria", rx.el.span(
                                    rx.icon("wrench", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Ferretería",
                                    class_name="inline-flex items-center text-xs font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-full px-2.5 py-0.5",
                                )),
                                ("farmacia", rx.el.span(
                                    rx.icon("pill", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Farmacia",
                                    class_name="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2.5 py-0.5",
                                )),
                                ("ropa", rx.el.span(
                                    rx.icon("shirt", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Ropa",
                                    class_name="inline-flex items-center text-xs font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-full px-2.5 py-0.5",
                                )),
                                ("jugueteria", rx.el.span(
                                    rx.icon("blocks", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Juguetería",
                                    class_name="inline-flex items-center text-xs font-medium text-pink-700 bg-pink-50 border border-pink-200 rounded-full px-2.5 py-0.5",
                                )),
                                ("restaurante", rx.el.span(
                                    rx.icon("utensils", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Restaurante",
                                    class_name="inline-flex items-center text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200 rounded-full px-2.5 py-0.5",
                                )),
                                ("supermercado", rx.el.span(
                                    rx.icon("shopping-basket", class_name="w-3.5 h-3.5 inline mr-1"),
                                    "Modo Supermercado",
                                    class_name="inline-flex items-center text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-full px-2.5 py-0.5",
                                )),
                                rx.el.span(
                                    "Realiza ventas directas, selecciona productos y gestiona el cobro.",
                                    class_name="text-sm text-slate-500",
                                ),
                            ),
                            class_name="flex items-center gap-2",
                        ),
                        class_name="flex flex-col gap-1",
                    ),
                    rx.el.button(
                        rx.icon("history", class_name="h-4 w-4"),
                        rx.el.span("Movimientos recientes(F11)"),
                        on_click=State.toggle_recent_modal(True),
                        custom_attrs={"data-venta-recent-btn": "1"},
                        class_name=(
                            "flex items-center gap-2 px-3 py-2 text-sm border border-slate-200 "
                            "rounded-lg text-slate-700 hover:bg-slate-50"
                        ),
                    ),
                    class_name="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4",
                ),
            ),
            # Info de reserva/servicio prominente (si aplica)
            reservation_info_card(),
            # Banner presupuesto cargado (contexto global, fuera de la card de productos)
            _presupuesto_banner(),
            # Desglose servicio + productos cuando ambos coexisten
            _reservation_products_breakdown(),
            # Selector de cliente — oculto cuando la reserva ya provee el cliente,
            # o cuando la empresa no tiene el módulo de clientes habilitado.
            rx.cond(
                State.company_has_clients & (State.reservation_payment_id == ""),
                client_selector(),
                rx.fragment(),
            ),
            # Barra de entrada rápida
            sale_products_card(),
            # Pago móvil/tablet
            payment_mobile_section(),
            class_name="flex flex-col flex-1 min-h-0 gap-2 sm:gap-3 p-2.5 sm:p-3 lg:pr-0 overflow-y-auto lg:overflow-hidden",
        ),
        # Sidebar de pago (solo desktop grande)
        rx.el.div(
            payment_sidebar(),
            class_name="hidden lg:block h-[calc(100vh-4rem)] sticky top-16 shrink-0",
        ),
        client_form_modal(),
        recent_moves_modal(),
        sale_receipt_modal(),
        batch_picker_modal(),
        variant_picker_modal(),
        _quot_save_modal(),
        _quot_load_drawer(),
        class_name="flex min-h-[calc(100vh-4rem)] lg:h-[calc(100vh-4rem)]",
    )
    return permission_guard(
        has_permission=State.can_view_ventas,
        content=content,
        redirect_message="Acceso denegado a Ventas",
    )
