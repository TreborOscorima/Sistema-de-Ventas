"""
Script de backup automático para la base de datos MySQL.

Uso:
    python scripts/backup_db.py                    # Backup normal
    python scripts/backup_db.py --compress         # Backup comprimido
    python scripts/backup_db.py --keep 7           # Mantener últimos 7 backups

El script lee la configuración de las variables de entorno o .env
"""
from __future__ import annotations

import os
import sys
import subprocess
import datetime
import gzip
import shutil
import argparse
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def get_db_config() -> dict:
    """Obtiene la configuración de la BD desde variables de entorno."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "3306"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "sistema_ventas"),
    }


def get_backup_dir() -> Path:
    """Obtiene o crea el directorio de backups."""
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def generate_backup_filename(database: str, compress: bool = False) -> str:
    """Genera nombre de archivo con timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".sql.gz" if compress else ".sql"
    return f"{database}_backup_{timestamp}{ext}"


def run_mysqldump(config: dict, output_path: Path) -> bool:
    """
    Ejecuta mysqldump para crear el backup.
    
    Returns:
        True si el backup fue exitoso
    """
    cmd = [
        "mysqldump",
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--user={config['user']}",
        f"--password={config['password']}",
        "--single-transaction",  # Consistencia para InnoDB
        "--routines",            # Incluir procedimientos almacenados
        "--triggers",            # Incluir triggers
        "--add-drop-table",      # Facilita restauración
        config["database"],
    ]
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,  # 5 minutos máximo
            )
        
        if result.returncode != 0:
            print(f"Error en mysqldump: {result.stderr}", file=sys.stderr)
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("Error: Timeout ejecutando mysqldump", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: mysqldump no encontrado. Asegúrate de que MySQL esté instalado y en el PATH.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        return False


def compress_file(input_path: Path, output_path: Path) -> bool:
    """Comprime un archivo con gzip."""
    try:
        with open(input_path, "rb") as f_in:
            with gzip.open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Eliminar archivo original
        input_path.unlink()
        return True
        
    except Exception as e:
        print(f"Error comprimiendo: {e}", file=sys.stderr)
        return False


def cleanup_old_backups(backup_dir: Path, database: str, keep: int) -> int:
    """
    Elimina backups antiguos, manteniendo los últimos 'keep'.
    
    Returns:
        Número de backups eliminados
    """
    pattern = f"{database}_backup_*"
    backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
    
    to_delete = backups[:-keep] if len(backups) > keep else []
    
    for backup_file in to_delete:
        try:
            backup_file.unlink()
        except Exception as e:
            print(f"Error eliminando {backup_file}: {e}", file=sys.stderr)
    
    return len(to_delete)


def create_backup(compress: bool = False, keep: int | None = None) -> Path | None:
    """
    Crea un backup de la base de datos.
    
    Args:
        compress: Si se debe comprimir el backup
        keep: Número de backups a mantener (None = no limpiar)
    
    Returns:
        Path del backup creado o None si falló
    """
    config = get_db_config()
    backup_dir = get_backup_dir()
    
    # Generar nombre de archivo
    if compress:
        sql_filename = generate_backup_filename(config["database"], compress=False)
        sql_path = backup_dir / sql_filename
        final_filename = generate_backup_filename(config["database"], compress=True)
        final_path = backup_dir / final_filename
    else:
        final_filename = generate_backup_filename(config["database"], compress=False)
        final_path = backup_dir / final_filename
        sql_path = final_path
    
    print(f"Iniciando backup de '{config['database']}'...")
    print(f"Host: {config['host']}:{config['port']}")
    
    # Ejecutar mysqldump
    if not run_mysqldump(config, sql_path):
        return None
    
    # Comprimir si es necesario
    if compress and sql_path != final_path:
        print("Comprimiendo backup...")
        if not compress_file(sql_path, final_path):
            return None
    
    # Obtener tamaño del archivo
    size_mb = final_path.stat().st_size / (1024 * 1024)
    print(f"Backup creado: {final_path.name} ({size_mb:.2f} MB)")
    
    # Limpiar backups antiguos
    if keep is not None and keep > 0:
        deleted = cleanup_old_backups(backup_dir, config["database"], keep)
        if deleted > 0:
            print(f"Backups antiguos eliminados: {deleted}")
    
    return final_path


def restore_backup(backup_path: Path) -> bool:
    """
    Restaura un backup a la base de datos.
    
    Args:
        backup_path: Path al archivo de backup
    
    Returns:
        True si la restauración fue exitosa
    """
    config = get_db_config()
    
    if not backup_path.exists():
        print(f"Error: Archivo no encontrado: {backup_path}", file=sys.stderr)
        return False
    
    print(f"Restaurando backup: {backup_path.name}")
    print(f"Base de datos: {config['database']}")
    print("¡ADVERTENCIA! Esto sobrescribirá todos los datos actuales.")
    
    # Determinar si está comprimido
    is_compressed = backup_path.suffix == ".gz"
    
    cmd = [
        "mysql",
        f"--host={config['host']}",
        f"--port={config['port']}",
        f"--user={config['user']}",
        f"--password={config['password']}",
        config["database"],
    ]
    
    try:
        if is_compressed:
            # Descomprimir y enviar a mysql
            with gzip.open(backup_path, "rb") as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    timeout=600,  # 10 minutos máximo
                )
        else:
            with open(backup_path, "rb") as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    timeout=600,
                )
        
        if result.returncode != 0:
            print(f"Error en restauración: {result.stderr.decode()}", file=sys.stderr)
            return False
        
        print("Restauración completada exitosamente.")
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def list_backups() -> list[dict]:
    """Lista todos los backups disponibles."""
    backup_dir = get_backup_dir()
    config = get_db_config()
    pattern = f"{config['database']}_backup_*"
    
    backups = []
    for path in sorted(backup_dir.glob(pattern), reverse=True):
        stat = path.stat()
        backups.append({
            "name": path.name,
            "path": path,
            "size_mb": stat.st_size / (1024 * 1024),
            "created": datetime.datetime.fromtimestamp(stat.st_mtime),
        })
    
    return backups


def main():
    parser = argparse.ArgumentParser(description="Backup de base de datos MySQL")
    parser.add_argument(
        "--compress", "-c",
        action="store_true",
        help="Comprimir backup con gzip"
    )
    parser.add_argument(
        "--keep", "-k",
        type=int,
        default=None,
        help="Número de backups a mantener (elimina antiguos)"
    )
    parser.add_argument(
        "--restore", "-r",
        type=str,
        default=None,
        help="Restaurar desde un archivo de backup"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Listar backups disponibles"
    )
    
    args = parser.parse_args()
    
    if args.list:
        backups = list_backups()
        if not backups:
            print("No hay backups disponibles.")
        else:
            print(f"{'Nombre':<45} {'Tamaño':<12} {'Fecha'}")
            print("-" * 75)
            for b in backups:
                print(f"{b['name']:<45} {b['size_mb']:.2f} MB     {b['created'].strftime('%Y-%m-%d %H:%M')}")
        return
    
    if args.restore:
        backup_path = Path(args.restore)
        if not backup_path.is_absolute():
            backup_path = get_backup_dir() / backup_path
        
        confirm = input("¿Está seguro de restaurar? Esto sobrescribirá los datos (s/N): ")
        if confirm.lower() != "s":
            print("Restauración cancelada.")
            return
        
        success = restore_backup(backup_path)
        sys.exit(0 if success else 1)
    
    # Crear backup
    result = create_backup(compress=args.compress, keep=args.keep)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
