"""Seed permisos de nuevos módulos: Presupuestos, Promociones, Listas de Precios, Etiquetas.

Inserta las filas faltantes en `permission` y las asigna a los roles
existentes según ADMIN_PRIVILEGES y DEFAULT_USER_PRIVILEGES:

  view_presupuestos    → Administrador (True), Usuario (True)
  manage_promociones   → Administrador (True)
  manage_listas_precios→ Administrador (True)
  view_etiquetas       → Administrador (True), Usuario (True)

Idempotente: usa INSERT IGNORE en ambas tablas.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-05-15
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Insertar los codenames nuevos en permission (si no existen) ────────
    op.execute("""
        INSERT IGNORE INTO permission (codename, description) VALUES
            ('view_presupuestos',    'Ver módulo de presupuestos y cotizaciones'),
            ('manage_promociones',   'Gestionar promociones y descuentos'),
            ('manage_listas_precios','Gestionar listas de precios'),
            ('view_etiquetas',       'Ver e imprimir etiquetas de productos')
    """)

    # ── 2. Asignar a roles "Administrador" (todos los permisos nuevos) ────────
    op.execute("""
        INSERT IGNORE INTO rolepermission (role_id, permission_id)
        SELECT r.id, p.id
        FROM role r
        CROSS JOIN permission p
        WHERE r.name = 'Administrador'
          AND p.codename IN (
              'view_presupuestos',
              'manage_promociones',
              'manage_listas_precios',
              'view_etiquetas'
          )
    """)

    # ── 3. Asignar a roles "Usuario" (solo permisos de lectura) ───────────────
    op.execute("""
        INSERT IGNORE INTO rolepermission (role_id, permission_id)
        SELECT r.id, p.id
        FROM role r
        CROSS JOIN permission p
        WHERE r.name = 'Usuario'
          AND p.codename IN (
              'view_presupuestos',
              'view_etiquetas'
          )
    """)


def downgrade() -> None:
    # No se revierten asignaciones de permisos — eliminarlos podría
    # romper sesiones activas. Revertir manualmente si es necesario.
    pass
