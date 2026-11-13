import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import Config

BACKUP_DIR = BASE_DIR / 'backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_database() -> Path:
    """Create a point-in-time timestamped backup of the active database."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    # Case 1: MySQL
    if Config.DB_PASSWORD or ('mysql' in Config.SQLALCHEMY_DATABASE_URI):
        backup_file = BACKUP_DIR / f"mysql_backup_{Config.DB_NAME}_{timestamp}.sql"
        print(f"Creating MySQL backup of '{Config.DB_NAME}' to {backup_file.name}...")
        
        cmd = [
            "mysqldump",
            f"-h{Config.DB_HOST}",
            f"-P{Config.DB_PORT}",
            f"-u{Config.DB_USER}",
            f"-p{Config.DB_PASSWORD}",
            "--single-transaction",
            "--quick",
            Config.DB_NAME
        ]
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                subprocess.run(cmd, stdout=f, check=True)
            print(f"MySQL backup completed successfully: {backup_file}")
            return backup_file
        except FileNotFoundError:
            print("mysqldump utility not found on PATH. Please ensure MySQL client tools are installed.")
        except subprocess.CalledProcessError as e:
            print(f"mysqldump failed with error code {e.returncode}")

    # Case 2: SQLite
    sqlite_file = BASE_DIR / 'seller_ops_db.sqlite'
    if sqlite_file.exists():
        backup_file = BACKUP_DIR / f"sqlite_backup_{timestamp}.sqlite"
        shutil.copy2(sqlite_file, backup_file)
        print(f"SQLite backup completed successfully: {backup_file}")
        return backup_file

    print("No active database file found to backup.")
    return None


def restore_database(backup_path: Path):
    """Restore database from a specified backup file."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    if backup_path.suffix == '.sqlite':
        target = BASE_DIR / 'seller_ops_db.sqlite'
        shutil.copy2(backup_path, target)
        print(f"SQLite database restored successfully from {backup_path} to {target}")
    elif backup_path.suffix == '.sql':
        cmd = [
            "mysql",
            f"-h{Config.DB_HOST}",
            f"-P{Config.DB_PORT}",
            f"-u{Config.DB_USER}",
            f"-p{Config.DB_PASSWORD}",
            Config.DB_NAME
        ]
        with open(backup_path, 'r', encoding='utf-8') as f:
            subprocess.run(cmd, stdin=f, check=True)
        print(f"MySQL database restored successfully from {backup_path}")
    else:
        raise ValueError(f"Unsupported backup format: {backup_path.suffix}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--restore':
        if len(sys.argv) < 3:
            print("Usage: python backup_restore.py --restore <path_to_backup_file>")
        else:
            restore_database(Path(sys.argv[2]))
    else:
        backup_database()

