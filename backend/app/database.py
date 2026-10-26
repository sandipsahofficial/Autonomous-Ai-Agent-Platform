import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings

settings = get_settings()

database_url = settings.DATABASE_URL

# Check postgres driver and reachability
if "postgres" in database_url:
    try:
        import psycopg2
    except ImportError:
        if settings.APP_ENV == "production":
            raise RuntimeError("Cannot connect to PostgreSQL in production mode: psycopg2 driver is not installed.")
        # psycopg2 not installed in current environment; use local sqlite file for development
        database_url = "sqlite:///./dev.db"

    # In development mode outside container, verify if host:port is reachable before blocking
    if settings.APP_ENV != "production" and "postgres" in database_url:
        import socket
        from urllib.parse import urlparse
        try:
            parsed = urlparse(database_url)
            pg_host = parsed.hostname or "localhost"
            pg_port = parsed.port or 5432
            with socket.create_connection((pg_host, pg_port), timeout=1.5):
                pass
        except (socket.timeout, ConnectionRefusedError, OSError):
            # PostgreSQL is not reachable from current dev host; use dev.db
            database_url = "sqlite:///./dev.db"

if settings.APP_ENV == "production" and "sqlite" in database_url.lower():
    raise RuntimeError("Production mode requires PostgreSQL. SQLite database is strictly forbidden in production.")

connect_args = {"check_same_thread": False} if "sqlite" in database_url else {"connect_timeout": 5}

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Session factory bound to the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session per request.
    Ensures session is closed after request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
