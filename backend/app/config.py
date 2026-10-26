import os
from pathlib import Path
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

# Resolve project directories and load .env from root or backend
ROOT_DIR = Path(__file__).resolve().parents[2]
ROOT_ENV_PATH = ROOT_DIR / ".env"
BACKEND_ENV_PATH = ROOT_DIR / "backend" / ".env"

if ROOT_ENV_PATH.exists():
    load_dotenv(dotenv_path=ROOT_ENV_PATH)
if BACKEND_ENV_PATH.exists():
    load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=True)
load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        """
        Application configuration loaded from environment variables or .env file.
        Validates types and provides sensible defaults.
        """
        APP_ENV: str = "development"
        APP_DEBUG: bool = True
        PORT: int = 8000
        HOST: str = "0.0.0.0"

        POSTGRES_USER: str = "agent_admin"
        POSTGRES_PASSWORD: str = "agent_secret_password"
        POSTGRES_DB: str = "agent_platform"
        POSTGRES_HOST: str = "postgres"
        POSTGRES_PORT: int = 5432
        DATABASE_URL: str = (
            "postgresql+psycopg2://agent_admin:agent_secret_password@postgres:5432/agent_platform"
        )

        LLM_PROVIDER: str = "mock"
        OPENAI_API_KEY: Optional[str] = None
        CLAUDE_API_KEY: Optional[str] = None
        LLM_MODEL_NAME: str = "gpt-4o"
        OLLAMA_BASE_URL: str = "http://localhost:11434"
        OLLAMA_MODEL_NAME: str = "llama3"
        LLM_TIMEOUT_SECONDS: float = 30.0

        MAX_REWORK_ATTEMPTS: int = 3
        MAX_STEPS: int = 15
        TOKEN_BUDGET: int = 50000
        COST_BUDGET_USD: float = 2.00

        # Phase 5 Security & Production Hardening
        JWT_SECRET_KEY: str = "mesh_insecure_development_secret_change_in_production"
        REQUIRE_AUTH: bool = False
        ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
        RATE_LIMIT_ENABLED: bool = True
        LOG_LEVEL: str = "INFO"

        model_config = SettingsConfigDict(
            env_file=(str(ROOT_ENV_PATH), str(BACKEND_ENV_PATH), ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

        def get_cors_origins(self) -> list[str]:
            if self.APP_ENV == "development" and self.APP_DEBUG:
                return ["*"]
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

        def validate_production_readiness(self) -> None:
            """
            Fail-fast validation for production deployments.
            Prevents deploying with development debug flags or default secrets.
            """
            if self.APP_ENV == "production":
                if self.APP_DEBUG:
                    raise ValueError("CRITICAL: APP_DEBUG must be False in production.")
                if self.JWT_SECRET_KEY == "mesh_insecure_development_secret_change_in_production":
                    raise ValueError("CRITICAL: JWT_SECRET_KEY must be configured with a secure secret in production.")
                if not self.REQUIRE_AUTH:
                    raise ValueError("CRITICAL: REQUIRE_AUTH must be True in production.")
                origins = self.get_cors_origins()
                if "*" in origins:
                    raise ValueError("CRITICAL: Wildcard '*' CORS origin is strictly forbidden in production.")
                if "sqlite" in self.DATABASE_URL.lower():
                    raise ValueError("CRITICAL: SQLite database is strictly forbidden in production. PostgreSQL is required.")

except ImportError:
    # Graceful fallback for lightweight local host environments without pydantic-settings
    from pydantic import BaseModel

    class Settings(BaseModel):  # type: ignore[no-redef]
        APP_ENV: str = os.getenv("APP_ENV", "development")
        APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() in ("true", "1", "yes")
        PORT: int = int(os.getenv("PORT", "8000"))
        HOST: str = os.getenv("HOST", "0.0.0.0")

        POSTGRES_USER: str = os.getenv("POSTGRES_USER", "agent_admin")
        POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "agent_secret_password")
        POSTGRES_DB: str = os.getenv("POSTGRES_DB", "agent_platform")
        POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
        POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://agent_admin:agent_secret_password@postgres:5432/agent_platform",
        )

        LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")
        OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        CLAUDE_API_KEY: Optional[str] = os.getenv("CLAUDE_API_KEY")
        LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o")
        OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        OLLAMA_MODEL_NAME: str = os.getenv("OLLAMA_MODEL_NAME", "llama3")
        LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))

        MAX_REWORK_ATTEMPTS: int = int(os.getenv("MAX_REWORK_ATTEMPTS", "3"))
        MAX_STEPS: int = int(os.getenv("MAX_STEPS", "15"))
        TOKEN_BUDGET: int = int(os.getenv("TOKEN_BUDGET", "50000"))
        COST_BUDGET_USD: float = float(os.getenv("COST_BUDGET_USD", "2.00"))

        # Phase 5 Security & Production Hardening
        JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "mesh_insecure_development_secret_change_in_production")
        REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")
        ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000")
        RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
        LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        def get_cors_origins(self) -> list[str]:
            if self.APP_ENV == "development" and self.APP_DEBUG:
                return ["*"]
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

        def validate_production_readiness(self) -> None:
            if self.APP_ENV == "production":
                if self.APP_DEBUG:
                    raise ValueError("CRITICAL: APP_DEBUG must be False in production.")
                if self.JWT_SECRET_KEY == "mesh_insecure_development_secret_change_in_production":
                    raise ValueError("CRITICAL: JWT_SECRET_KEY must be configured with a secure secret in production.")
                if not self.REQUIRE_AUTH:
                    raise ValueError("CRITICAL: REQUIRE_AUTH must be True in production.")
                origins = self.get_cors_origins()
                if "*" in origins:
                    raise ValueError("CRITICAL: Wildcard '*' CORS origin is strictly forbidden in production.")
                if "sqlite" in self.DATABASE_URL.lower():
                    raise ValueError("CRITICAL: SQLite database is strictly forbidden in production. PostgreSQL is required.")


@lru_cache()
def get_settings() -> Settings:
    """
    Cached accessor for application settings to prevent re-reading .env on every call.
    """
    return Settings()
