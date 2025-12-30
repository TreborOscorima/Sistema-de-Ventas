import os

from dotenv import load_dotenv
import reflex as rx

load_dotenv()


def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


DB_USER = _require_env("DB_USER")
DB_PASSWORD = _require_env("DB_PASSWORD")
DB_HOST = _require_env("DB_HOST")
DB_NAME = _require_env("DB_NAME")

db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"

config = rx.Config(
    app_name="app",
    
    # Conexión a Base de Datos (ESTA ESTÁ PERFECTA, NO LA TOQUES)
    db_url=db_url,
    
    # --- AGREGA ESTA LÍNEA AQUÍ ---
    api_url="http://localhost:8000",
    # ------------------------------

    plugins=[rx.plugins.TailwindV3Plugin()],
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    telemetry_enabled=True,
    theme=rx.theme(
        has_background=True,
        radius="medium",
        spacing="relaxed",
        transitions="gentle",
    ),
)
