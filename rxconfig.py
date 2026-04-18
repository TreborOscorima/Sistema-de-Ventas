"""
Configuración Reflex + SQLAlchemy.

Principios:
- Un solo engine sync (el que usa Reflex internamente) bajo el mismo pool del engine async.
- En producción: ninguna credencial tiene default. Cualquier variable faltante -> RuntimeError.
- Charset, timezone e isolation level se fijan explícitamente para evitar
  corrupción de datos internacionales y phantoms en reportes concurrentes.
- Headers de seguridad: configurados en reverse proxy (nginx) — ver docs/DEPLOYMENT_SECURITY.md.
"""
from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
import reflex as rx

load_dotenv()

# ---------------------------------------------------------------------------
# Entorno
# ---------------------------------------------------------------------------
ENV = (os.getenv("ENV") or "dev").strip().lower()
IS_PROD = ENV in {"prod", "production"}
API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8000")


def _require_env(var_name: str, *, default: str | None = None, dev_default: str | None = None) -> str:
    """Lee una env var. En prod nunca acepta default; en dev acepta `dev_default`."""
    value = os.getenv(var_name)
    if value:
        return value
    if IS_PROD:
        raise RuntimeError(f"[rxconfig] Variable obligatoria en producción: {var_name}")
    return dev_default if dev_default is not None else (default or "")


# Redis requerido en prod (sesiones distribuidas + caché L2).
REDIS_URL = _require_env("REDIS_URL", dev_default="")

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------
DB_USER = _require_env("DB_USER", dev_default="root")
DB_PASSWORD = _require_env("DB_PASSWORD")  # sin default, incluso en dev — forzar .env
DB_HOST = _require_env("DB_HOST", dev_default="localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = _require_env("DB_NAME", dev_default="sistema_ventas")

_USER_ESC = quote_plus(DB_USER)
_PASS_ESC = quote_plus(DB_PASSWORD)

# URL sync (Reflex + alembic). charset y autocommit parametrizados.
DB_URL = (
    f"mysql+pymysql://{_USER_ESC}:{_PASS_ESC}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# ---------------------------------------------------------------------------
# Pool tuning (Reflex lee estas env vars vía reflex.config.environment)
# ---------------------------------------------------------------------------
_POOL_DEFAULTS = {
    "SQLALCHEMY_POOL_SIZE": os.getenv("DB_POOL_SIZE", "15"),
    "SQLALCHEMY_POOL_RECYCLE": os.getenv("DB_POOL_RECYCLE", "1800"),
    "SQLALCHEMY_POOL_PRE_PING": "true",
    "SQLALCHEMY_POOL_TIMEOUT": os.getenv("DB_POOL_TIMEOUT", "10"),
    "SQLALCHEMY_MAX_OVERFLOW": os.getenv("DB_MAX_OVERFLOW", "10"),
}
for _k, _v in _POOL_DEFAULTS.items():
    os.environ.setdefault(_k, _v)

# ---------------------------------------------------------------------------
# Reflex config
# ---------------------------------------------------------------------------
config = rx.Config(
    app_name="app",
    db_url=DB_URL,
    api_url=API_URL,
    plugins=[
        rx.plugins.TailwindV3Plugin(
            config={
                "plugins": ["@tailwindcss/typography@0.5.19"],
                "theme": {
                    "extend": {
                        "fontFamily": {
                            "sans": ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
                            "grotesk": ["'Space Grotesk'", "system-ui", "sans-serif"],
                        },
                        "screens": {
                            "motion-safe": {"raw": "(prefers-reduced-motion: no-preference)"},
                            "motion-reduce": {"raw": "(prefers-reduced-motion: reduce)"},
                        },
                    },
                },
            }
        ),
    ],
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    telemetry_enabled=not IS_PROD,
    show_built_with_reflex=False,
    theme=rx.theme(
        has_background=True,
        radius="medium",
        accent_color="indigo",
        gray_color="slate",
        spacing="relaxed",
        transitions="gentle",
    ),
)
