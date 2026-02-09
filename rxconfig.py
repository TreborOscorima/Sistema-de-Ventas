import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
import reflex as rx

load_dotenv()

# Configuracion de Entorno
env = (os.getenv("ENV") or "dev").strip().lower()
is_prod = env in {"prod", "production"}
api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
redis_url = (os.getenv("REDIS_URL") or "").strip()
if is_prod and not redis_url:
    raise RuntimeError(
        "Missing required environment variable for production: REDIS_URL"
    )

# Helpers
def _get_env(var_name: str, default: str | None = None) -> str | None:
    value = os.getenv(var_name)
    if is_prod and not value:
        raise RuntimeError(
            f"Missing required environment variable for production: {var_name}"
        )
    return value if value is not None else default

# DB Config
db_user = _get_env("DB_USER", "root")
db_password = _get_env("DB_PASSWORD", "tu_clave_local")
db_host = _get_env("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "3306")
db_name = _get_env("DB_NAME", "sistema_ventas")

db_user_escaped = quote_plus(db_user or "")
db_password_escaped = quote_plus(db_password or "")

# URL sincronica para Reflex
db_url = (
    f"mysql+pymysql://{db_user_escaped}:{db_password_escaped}@{db_host}:{db_port}/{db_name}"
)

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD (Producción)
# =============================================================================
# Los siguientes headers deben configurarse en el reverse proxy (nginx/Caddy):
#
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# Encabezado Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
#
# Ejemplo nginx:
#   add_header X-Content-Type-Options "nosniff" always;
#   add_header X-Frame-Options "DENY" always;
# =============================================================================

config = rx.Config(
    app_name="app",
    db_url=db_url,
    api_url=api_url,
    plugins=[rx.plugins.TailwindV3Plugin()],
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    telemetry_enabled=not is_prod,
    theme=rx.theme(
        has_background=True,
        radius="medium",
        spacing="relaxed",
        transitions="gentle",
    ),
)
