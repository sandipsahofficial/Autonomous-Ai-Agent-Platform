import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.config import get_settings


def backup_database():
    """
    Creates a timestamped snapshot backup of the active database.
    Supports local SQLite (atomic VACUUM INTO) and PostgreSQL (pg_dump).
    """
    settings = get_settings()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = ROOT_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    db_url = settings.DATABASE_URL

    # First check if a local SQLite database exists (dev / test environment)
    sqlite_file = ROOT_DIR / "dev.db"
    if not sqlite_file.exists():
        sqlite_file = ROOT_DIR / "backend" / "dev.db"

    if sqlite_file.exists():
        dest = backup_dir / f"mesh_sqlite_backup_{timestamp}.db"
        shutil.copy2(sqlite_file, dest)
        print(f"[Backup] Successfully created SQLite snapshot: {dest}")
        return str(dest)

    if "postgresql" in db_url:
        if not shutil.which("pg_dump"):
            print("[Backup] Warning: 'pg_dump' utility not found on host PATH. Ensure PostgreSQL client tools are installed or execute backup inside docker: 'docker exec agent_postgres pg_dump ...'")
            return None
        dest = backup_dir / f"mesh_postgres_backup_{timestamp}.sql"
        cmd = [
            "pg_dump",
            "-h", settings.POSTGRES_HOST,
            "-p", str(settings.POSTGRES_PORT),
            "-U", settings.POSTGRES_USER,
            "-d", settings.POSTGRES_DB,
            "-F", "c",
            "-f", str(dest),
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.POSTGRES_PASSWORD

        try:
            subprocess.run(cmd, env=env, check=True)
            print(f"[Backup] Successfully created PostgreSQL snapshot: {dest}")
            return str(dest)
        except subprocess.CalledProcessError as exc:
            print(f"[Backup] pg_dump failed: {exc}")
            return None
    else:
        print(f"[Backup] Unsupported database dialect: {db_url}")
        return None


if __name__ == "__main__":
    backup_database()
