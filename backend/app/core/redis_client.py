import json
import logging
import os
from typing import Any, Optional
from dotenv import load_dotenv
import redis

load_dotenv()
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Connection pool maintains reusable sockets
pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_timeout=2.0,
)


def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=pool)


class CacheManager:
    @staticmethod
    def build_forecast_key(product_id: int, version: str = "v1") -> str:
        return f"forecast:{version}:product:{product_id}"

    @classmethod
    def get_json(cls, key: str) -> Optional[dict]:
        try:
            client = get_redis_client()
            data = client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("Redis read error on key '%s': %s", key, e)
            return None

    @classmethod
    def set_json(cls, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        try:
            client = get_redis_client()
            serialized = json.dumps(value)
            client.set(name=key, value=serialized, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning("Redis write error on key '%s': %s", key, e)
            return False

    @classmethod
    def invalidate_product(cls, product_id: int) -> bool:
        try:
            client = get_redis_client()
            pattern = f"forecast:*:product:{product_id}"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
                logger.info("Invalidated %d cache keys for product %d", len(keys), product_id)
            # Also invalidate fleet dashboard summary
            client.delete("dashboard:summary")
            return True
        except Exception as e:
            logger.warning("Redis invalidation error for product %d: %s", product_id, e)
            return False