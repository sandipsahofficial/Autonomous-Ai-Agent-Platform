import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings

settings = get_settings()

database_url = settings.DATABASE_URL

# Test if postgres driver is available; if not, fall back to SQLite for local development
try:
    if "postgres" in database_url:
        import psycopg2
except ImportError:
    # psycopg2 not installed in current environment; use local sqlite file
    database_url = "sqlite:///./dev.db"

connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}

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
