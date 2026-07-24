"""Helper para imprimir HTML dentro de la misma ventana (nativo en la PWA).

En la app instalada (PWA) `window.open('', '_blank')` lanzaba una ventana nueva
del navegador (Chrome) para poder imprimir, lo que rompía la sensación de app
nativa. `build_print_script` imprime el HTML desde un iframe oculto en la ventana
actual: el diálogo de impresión (Guardar PDF / elegir impresora) aparece igual,
pero sobre la propia app, sin abrir el navegador.
"""
import json


def build_print_script(html_content: str) -> str:
    """Genera el JS que imprime `html_content` vía un iframe oculto in-window."""
    return f"""
    (function() {{
        var html = {json.dumps(html_content)};
        var prev = document.getElementById('twk-print-frame');
        if (prev) prev.remove();
        var iframe = document.createElement('iframe');
        iframe.id = 'twk-print-frame';
        iframe.setAttribute('aria-hidden', 'true');
        iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
        iframe.onload = function() {{
            try {{
                var w = iframe.contentWindow;
                w.focus();
                w.onafterprint = function() {{ setTimeout(function() {{ iframe.remove(); }}, 200); }};
                w.print();
                setTimeout(function() {{
                    var f = document.getElementById('twk-print-frame');
                    if (f) f.remove();
                }}, 60000);
            }} catch (e) {{}}
        }};
        iframe.srcdoc = html;
        document.body.appendChild(iframe);
    }})();
    """
