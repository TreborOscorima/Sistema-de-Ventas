/**
 * Shortcut global: Escape cierra overlays en orden de prioridad
 * (modales custom → Radix → sidebar overlay).
 */
(function () {
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;

        const modalOverlays = document.querySelectorAll('.modal-overlay');
        if (modalOverlays.length > 0) {
            modalOverlays[modalOverlays.length - 1].click();
            return;
        }

        const radixOverlay = document.querySelector('[data-radix-dialog-overlay]');
        if (radixOverlay) {
            radixOverlay.click();
            return;
        }

        const sidebarOverlay = document.querySelector('.sidebar-overlay');
        if (sidebarOverlay) {
            sidebarOverlay.click();
        }
    });
})();
