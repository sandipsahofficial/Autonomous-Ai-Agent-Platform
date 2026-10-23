import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import get_settings

logger = logging.getLogger("mesh.error_handler")


class ErrorSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled internal exceptions, securely logs the traceback with correlation ID,
    and returns a sanitized error response to prevent leaking internal stack traces, paths,
    or credentials to clients.
    """
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            settings = get_settings()
            correlation_id = getattr(request.state, "correlation_id", "unknown")

            # Log full stack trace internally with correlation ID
            logger.error(
                f"[InternalError] correlation_id={correlation_id} path={request.url.path} error={exc}",
                exc_info=True,
            )

            # In production or non-debug mode, return strictly sanitized generic message
            if not getattr(settings, "APP_DEBUG", False) or getattr(settings, "APP_ENV", "development") == "production":
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "InternalServerError",
                        "detail": "An internal server error occurred. Please contact system administrator with your correlation ID.",
                        "correlation_id": correlation_id,
                    },
                    headers={"X-Correlation-ID": correlation_id},
                )

            # In debug/development mode, provide error description with correlation ID
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "detail": str(exc),
                    "correlation_id": correlation_id,
                },
                headers={"X-Correlation-ID": correlation_id},
            )
