import json
import logging
from typing import Any, Callable, Optional

try:
    import redis
except ImportError:
    redis = None

from app.core.config import settings

logger = logging.getLogger("webgis.redis.processing")


class ProcessingRedisClient:
    """Thread-safe Singleton Redis Client for SEG-Y Processing Service."""

    _instance: Optional["ProcessingRedisClient"] = None

    def __new__(cls) -> "ProcessingRedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_pools()
        return cls._instance

    def _init_pools(self) -> None:
        if redis is None:
            logger.warning("Redis package is not installed. Operating in fallback mode.")
            self._task_client = None
            self._cache_client = None
            self._warned = True
            return

        try:
            # Primary pool for tasks and Pub/Sub (db 1)
            self._task_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                protocol=2,  # RESP2 protocol compatibility
            )
            self._task_client = redis.Redis(connection_pool=self._task_pool)

            # Secondary pool for invalidating data-serving cache (db 0)
            self._cache_pool = redis.ConnectionPool.from_url(
                settings.REDIS_DATA_SERVING_URL,
                max_connections=10,
                decode_responses=True,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                protocol=2,  # RESP2 protocol compatibility
            )
            self._cache_client = redis.Redis(connection_pool=self._cache_pool)
            self._warned = False
        except Exception as exc:
            logger.warning(f"Processing Redis initialization failed: {exc}. Operating in fallback mode.")
            self._task_client = None
            self._cache_client = None
            self._warned = True

    def is_available(self) -> bool:
        if not settings.REDIS_ENABLED or not self._task_client:
            return False
        try:
            return bool(self._task_client.ping())
        except Exception:
            return False

    # ── Task State Management (Key-Value in DB 1) ──────────────────────────
    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not settings.REDIS_ENABLED or not self._task_client or value is None:
            return False
        try:
            expire = ttl or settings.REDIS_TASK_TTL_SECONDS
            raw = json.dumps(value, ensure_ascii=False)
            return bool(self._task_client.setex(key, expire, raw))
        except Exception as exc:
            logger.debug(f"Redis SETEX json failed for {key}: {exc}")
            return False

    def get_json(self, key: str) -> Optional[Any]:
        if not settings.REDIS_ENABLED or not self._task_client:
            return None
        try:
            raw = self._task_client.get(key)
            if raw:
                return json.loads(raw)
            return None
        except Exception as exc:
            logger.debug(f"Redis GET json failed for {key}: {exc}")
            return None

    def set_task_status(self, task_id: str, task_dict: dict, ttl: Optional[int] = None) -> bool:
        return self.set_json(f"task:{task_id}", task_dict, ttl=ttl)

    def get_task_status(self, task_id: str) -> Optional[dict]:
        return self.get_json(f"task:{task_id}")

    # ── Real-time Pub/Sub Messaging ────────────────────────────────────────
    def publish(self, channel: str, message: Any) -> int:
        if not settings.REDIS_ENABLED or not self._task_client:
            return 0
        try:
            raw = json.dumps(message, ensure_ascii=False) if not isinstance(message, (str, bytes)) else message
            return self._task_client.publish(channel, raw)
        except Exception as exc:
            logger.debug(f"Redis publish failed: {exc}")
            return 0

    def publish_progress(self, message: dict, channel: str = "segy_task_updates") -> int:
        return self.publish(channel, message)

    # ── Cross-Service Cache Invalidation (DB 0 for Data-Serving) ───────────
    def invalidate_data_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache keys in data-serving Redis (db 0) matching pattern (e.g. 'mvt:*', 'blocks:*')."""
        if not self._cache_client:
            return 0
        try:
            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = self._cache_client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += self._cache_client.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"[REDIS CACHE INVALIDATED] Deleted {deleted_count} keys in DB 0 matching pattern: '{pattern}'")
            return deleted_count
        except Exception as exc:
            logger.warning(f"Cross-service cache invalidation failed for pattern {pattern}: {exc}")
            return 0


# Global singleton instance
processing_redis = ProcessingRedisClient()
redis_task_client = processing_redis
redis_data_serving_pool = processing_redis

