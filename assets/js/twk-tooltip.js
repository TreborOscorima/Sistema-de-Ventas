/**
 * Tooltip global para botones/enlaces icon-only.
 * Convierte title/aria-label en tooltip visual consistente con mapeos ES.
 * Idempotente: segunda carga no reinicializa.
 */
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
        const text = (el.textContent || "").replace(/\s+/g, " ").trim();
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

        if (rawTitle) {
            el.dataset.twkNativeTitle = rawTitle;
            el.removeAttribute("title");
        }
    }

    function normalizeTechnicalLabel(rawLabel) {
        if (!rawLabel) return "";
        const canonical = String(rawLabel).toLowerCase().replace(/[^a-z0-9]/g, "");
        const labelMap = {
            trash2: "Eliminar", trash: "Eliminar", delete: "Eliminar", remove: "Eliminar",
            pencil: "Editar", edit: "Editar",
            eye: "Visualizar", view: "Visualizar",
            printer: "Imprimir", print: "Imprimir",
            download: "Descargar", upload: "Subir",
            search: "Buscar", close: "Cerrar", x: "Cerrar",
            refreshcw: "Actualizar", refreshccw: "Actualizar", rotateccw: "Reiniciar",
            creditcard: "Metodo de pago", wallet: "Caja",
            users: "Usuarios", user: "Usuario",
            settings: "Configurar", filter: "Filtrar", menu: "Menu",
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
            "pencil": "Editar", "square-pen": "Editar",
            "trash": "Eliminar", "trash-2": "Eliminar",
            "eye": "Visualizar", "eye-off": "Ocultar",
            "file-text": "Documento", "file-down": "Descargar archivo",
            "printer": "Imprimir",
            "plus": "Agregar", "minus": "Quitar",
            "x": "Cerrar", "x-circle": "Cerrar",
            "chevron-left": "Anterior", "chevron-right": "Siguiente",
            "download": "Descargar", "upload": "Subir",
            "refresh-cw": "Actualizar", "refresh-ccw": "Actualizar", "rotate-ccw": "Reiniciar",
            "repeat": "Repetir",
            "settings": "Configurar", "sliders-horizontal": "Ajustes",
            "filter": "Filtrar", "search": "Buscar",
            "calendar": "Calendario", "calendar-check": "Confirmar", "calendar-plus": "Nueva reserva",
            "wallet": "Caja", "credit-card": "Metodo de pago",
            "users": "Usuarios", "user": "Usuario",
            "history": "Historial",
            "log-in": "Iniciar sesion", "log-out": "Cerrar sesion",
            "lock": "Bloquear", "unlock": "Desbloquear",
            "info": "Informacion", "circle-help": "Ayuda",
            "play": "Iniciar", "save": "Guardar",
            "check": "Confirmar", "circle-check": "Confirmar", "badge-check": "Confirmar",
            "ban": "Cancelar", "menu": "Menu",
            "panel-left-close": "Ocultar menu",
        };
        if (mapByName[iconName]) return mapByName[iconName];

        const mapByCanonical = {
            trash2: "Eliminar",
            refreshcw: "Actualizar", refreshccw: "Actualizar", rotateccw: "Reiniciar",
            slidershorizontal: "Ajustes",
            creditcard: "Metodo de pago",
            filetext: "Documento", filedown: "Descargar archivo",
            eyeoff: "Ocultar",
            xcircle: "Cerrar",
            checkcheck: "Confirmar", circlecheck: "Confirmar", badgecheck: "Confirmar",
            logout: "Cerrar sesion", login: "Iniciar sesion",
            panelleftclose: "Ocultar menu",
            chevronleft: "Anterior", chevronright: "Siguiente",
            calendarplus: "Nueva reserva", calendarcheck: "Confirmar",
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
            .replace(/\b\w/g, (match) => match.toUpperCase());
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
