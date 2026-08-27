"""
In-memory Sliding Window Rate Limiter — data-serving service.

Thread-safe, zero external dependency.

Upgrade path to Redis (Phase 2):
    Replace SlidingWindowRateLimiter with RedisRateLimiter using the same
    is_allowed(key, max_requests, window_seconds) interface.
    No changes needed in routes or dependency signatures.
"""

import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.models import UserModel


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.

    Uses a deque of monotonic timestamps per key.
    Old timestamps (outside the window) are evicted on each check.
    """

    def __init__(self) -> None:
        self._store: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Return True and record the request if within limit.
        Return False (without recording) if the limit is exceeded.
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._store.setdefault(key, deque())
            # Evict timestamps outside the sliding window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            if len(timestamps) >= max_requests:
                return False
            timestamps.append(now)
            return True


# Module-level singleton — created once at import time, shared across requests.
_limiter = SlidingWindowRateLimiter()


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def ip_rate_limit(max_requests: int, window_seconds: int = 60) -> Callable[..., None]:
    """
    Dependency factory: rate limit by client IP address.

    Use for unauthenticated endpoints (login, register, refresh) where
    the attack vector is a single IP spamming the endpoint.

    Args:
        max_requests: Maximum allowed requests within the window.
        window_seconds: Sliding window duration in seconds.

    Returns:
        A FastAPI dependency that raises HTTP 429 when limit is exceeded.
    """
    def dependency(request: Request) -> None:
        key = f"ip:{_get_client_ip(request)}"
        if not _limiter.is_allowed(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency


def user_rate_limit(max_requests: int, window_seconds: int = 60) -> Callable[..., None]:
    """
    Dependency factory: rate limit by authenticated user_id.

    Use for protected endpoints that already require a valid access_token.
    FastAPI deduplicates get_current_user per request — no extra DB query.

    Args:
        max_requests: Maximum allowed requests within the window.
        window_seconds: Sliding window duration in seconds.

    Returns:
        A FastAPI dependency that raises HTTP 429 when limit is exceeded.
    """
    def dependency(current_user: UserModel = Depends(get_current_user)) -> None:
        key = f"user:{current_user.id}"
        if not _limiter.is_allowed(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency
