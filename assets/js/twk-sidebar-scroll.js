/**
 * Persiste el scroll del sidebar via sessionStorage y lo restaura
 * incluso cuando React reemplaza el nodo durante navegación.
 */
(function () {
    const K = '__sb_scroll';
    let _skip = false;

    document.addEventListener('scroll', function (e) {
        if (!_skip && e.target && e.target.id === 'sidebar-nav') {
            sessionStorage.setItem(K, String(e.target.scrollTop));
        }
    }, true);

    window.addEventListener('load', function () {
        const n = document.getElementById('sidebar-nav');
        const s = sessionStorage.getItem(K);
        if (n && s) n.scrollTop = parseInt(s, 10);
    });

    new MutationObserver(function () {
        const n = document.getElementById('sidebar-nav');
        const s = sessionStorage.getItem(K);
        if (n && s) {
            const t = parseInt(s, 10);
            if (t > 5 && n.scrollTop < 5) {
                _skip = true;
                n.scrollTop = t;
                setTimeout(function () { _skip = false; }, 50);
            }
        }
    }).observe(document.body, { childList: true, subtree: true });
})();
