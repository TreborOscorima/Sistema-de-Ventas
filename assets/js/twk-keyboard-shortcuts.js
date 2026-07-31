/**
 * Atajo global de Escape con prioridad de overlays:
 *
 *   1er ESC  -> cierra el modal / diálogo superior (y NADA más).
 *   2do ESC  -> ya sin modal abierto, recién ahí contrae el sidebar
 *               (cierra el overlay lateral en móvil).
 *
 * Por qué en fase de CAPTURA (tercer argumento `true`):
 *   Los diálogos Radix cierran con su propio manejador de ESC y desmontan su
 *   overlay del DOM. Si este handler corriera en fase de burbujeo, Radix ya
 *   habría quitado el overlay y no detectaríamos el modal, cayendo por error al
 *   branch del sidebar (cerrando el modal y contrayendo el menú en el mismo
 *   ESC). En captura evaluamos el DOM ANTES de que Radix lo modifique.
 *
 * Red de seguridad (DIALOG_SELECTOR):
 *   Cualquier diálogo abierto —modal propio, Radix, o [role=dialog]/
 *   [aria-modal]— bloquea el ESC del sidebar. Mientras haya un modal abierto,
 *   el Escape jamás toca el menú lateral.
 *
 * Nota: el `.sidebar-overlay` existe en el DOM incluso en desktop (oculto con
 * `md:hidden` = display:none), y `querySelector`/`.click()` igual lo disparan;
 * por eso el orden y la red de seguridad son necesarios y no alcanza con CSS.
 */
(function () {
    var DIALOG_SELECTOR =
        '.modal-overlay, [data-radix-dialog-overlay], [role="dialog"], ' +
        '[role="alertdialog"], [aria-modal="true"]';

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;

        // 1) Modal propio con overlay: no tiene ESC nativo, lo cerramos nosotros
        //    (click en el overlay -> dispara su handler de cierre en Reflex).
        var modalOverlays = document.querySelectorAll('.modal-overlay');
        if (modalOverlays.length > 0) {
            modalOverlays[modalOverlays.length - 1].click();
            return;
        }

        // 2) Diálogo Radix: lo cierra su propio manejador de ESC. Hacemos click
        //    al overlay por compatibilidad y frenamos acá para NO tocar el
        //    sidebar en el mismo ESC.
        var radixOverlay = document.querySelector('[data-radix-dialog-overlay]');
        if (radixOverlay) {
            radixOverlay.click();
            return;
        }

        // 3) Red de seguridad: cualquier otro diálogo abierto bloquea el ESC del
        //    sidebar (evita cerrar el modal y contraer el menú en el mismo ESC).
        if (document.querySelector(DIALOG_SELECTOR)) {
            return;
        }

        // 4) Sin ningún modal abierto: recién ahora el ESC afecta al sidebar.
        var sidebarOverlay = document.querySelector('.sidebar-overlay');
        if (sidebarOverlay) {
            sidebarOverlay.click();
        }
    }, true);
})();
