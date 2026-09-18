"""
Hybrid Redis & In-Memory Sliding Window Rate Limiter — data-serving service.

Uses Redis Sorted Sets (ZSET) for distributed, atomic sliding-window rate limiting.
Automatically falls back to thread-safe in-memory sliding window if Redis is offline.
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.redis_client import redis_cache
from app.models import UserModel

logger = logging.getLogger("webgis.rate_limiter")


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter (Fallback engine).
    """

    def __init__(self) -> None:
        self._store: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._store.setdefault(key, deque())
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            if len(timestamps) >= max_requests:
                return False
            timestamps.append(now)
            return True


_in_memory_limiter = SlidingWindowRateLimiter()


def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
    """
    Check rate limit using Redis ZSET (distributed). Falls back to in-memory.
    Returns True if request is allowed, False if rate limit is exceeded.
    """
    redis_client = getattr(redis_cache, "_client", None)
    if redis_client and redis_cache.is_available():
        try:
            now = time.time()
            cutoff = now - window_seconds
            r_key = f"ratelimit:{key}"

            pipe = redis_client.pipeline()
            # 1. Clear timestamps older than sliding window
            pipe.zremrangebyscore(r_key, 0, cutoff)
            # 2. Count requests in current window
            pipe.zcard(r_key)
            results = pipe.execute()

            current_count = results[1]
            if current_count >= max_requests:
                return False

            # 3. Add current timestamp & set TTL
            pipe = redis_client.pipeline()
            pipe.zadd(r_key, {f"{now}_{time.time_ns()}": now})
            pipe.expire(r_key, window_seconds + 5)
            pipe.execute()
            return True
        except Exception as exc:
            logger.warning(f"Redis rate limiting failed: {exc}. Falling back to in-memory limiter.")

    return _in_memory_limiter.is_allowed(key, max_requests, window_seconds)


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def ip_rate_limit(max_requests: int, window_seconds: int = 60) -> Callable[..., None]:
    """
    Dependency factory: rate limit by client IP address.
    """
    def dependency(request: Request) -> None:
        key = f"ip:{_get_client_ip(request)}"
        if not is_rate_limited(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency


def user_rate_limit(max_requests: int, window_seconds: int = 60) -> Callable[..., None]:
    """
    Dependency factory: rate limit by authenticated user_id.
    """
    def dependency(current_user: UserModel = Depends(get_current_user)) -> None:
        key = f"user:{current_user.id}"
        if not is_rate_limited(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency

