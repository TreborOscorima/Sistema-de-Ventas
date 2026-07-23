/**
 * Reposiciona los flyouts del rail colapsado (tooltip de nombre y submenús)
 * con position:fixed junto al icono que se está hoverando.
 *
 * Motivo: el rail colapsado ahora es scrolleable (overflow-y-auto), lo que
 * fuerza overflow-x a recortar. Con los flyouts en position:fixed y ubicados
 * por JS, escapan del recorte y siguen apareciendo al costado del icono.
 *
 * Cada icono del rail lleva data-rail-item="<pagina>" y su flyout
 * data-rail-flyout="<pagina>". En hover, ubicamos el flyout a la derecha del
 * icono y lo acotamos dentro del viewport (para paneles altos como
 * Configuración con varios submódulos).
 */
(function () {
    function positionFor(item) {
        var label = item.getAttribute('data-rail-item');
        if (!label) return;
        var flyout = null;
        var all = document.querySelectorAll('[data-rail-flyout]');
        for (var i = 0; i < all.length; i++) {
            if (all[i].getAttribute('data-rail-flyout') === label) { flyout = all[i]; break; }
        }
        if (!flyout) return;

        var r = item.getBoundingClientRect();
        // Junto al borde derecho del icono; el gap visual lo da el pl-2 del panel.
        flyout.style.left = Math.round(r.right) + 'px';
        flyout.style.top = Math.round(r.top) + 'px';
        flyout.style.bottom = 'auto';

        // Acotar dentro del viewport: si el panel se pasa por abajo, lo
        // anclamos hacia arriba sin salirse por el borde superior.
        var fr = flyout.getBoundingClientRect();
        var vh = window.innerHeight;
        if (fr.height > 0 && fr.bottom > vh - 8) {
            var top = Math.max(8, vh - 8 - fr.height);
            flyout.style.top = Math.round(top) + 'px';
        }
    }

    document.addEventListener('mouseover', function (e) {
        var t = e.target;
        if (!t || !t.closest) return;
        var item = t.closest('[data-rail-item]');
        if (item) positionFor(item);
    }, true);
})();
