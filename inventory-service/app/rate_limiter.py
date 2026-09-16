import re
import time
import threading
from typing import Dict, Tuple, Optional
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60
AUTH_RATE_LIMIT_REQUESTS = 5
AUTH_RATE_LIMIT_WINDOW_SECONDS = 60

INTERNAL_SERVICE_TOKEN = "microservices-internal-secret-token-2026"
JWT_SECRET_KEY = "microservices-shared-secret-key-at-least-32-bytes-long!"
JWT_ALGORITHM = "HS256"

class InMemoryRateLimiter:

    def __init__(self):
        self._lock = threading.Lock()

        self._records: Dict[str, Tuple[float, int]] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:

        now = time.time()
        with self._lock:
            if key not in self._records:

                self._records[key] = (now, 1)
                return True, 0

            window_start, count = self._records[key]
            elapsed = now - window_start

            if elapsed >= window_seconds:

                self._records[key] = (now, 1)
                return True, 0

            if count < max_requests:
                self._records[key] = (window_start, count + 1)
                return True, 0

            retry_after = max(1, int(round(window_seconds - elapsed)))
            return False, retry_after

    def reset(self, key: Optional[str] = None):

        with self._lock:
            if key:
                self._records.pop(key, None)
            else:
                self._records.clear()

limiter = InMemoryRateLimiter()

class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        if path in ["/", "/docs", "/openapi.json", "/redoc", "/favicon.ico"]:
            return await call_next(request)

        internal_token = request.headers.get("X-Internal-Service-Token")
        if internal_token and internal_token == INTERNAL_SERVICE_TOKEN:
            return await call_next(request)

        client_key = self._get_client_identifier(request)

        normalized_path = re.sub(r"/\d+", "/{id}", path).rstrip("/")
        if not normalized_path:
            normalized_path = "/"

        if normalized_path in ["/auth/login", "/auth/register"]:
            max_requests = AUTH_RATE_LIMIT_REQUESTS
            window_seconds = AUTH_RATE_LIMIT_WINDOW_SECONDS
            bucket_key = f"auth:{request.method}:{normalized_path}:{client_key}"
        else:
            max_requests = RATE_LIMIT_REQUESTS
            window_seconds = RATE_LIMIT_WINDOW_SECONDS
            bucket_key = f"api:{request.method}:{normalized_path}:{client_key}"

        allowed, retry_after = limiter.is_allowed(bucket_key, max_requests, window_seconds)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please wait 60 seconds before trying again."
                },
                headers={
                    "Retry-After": str(retry_after)
                }
            )

        return await call_next(request)

    def _get_client_identifier(self, request: Request) -> str:

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:

                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("user_id") or payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except Exception:
                pass

        client_ip = request.client.host if request.client else "unknown_client"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        return f"ip:{client_ip}"
