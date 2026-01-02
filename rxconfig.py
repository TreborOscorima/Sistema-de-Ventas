import os

from dotenv import load_dotenv
import reflex as rx

load_dotenv()

# Configuracion de Entorno
api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000")

# DB Config
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "tu_clave_local")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "3306")
db_name = os.getenv("DB_NAME", "sistema_ventas")

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
    telemetry_enabled=True,
    theme=rx.theme(
        has_background=True,
        radius="medium",
        spacing="relaxed",
        transitions="gentle",
    ),
)
