"""food_page — landing page de TUWAYKIFOOD."""

import reflex as rx

from ._scripts import (
    _global_styles,
    _sw_cleanup_script,
    _analytics_bootstrap_script,
    _cookie_consent_script,
    _reveal_script,
    _cookie_consent_banner,
)
from ._food_sections import (
    _food_header,
    _food_hero,
    _food_how_it_works,
    _food_features,
    _food_extra_modules,
    _food_faq,
    _food_cta,
    _food_footer,
    _food_floating_whatsapp,
)


def food_page() -> rx.Component:
    """Landing page completa de TUWAYKIFOOD."""
    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.script(_sw_cleanup_script()),
        rx.script(_analytics_bootstrap_script()),
        rx.script(_cookie_consent_script()),
        rx.script(_reveal_script()),
        _food_header(),
        rx.el.main(
            _food_hero(),
            _food_how_it_works(),
            _food_features(),
            _food_extra_modules(),
            _food_faq(),
            _food_cta(),
            class_name="relative",
        ),
        _food_footer(),
        _food_floating_whatsapp(),
        _cookie_consent_banner(),
        class_name="notranslate relative min-h-screen bg-slate-50",
        style={"fontFamily": "'Manrope', sans-serif"},
        **{"translate": "no"},
    )
