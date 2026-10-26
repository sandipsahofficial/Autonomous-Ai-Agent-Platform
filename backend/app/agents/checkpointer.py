from functools import lru_cache
from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from app.config import get_settings

settings = get_settings()

# Global memory saver for local development and unit tests
_memory_saver = MemorySaver()


def get_checkpointer() -> BaseCheckpointSaver:
    """
    Thin wrapper returning the official LangGraph checkpointer.
    Keeps LangGraph internal checkpoint tables separate from application tables (tasks, audit_logs).
    Uses MemorySaver for zero-dependency local runs and tests.
    """
    from app.database import database_url
    if "postgres" in database_url and settings.APP_ENV != "test":
        try:
            from langgraph_checkpoint_postgres import PostgresSaver
            # Use connection string to initialize official postgres checkpointer
            # PostgresSaver manages its own internal checkpoints and checkpoint_blobs tables
            return PostgresSaver.from_conn_string(database_url)
        except Exception:
            # Fallback to in-memory checkpointer if PostgreSQL is starting or not reachable
            return _memory_saver

    return _memory_saver
