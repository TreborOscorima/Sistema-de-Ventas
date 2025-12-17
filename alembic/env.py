from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine # Agregamos create_engine
from alembic import context

# --- IMPORTACIÓN DE TU CONFIGURACIÓN DE REFLEX ---
import sys
import os
# Aseguramos que Python encuentre el archivo rxconfig.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from rxconfig import config as rx_config
# ------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importamos tus modelos para que Alembic reconozca las tablas
from app.models import rx 
target_metadata = rx.Model.metadata

def run_migrations_offline() -> None:
    """Modo offline: usa la URL de rxconfig."""
    url = rx_config.db_url # Usamos la URL de tu rxconfig.py
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Modo online: crea el motor usando la URL de rxconfig."""
    # Creamos el motor de conexión directamente con la URL de tu base de datos
    connectable = create_engine(rx_config.db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()