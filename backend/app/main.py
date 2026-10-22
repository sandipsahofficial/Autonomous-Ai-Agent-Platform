from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base
import app.models  # Ensure all models are registered on Base.metadata
from app.api.router import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifespan handler.
    Ensures tables are created on startup.
    """
    # Create tables if not existing (ideal for quick start / test sqlite)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"Warning: Could not automatically run create_all on startup: {exc}")
    yield


app = FastAPI(
    title="Autonomous AI Agent Platform API",
    description="Multi-agent orchestration platform with safety guardrails, sandboxing, and human-in-the-loop controls.",
    version="0.1.0",
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# Configure CORS to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router)


@app.get("/")
def read_root():
    """
    Root endpoint returning basic platform information.
    """
    return {
        "platform": "Autonomous AI Agent Platform",
        "status": "online",
        "version": "0.1.0",
        "docs_url": "/docs",
    }


@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    """
    Health check endpoint returning application status and active runtime configuration.
    """
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "max_rework_attempts": settings.MAX_REWORK_ATTEMPTS,
        "max_steps": settings.MAX_STEPS,
    }
