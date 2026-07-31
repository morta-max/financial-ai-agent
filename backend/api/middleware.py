"""
Custom middleware for the Financial AI Agent API.

Provides:
- Rate limiting (token bucket algorithm)
- Request logging
- Security headers
- CORS with proper origin validation
"""

import os
import time
import hashlib
from collections import defaultdict
from datetime import datetime

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RateLimiter:
    """
    Token bucket rate limiter.
    Limits requests per client IP per time window.
    """

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        burst_multiplier: int = 3,
    ):
        self.rate = requests_per_window / window_seconds
        self.window = window_seconds
        self.burst = requests_per_window * burst_multiplier
        self.buckets: dict[str, tuple[float, float]] = {}  # ip -> (tokens, last_refill)
        self._cleanup_time = time.time()

    def _refill(self, key: str) -> tuple[float, float]:
        """Refill tokens based on elapsed time."""
        now = time.time()
        tokens, last = self.buckets.get(key, (self.burst, now))
        elapsed = now - last
        new_tokens = min(self.burst, tokens + elapsed * self.rate)
        self.buckets[key] = (new_tokens, now)
        return new_tokens, now

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed. Each call consumes 1 token."""
        # Periodic cleanup of old entries
        now = time.time()
        if now - self._cleanup_time > 300:  # Every 5 minutes
            self._cleanup_time = now
            stale = [k for k, (_, last) in self.buckets.items() if now - last > 600]
            for k in stale:
                del self.buckets[k]

        tokens, _ = self._refill(key)
        if tokens >= 1:
            self.buckets[key] = (tokens - 1, now)
            return True
        return False

    def remaining(self, key: str) -> int:
        """Get remaining tokens for a key."""
        tokens, _ = self._refill(key)
        return max(0, int(tokens))


# Global rate limiters
general_limiter = RateLimiter(requests_per_window=200, window_seconds=60)
sync_limiter = RateLimiter(requests_per_window=5, window_seconds=300)  # 5 syncs per 5 min
ws_limiter = RateLimiter(requests_per_window=10, window_seconds=60)


def get_client_key(request: Request) -> str:
    """Generate a rate limit key from client IP or API key."""
    # Prefer X-Forwarded-For for proxied setups
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    # Hash for privacy
    return hashlib.sha256(f"{ip}:{request.url.path}".encode()).hexdigest()[:16]


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Skip health check and root
    if request.url.path in ("/", "/health", "/docs", "/redoc", "/openapi.json"):
        return await call_next(request)

    key = get_client_key(request)

    # Admin/sync endpoints have stricter limits
    if "/admin/sync" in request.url.path:
        limiter = sync_limiter
    elif "/ws/" in request.url.path:
        limiter = ws_limiter
    else:
        limiter = general_limiter

    if not limiter.is_allowed(key):
        logger.warning(f"Rate limit exceeded for key={key} path={request.url.path}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "请求过于频繁，请稍后再试",
                "retry_after_seconds": 30,
            },
            headers={"Retry-After": "30"},
        )

    response = await call_next(request)

    # Add rate limit headers
    remaining = limiter.remaining(key)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(limiter.burst)

    return response


async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


async def request_logging_middleware(request: Request, call_next):
    """Log all API requests with timing."""
    start = time.time()

    try:
        response = await call_next(request)
        elapsed = time.time() - start

        # Only log non-static paths
        if "/api/" in request.url.path:
            logger.info(
                f"{request.method} {request.url.path} "
                f"→ {response.status_code} ({elapsed:.3f}s)"
            )

        return response
    except Exception as e:
        elapsed = time.time() - start
        logger.error(
            f"{request.method} {request.url.path} "
            f"→ ERROR: {e} ({elapsed:.3f}s)"
        )
        raise
