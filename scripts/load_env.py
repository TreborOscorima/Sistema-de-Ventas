#!/usr/bin/env python3
"""
Cargador seguro de variables de entorno para shells Bash.

Uso:
    eval "$(python3 scripts/load_env.py)"
    eval "$(python3 scripts/load_env.py /ruta/custom/.env)"

Resuelve el problema de passwords con caracteres especiales (paréntesis,
signos, espacios) que rompen `source .env`.
"""
from __future__ import annotations

import shlex
import sys
from pathlib import Path

try:
    from dotenv import dotenv_values
except ImportError:
    print("echo 'ERROR: python-dotenv no instalado. pip install python-dotenv'", flush=True)
    sys.exit(1)


def main() -> None:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env")
    if not env_path.is_file():
        print(f"echo 'ERROR: archivo {env_path} no encontrado.'", flush=True)
        sys.exit(1)

    values = dotenv_values(env_path)
    for key, val in values.items():
        # shlex.quote() encapsula correctamente cualquier caracter especial
        safe_val = shlex.quote(val or "")
        print(f"export {key}={safe_val}")


if __name__ == "__main__":
    main()
