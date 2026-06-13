"""marketing_page entry point."""

import reflex as rx

from ._scripts import (
    _global_styles,
    _analytics_bootstrap_script,
    _cookie_consent_script,
    _reveal_script,
    _cookie_consent_banner,
    _sw_cleanup_script,
)
from ._sections import (
    _announcement_banner,
    _header_section,
    _hero_section,
    _metrics_section,
    _industries_section,
    _comparison_section,
    _modules_section,
    _demo_flow_section,
    _screenshots_section,
    _pricing_section,
    _use_cases_section,
    _extra_capabilities_section,
    _timeline_section,
    _strength_section,
    _faq_section,
    _tuwaykifood_section,
    _cta_section,
    _footer_section,
    _floating_whatsapp,
)


def marketing_page() -> rx.Component:
    """Pagina de marketing y landing page publica."""
    return rx.el.div(
        rx.el.style(_global_styles()),
        rx.script(_sw_cleanup_script()),
        rx.script(_analytics_bootstrap_script()),
        rx.script(_cookie_consent_script()),
        rx.script(_reveal_script()),
        _announcement_banner(),
        _header_section(),
        rx.el.main(
            _hero_section(),
            _metrics_section(),
            _industries_section(),
            _comparison_section(),
            _modules_section(),
            _demo_flow_section(),
            _screenshots_section(),
            _pricing_section(),
            _use_cases_section(),
            _extra_capabilities_section(),
            _timeline_section(),
            _strength_section(),
            _faq_section(),
            _tuwaykifood_section(),
            _cta_section(),
            class_name="relative",
        ),
        _footer_section(),
        _floating_whatsapp(),
        _cookie_consent_banner(),
        class_name="notranslate relative min-h-screen bg-slate-50",
        style={"fontFamily": "'Manrope', sans-serif"},
        **{"translate": "no"},
    )
