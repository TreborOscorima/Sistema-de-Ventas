/**
 * Escucha cambios cross-tab y refresca estado en pestañas activas.
 * Debounce 700ms para evitar refrescos en ráfaga.
 */
(function () {
    if (window.__twkRuntimeSyncAttached) return;
    window.__twkRuntimeSyncAttached = true;
    const KEY = "twk_runtime_sync";
    let lastSeen = "";
    let lastRunAt = 0;

    try { lastSeen = localStorage.getItem(KEY) || ""; }
    catch (_err) { lastSeen = ""; }

    function triggerRefresh() {
        const now = Date.now();
        if ((now - lastRunAt) < 700) return;
        lastRunAt = now;
        const btn = document.querySelector('[data-twk-runtime-sync="1"]');
        if (btn) btn.click();
    }

    function checkForExternalChange() {
        let current = "";
        try { current = localStorage.getItem(KEY) || ""; }
        catch (_err) { current = ""; }
        if (!current || current === lastSeen) return;
        lastSeen = current;
        triggerRefresh();
    }

    window.addEventListener("storage", function (event) {
        if (!event || event.key !== KEY) return;
        lastSeen = event.newValue || "";
        triggerRefresh();
    });

    window.addEventListener("focus", checkForExternalChange);
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") {
            checkForExternalChange();
        }
    });
})();
