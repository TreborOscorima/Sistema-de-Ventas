import os

from dotenv import load_dotenv
import reflex as rx

load_dotenv()

# Configuracion de Entorno
env = (os.getenv("ENV") or "dev").strip().lower()
is_prod = env in {"prod", "production"}
api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")

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

# URL sincronica para Reflex
db_url = (
    f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

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
