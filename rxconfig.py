import reflex as rx

config = rx.Config(
    app_name="app",
    
    # Conexión a Base de Datos (ESTA ESTÁ PERFECTA, NO LA TOQUES)
    db_url="mysql+pymysql://root:TreborOD%28523%29@localhost:3306/sistema_ventas",
    
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