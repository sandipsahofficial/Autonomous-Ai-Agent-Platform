import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.config import get_settings


def restore_database(snapshot_path: str):
    """
    Restores the database from a verified backup snapshot.
    """
    settings = get_settings()
    src = Path(snapshot_path)
    if not src.exists():
        print(f"[Restore] Error: Snapshot file '{snapshot_path}' does not exist.")
        return False

    db_url = settings.DATABASE_URL

    if "sqlite" in db_url:
        for dest in [ROOT_DIR / "dev.db", ROOT_DIR / "backend" / "dev.db"]:
            if dest.parent.exists():
                shutil.copy2(src, dest)
                print(f"[Restore] Successfully restored SQLite database to: {dest}")
        return True

    elif "postgresql" in db_url:
        cmd = [
            "pg_restore",
            "-h", settings.POSTGRES_HOST,
            "-p", str(settings.POSTGRES_PORT),
            "-U", settings.POSTGRES_USER,
            "-d", settings.POSTGRES_DB,
            "--clean",
            str(src),
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.POSTGRES_PASSWORD

        try:
            subprocess.run(cmd, env=env, check=True)
            print(f"[Restore] Successfully restored PostgreSQL database from: {src}")
            return True
        except subprocess.CalledProcessError as exc:
            print(f"[Restore] pg_restore failed: {exc}")
            return False
    else:
        print(f"[Restore] Unsupported database dialect: {db_url}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_db.py <path_to_snapshot>")
        sys.exit(1)
    restore_database(sys.argv[1])
