"""
Hybrid Redis & In-Memory Sliding Window Rate Limiter — segy-processing-service.

Uses Redis Sorted Sets (ZSET) for distributed, atomic sliding-window rate limiting.
Automatically falls back to thread-safe in-memory sliding window if Redis is offline.

Rate limit constants:
    UPLOAD_SINGLE_MAX  — max requests per window for single file upload
    UPLOAD_BATCH_MAX   — max requests per window for batch file upload
    RATE_LIMIT_WINDOW  — sliding window duration in seconds
"""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user_id
from app.core.redis_client import processing_redis

logger = logging.getLogger("webgis.processing.rate_limiter")

UPLOAD_SINGLE_MAX: int = 5   # POST /api/segy-files/upload
UPLOAD_BATCH_MAX: int = 3    # POST /api/segy-files/upload/batch
RATE_LIMIT_WINDOW: int = 60  # seconds


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
    redis_client = getattr(processing_redis, "_client", None)
    if redis_client and processing_redis.is_available():
        try:
            now = time.time()
            cutoff = now - window_seconds
            r_key = f"ratelimit:{key}"

            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(r_key, 0, cutoff)
            pipe.zcard(r_key)
            results = pipe.execute()

            current_count = results[1]
            if current_count >= max_requests:
                return False

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


def upload_rate_limit(max_requests: int, window_seconds: int = RATE_LIMIT_WINDOW) -> Callable[..., None]:
    """
    Dependency factory: rate limit upload endpoints.
    """
    def dependency(
        request: Request,
        user_id: int = Depends(get_current_user_id),
    ) -> None:
        key = f"user:{user_id}" if user_id is not None else f"ip:{_get_client_ip(request)}"

        if not is_rate_limited(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency

