import json
import logging
from typing import Any, Optional

try:
    import redis
except ImportError:
    redis = None

from app.config import settings

logger = logging.getLogger("webgis.redis.data_serving")


class RedisClient:
    """Thread-safe Singleton Redis Client for Data Serving (MVT & GeoJSON Cache)."""

    _instance: Optional["RedisClient"] = None
    _pool: Optional[Any] = None

    def __new__(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_pool()
        return cls._instance

    def _init_pool(self) -> None:
        if redis is None:
            logger.warning("Redis package is not installed. Operating in fallback mode.")
            self._client = None
            self._warned = True
            return

        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=30,
                decode_responses=False,  # Keep binary support for MVT tiles (.pbf)
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                protocol=2,  # RESP2 protocol compatibility for all Redis versions (Windows/Linux/Docker)
            )
            self._client = redis.Redis(connection_pool=self._pool)
            self._warned = False
        except Exception as exc:
            logger.warning(f"Redis initialization failed: {exc}. Cache will operate in fallback mode.")
            self._client = None
            self._warned = True

    def is_available(self) -> bool:
        if not settings.redis_cache_enabled or not self._client:
            return False
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def get_bytes(self, key: str) -> Optional[bytes]:
        if not settings.redis_cache_enabled or not self._client:
            return None
        try:
            val = self._client.get(key)
            if val is not None and isinstance(val, (bytes, bytearray)):
                return bytes(val)
            return None
        except Exception as exc:
            if not getattr(self, "_warned", False):
                logger.warning(f"Redis GET failed for key {key}: {exc}. Bypassing cache.")
                self._warned = True
            return None

    def set_bytes(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        if not settings.redis_cache_enabled or not self._client or value is None:
            return False
        try:
            expire = ttl or settings.redis_mvt_ttl_seconds
            return bool(self._client.setex(key, expire, value))
        except Exception as exc:
            logger.debug(f"Redis SETEX bytes failed for {key}: {exc}")
            return False

    def get_json(self, key: str) -> Optional[Any]:
        if not settings.redis_cache_enabled or not self._client:
            return None
        try:
            raw = self._client.get(key)
            if raw:
                return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            return None
        except Exception as exc:
            logger.debug(f"Redis GET json failed for {key}: {exc}")
            return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not settings.redis_cache_enabled or not self._client or value is None:
            return False
        try:
            expire = ttl or settings.redis_blocks_ttl_seconds
            raw = json.dumps(value, ensure_ascii=False)
            return bool(self._client.setex(key, expire, raw.encode("utf-8")))
        except Exception as exc:
            logger.debug(f"Redis SETEX json failed for {key}: {exc}")
            return False

    def delete(self, key: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.delete(key))
        except Exception as exc:
            logger.debug(f"Redis DELETE failed for {key}: {exc}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Scan and delete all keys matching a glob pattern (e.g. 'mvt:*', 'blocks:*')."""
        if not self._client:
            return 0
        try:
            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += self._client.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"[REDIS CACHE INVALIDATED] Deleted {deleted_count} keys matching pattern: '{pattern}'")
            return deleted_count
        except Exception as exc:
            logger.warning(f"Redis delete_pattern failed for {pattern}: {exc}")
            return 0


# Global singleton instance
redis_cache = RedisClient()
