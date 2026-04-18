"""
Script CLI para promover/revocar un usuario como Owner de la plataforma.

Uso:
    # Promover a owner
    python scripts/make_owner.py owner@example.com

    # Revocar owner
    python scripts/make_owner.py owner@example.com --revoke

    # Listar todos los owners
    python scripts/make_owner.py --list
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Permite ejecutar directamente desde scripts/
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")


def _build_db_url() -> str:
    """Construye la URL de conexión a la BD."""
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        print(
            "ERROR: DB_PASSWORD no está configurado. "
            "Verifica tu archivo .env o variables de entorno antes de ejecutar este script.",
            file=sys.stderr,
        )
        sys.exit(1)
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "sistema_ventas")
    return (
        f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def list_owners(engine) -> None:
    """Lista todos los usuarios con is_platform_owner=True."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, email, username, is_platform_owner "
                "FROM user WHERE is_platform_owner = 1"
            )
        ).fetchall()

    if not rows:
        print("No hay owners registrados en la plataforma.")
        return

    print(f"\n{'ID':<6} {'Email':<40} {'Username':<25} {'Owner'}")
    print("-" * 80)
    for row in rows:
        print(f"{row[0]:<6} {row[1]:<40} {row[2]:<25} {'Sí'}")
    print(f"\nTotal: {len(rows)} owner(s)\n")


def set_owner(engine, email: str, *, revoke: bool = False) -> None:
    """Activa o revoca el flag is_platform_owner para un usuario."""
    new_value = 0 if revoke else 1
    action = "revocar" if revoke else "promover"

    with engine.connect() as conn:
        # Verificar que el usuario existe
        user = conn.execute(
            text("SELECT id, email, username, is_platform_owner FROM user WHERE email = :email"),
            {"email": email},
        ).fetchone()

        if not user:
            print(f"\n[ERROR] No se encontró un usuario con email: {email}")
            sys.exit(1)

        current_value = user[3]
        if current_value == new_value:
            status = "ya es owner" if new_value else "no es owner"
            print(f"\n[INFO] El usuario '{user[2]}' ({email}) {status}. Sin cambios.")
            return

        # Confirmar antes de proceder
        action_desc = "PROMOVER a Owner" if not revoke else "REVOCAR Owner"
        print(f"\nUsuario: {user[2]} ({email})")
        print(f"Acción:  {action_desc}")
        confirm = input("¿Confirmar? (s/N): ").strip().lower()

        if confirm not in ("s", "si", "sí", "y", "yes"):
            print("Operación cancelada.")
            return

        conn.execute(
            text("UPDATE user SET is_platform_owner = :val WHERE email = :email"),
            {"val": new_value, "email": email},
        )
        conn.commit()

        emoji = "✓" if not revoke else "✗"
        past = "promovido a Owner" if not revoke else "revocado como Owner"
        print(f"\n{emoji} Usuario '{user[2]}' ({email}) {past} exitosamente.")


def main():
    parser = argparse.ArgumentParser(
        description="Gestionar owners de la plataforma SaaS"
    )
    parser.add_argument(
        "email",
        nargs="?",
        help="Email del usuario a promover/revocar",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Revocar permisos de owner en vez de otorgarlos",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_owners",
        help="Listar todos los owners actuales",
    )
    args = parser.parse_args()

    if not args.email and not args.list_owners:
        parser.error("Debes proporcionar un email o usar --list")

    engine = create_engine(_build_db_url(), echo=False)

    if args.list_owners:
        list_owners(engine)
        if args.email:
            set_owner(engine, args.email, revoke=args.revoke)
    else:
        set_owner(engine, args.email, revoke=args.revoke)


if __name__ == "__main__":
    main()
