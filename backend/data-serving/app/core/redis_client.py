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

    def get_cache_stats(self) -> dict:
        """
        Lấy thống kê hiệu năng thời gian thực trực tiếp từ Redis engine:
        - keyspace_hits
        - keyspace_misses
        - total_requests (hits + misses)
        - hit_ratio (% thành công)
        - total_keys (tổng số key qua DBSIZE)
        - used_memory_human
        """
        default_stats = {
            "is_connected": False,
            "keyspace_hits": 0,
            "keyspace_misses": 0,
            "total_requests": 0,
            "hit_ratio": 0.0,
            "total_keys": 0,
            "used_memory_human": "0B",
        }
        if not self._client or not settings.redis_cache_enabled:
            return default_stats

        try:
            info_stats = self._client.info("stats")
            info_memory = self._client.info("memory")
            dbsize = self._client.dbsize()

            hits = int(info_stats.get("keyspace_hits", 0))
            misses = int(info_stats.get("keyspace_misses", 0))
            total = hits + misses
            # Nếu chưa phát sinh request nào, mặc định 100.0% nếu đã có keys, ngược lại 0.0%
            ratio = round((hits / total) * 100, 1) if total > 0 else (100.0 if dbsize > 0 else 0.0)

            return {
                "is_connected": True,
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "total_requests": total,
                "hit_ratio": ratio,
                "total_keys": int(dbsize),
                "used_memory_human": str(info_memory.get("used_memory_human", "0B")),
            }
        except Exception as exc:
            logger.warning(f"Lỗi khi truy vấn thông số thống kê Redis: {exc}")
            return default_stats

    def set_user_online(self, user_id: int, ttl_seconds: int = 90) -> None:
        """Ghi nhận người dùng đang Online vào Redis với thời gian hết hạn TTL (mặc định 90s)."""
        if not self._client or not settings.redis_cache_enabled:
            return
        try:
            self._client.set(f"user:online:{user_id}", "1", ex=ttl_seconds)
        except Exception as exc:
            logger.debug(f"Redis set_user_online failed for {user_id}: {exc}")

    def set_user_offline(self, user_id: int) -> None:
        """Xóa trạng thái Online khi người dùng đăng xuất (Logout)."""
        if not self._client or not settings.redis_cache_enabled:
            return
        try:
            self._client.delete(f"user:online:{user_id}")
        except Exception as exc:
            logger.debug(f"Redis set_user_offline failed for {user_id}: {exc}")

    def is_user_online(self, user_id: int) -> bool:
        """Kiểm tra một người dùng có đang Online hay không."""
        if not self._client or not settings.redis_cache_enabled:
            return False
        try:
            return bool(self._client.exists(f"user:online:{user_id}"))
        except Exception:
            return False

    def get_online_user_ids(self) -> set[int]:
        """Lấy danh sách tất cả ID người dùng đang Online (quét nhanh qua pattern user:online:*)."""
        if not self._client or not settings.redis_cache_enabled:
            return set()
        try:
            online_ids: set[int] = set()
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match="user:online:*", count=100)
                for k in keys:
                    key_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                    parts = key_str.split(":")
                    if len(parts) >= 3 and parts[2].isdigit():
                        online_ids.add(int(parts[2]))
                if cursor == 0:
                    break
            return online_ids
        except Exception as exc:
            logger.debug(f"Redis get_online_user_ids failed: {exc}")
            return set()


# Global singleton instance
redis_cache = RedisClient()

