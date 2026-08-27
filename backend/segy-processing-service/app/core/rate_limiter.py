"""
In-memory Sliding Window Rate Limiter — segy-processing-service.

Thread-safe, zero external dependency.

Upgrade path to Redis (Phase 2):
    Replace SlidingWindowRateLimiter with RedisRateLimiter using the same
    is_allowed(key, max_requests, window_seconds) interface.
    No changes needed in routes or dependency signatures.

Rate limit constants (configurable at module level):
    UPLOAD_SINGLE_MAX  — max requests per window for single file upload
    UPLOAD_BATCH_MAX   — max requests per window for batch file upload
    RATE_LIMIT_WINDOW  — sliding window duration in seconds
"""

import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user_id

# ---------------------------------------------------------------------------
# Rate limit configuration
# These constants can be extracted to a config/settings module in the future.
# ---------------------------------------------------------------------------
UPLOAD_SINGLE_MAX: int = 5   # POST /api/segy-files/upload
UPLOAD_BATCH_MAX: int = 3    # POST /api/segy-files/upload/batch
RATE_LIMIT_WINDOW: int = 60  # seconds


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


def upload_rate_limit(max_requests: int, window_seconds: int = RATE_LIMIT_WINDOW) -> Callable[..., None]:
    """
    Dependency factory: rate limit upload endpoints.

    Key strategy:
      - Authenticated request (JWT present) → keyed by user_id
      - Unauthenticated request             → keyed by client IP

    FastAPI deduplicates get_current_user_id per request — no extra JWT
    decode overhead when the route already calls get_current_user_id.

    Args:
        max_requests: Maximum allowed requests within the window.
        window_seconds: Sliding window duration in seconds.

    Returns:
        A FastAPI dependency that raises HTTP 429 when limit is exceeded.
    """
    def dependency(
        request: Request,
        user_id: int | None = Depends(get_current_user_id),
    ) -> None:
        if user_id is not None:
            key = f"user:{user_id}"
        else:
            key = f"ip:{_get_client_ip(request)}"

        if not _limiter.is_allowed(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.",
                headers={"Retry-After": str(window_seconds)},
            )
    return dependency
