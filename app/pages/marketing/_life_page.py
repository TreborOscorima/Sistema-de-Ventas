"""life_page — landing page de TUWAYKILIFE (Sistema para Clínicas)."""

import reflex as rx

from ._scripts import (
    _global_styles,
    _sw_cleanup_script,
    _analytics_bootstrap_script,
    _cookie_consent_script,
    _reveal_script,
    _cookie_consent_banner,
    life_jsonld_components,
)
from ._life_sections import (
    _life_header,
    _life_hero,
    _life_how_it_works,
    _life_features,
    _life_extra_modules,
    _life_faq,
    _life_cta,
    _life_footer,
    _life_floating_whatsapp,
)


def life_page() -> rx.Component:
    """Landing page completa de TUWAYKILIFE."""
    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.script(_sw_cleanup_script()),
        rx.script(_analytics_bootstrap_script()),
        rx.script(_cookie_consent_script()),
        rx.script(_reveal_script()),
        *life_jsonld_components(),
        _life_header(),
        rx.el.main(
            _life_hero(),
            _life_how_it_works(),
            _life_features(),
            _life_extra_modules(),
            _life_faq(),
            _life_cta(),
            class_name="relative",
        ),
        _life_footer(),
        _life_floating_whatsapp(),
        _cookie_consent_banner(),
        class_name="notranslate relative min-h-screen bg-slate-50",
        style={"fontFamily": "'Manrope', sans-serif"},
        **{"translate": "no"},
    )
