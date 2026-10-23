import time
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import get_settings


class RateLimiter:
    """
    In-memory sliding-window rate limiter.
    Stores request timestamps per client IP / identifier within a rolling 60-second window.
    """
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        # key -> list of float timestamps
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def is_allowed(self, client_key: str, max_requests: int) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window_seconds

        # Periodic cleanup of stale client keys
        if now - self._last_cleanup > 120:
            self._cleanup(cutoff)
            self._last_cleanup = now

        timestamps = [t for t in self.requests[client_key] if t > cutoff]
        self.requests[client_key] = timestamps

        if len(timestamps) >= max_requests:
            retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
            return False, max(1, retry_after)

        self.requests[client_key].append(now)
        return True, 0

    def _cleanup(self, cutoff: float):
        keys_to_delete = [k for k, v in self.requests.items() if not v or v[-1] <= cutoff]
        for k in keys_to_delete:
            del self.requests[k]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces route-specific and global rate limits to protect against brute-force attacks and resource exhaustion.
    """
    def __init__(self, app, window_seconds: int = 60, default_limit: int = 180):
        super().__init__(app)
        self.limiter = RateLimiter(window_seconds)
        self.default_limit = default_limit
        # Sensitive or expensive endpoints with lower limits
        self.custom_limits = {
            "/api/v1/auth/login": 15,          # Brute-force defense
            "/api/v1/auth/register": 10,       # Spam defense
            "/api/v1/tasks": 30,               # Expensive graph dispatches
            "/api/v1/documents/upload": 20,    # File parsing / memory
        }

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return await call_next(request)

        # Health / ready checks are excluded from rate limits
        path = request.url.path
        if path in ("/health", "/ready", "/api/v1/health", "/api/v1/ready"):
            return await call_next(request)

        # Identify client by user header, auth token, or client IP
        client_ip = request.headers.get("X-Forwarded-For") or (request.client.host if request.client else "unknown")
        user_key = request.headers.get("X-User-ID") or client_ip

        # Determine limit for this path
        max_reqs = self.default_limit
        for prefix, limit in self.custom_limits.items():
            if path.startswith(prefix) and request.method == "POST":
                max_reqs = limit
                break

        key = f"{user_key}:{path}"
        allowed, retry_after = self.limiter.is_allowed(key, max_reqs)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "TooManyRequests",
                    "detail": f"Rate limit exceeded. Maximum {max_reqs} requests per minute allowed.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
