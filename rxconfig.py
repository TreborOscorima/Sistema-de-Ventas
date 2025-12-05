import reflex as rx

config = rx.Config(
    app_name="app",
    db_url="mysql+pymysql://root:TreborOD%28523%29@localhost:3306/sistema_ventas",
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
