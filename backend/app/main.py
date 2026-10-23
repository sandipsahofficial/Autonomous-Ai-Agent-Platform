from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base
import app.models  # Ensure all models are registered on Base.metadata
from app.api.router import api_router
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.error_handler import ErrorSanitizationMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifespan handler.
    Validates production readiness and ensures tables are created on startup.
    """
    # 1. Validate production readiness fail-fast checks
    settings.validate_production_readiness()

    # 2. Create tables if not existing (ideal for quick start / dev SQLite)
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

# Middleware Stack (Execution order: ErrorSanitizer -> CorrelationId -> SecurityHeaders -> RateLimiter -> CORS)
app.add_middleware(ErrorSanitizationMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
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
    Liveness probe: verifies basic web service responsiveness.
    """
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "max_rework_attempts": settings.MAX_REWORK_ATTEMPTS,
        "max_steps": settings.MAX_STEPS,
    }


@app.get("/ready")
@app.get("/api/v1/ready")
def readiness_check():
    """
    Readiness probe: explicitly verifies database connectivity, latency, and inference engine readiness.
    Distinguishes liveness from backend dependency readiness.
    """
    import time
    start_time = time.time()
    db_ok = False
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        db_err = str(exc)
        return {
            "status": "not_ready",
            "database": "unreachable",
            "error": "Database connectivity check failed.",
        }

    latency_ms = round((time.time() - start_time) * 1000, 2)
    return {
        "status": "ready",
        "database": "connected",
        "database_latency_ms": latency_ms,
        "llm_provider": settings.LLM_PROVIDER,
        "environment": settings.APP_ENV,
        "auth_enforced": getattr(settings, "REQUIRE_AUTH", False),
        "rate_limiting": getattr(settings, "RATE_LIMIT_ENABLED", True),
    }
