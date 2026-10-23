import sqlite3
import os
import sys

# Ensure backend is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine
import app.models  # Registers all models

for path in ["dev.db", os.path.join(os.path.dirname(__file__), "dev.db")]:
    if os.path.exists(path):
        con = sqlite3.connect(path)
        cur = con.cursor()

        # Update tasks table
        existing_task_cols = [r[1] for r in cur.execute("PRAGMA table_info(tasks)").fetchall()]
        for col, ctype in [("user_id", "VARCHAR(64)"), ("workspace_id", "VARCHAR(64)"), ("current_stage", "VARCHAR(32)")]:
            if col not in existing_task_cols:
                cur.execute(f"ALTER TABLE tasks ADD COLUMN {col} {ctype}")
                print(f"Added {col} to {path} tasks")

        # Update subtasks table
        existing_subtask_cols = [r[1] for r in cur.execute("PRAGMA table_info(subtasks)").fetchall()]
        for col, ctype in [("stage", "VARCHAR(32)"), ("dependencies", "JSON"), ("retry_count", "INTEGER DEFAULT 0")]:
            if col not in existing_subtask_cols:
                cur.execute(f"ALTER TABLE subtasks ADD COLUMN {col} {ctype}")
                print(f"Added {col} to {path} subtasks")

        # Update execution_events table
        existing_event_cols = [r[1] for r in cur.execute("PRAGMA table_info(execution_events)").fetchall()]
        for col, ctype in [("status", "VARCHAR(32) DEFAULT 'INFO'"), ("duration_ms", "FLOAT"), ("idempotency_key", "VARCHAR(64)")]:
            if col not in existing_event_cols:
                cur.execute(f"ALTER TABLE execution_events ADD COLUMN {col} {ctype}")
                print(f"Added {col} to {path} execution_events")

        con.commit()
        con.close()

# Create all newly defined tables
Base.metadata.create_all(bind=engine)

# Seed default admin user if not existing
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.auth.security import hash_password

db = SessionLocal()
try:
    admin_user = db.query(User).filter(User.username == "sandip_sah").first()
    if not admin_user:
        admin_user = User(
            username="sandip_sah",
            email="sandip.sah@mesh.internal",
            hashed_password=hash_password("MeshAdmin@2026!"),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        print("Seeded default admin user: sandip_sah")
finally:
    db.close()

print("All Phase 5 tables, users, and security migrations completed successfully.")
