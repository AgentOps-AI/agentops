from agentops.api.log_config import logger
from .environment import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_USER,
    REDIS_PASSWORD,
)


if REDIS_HOST and REDIS_PORT:
    from redis import Redis

    logger.info("Using Redis cache for production.")

    _redis_creds = {
        'host': REDIS_HOST,
        'port': REDIS_PORT,
        'decode_responses': True,
    }
    if REDIS_USER and REDIS_PASSWORD:
        _redis_creds['username'] = REDIS_USER
        _redis_creds['password'] = REDIS_PASSWORD

    _backend = Redis(**_redis_creds)

else:
    import os
    import sqlite3
    from collections import defaultdict
    import time

    class BaseDevCache:
        """
        Base class for local development cache.

        Includes noops for methods we don't need in local development.
        """

        def zadd(self, key: str, mapping: dict) -> None:
            logger.warning("[agentops.common.cache] zadd() is not implemented in development")

        def zremrangebyscore(self, key: str, min: int, max: int) -> None:
            logger.warning("[agentops.common.cache] zremrangebyscore() is not implemented in development")

        def zcount(self, key: str, min: int, max: int) -> int:
            logger.warning("[agentops.common.cache] zcount() is not implemented in development")
            return 0

    class SimpleCache(BaseDevCache):
        """In-memory cache for local development."""

        def __init__(self):
            self.store = defaultdict(lambda: None)
            self.expiry = {}

        def get(self, key: str) -> str | None:
            if key in self.expiry and time.time() > self.expiry[key]:
                del self.store[key]
                del self.expiry[key]
                return None
            return self.store[key]

        def setex(self, key: str, expiry: int, value: str) -> None:
            self.store[key] = value
            self.expiry[key] = time.time() + expiry

        def expire(self, key: str, expiry: int) -> None:
            if key in self.store:
                self.expiry[key] = time.time() + expiry

        def delete(self, key: str) -> None:
            if key in self.store:
                del self.store[key]
            if key in self.expiry:
                del self.expiry[key]

    class SQLiteCache(BaseDevCache):
        """SQLite-backed cache for local development."""

        def __init__(self):
            self.db_path = os.path.join(os.getcwd(), "cache.db")
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expiry INTEGER
                )
            """)
            self.conn.commit()

        def get(self, key: str) -> str | None:
            cursor = self.conn.execute("SELECT value, expiry FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                value, expiry = row
                if expiry is not None and time.time() > expiry:
                    self.delete(key)
                    return None
                return value
            return None

        def setex(self, key: str, expiry: int, value: str) -> None:
            expiry_time = int(time.time() + expiry)
            self.conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, expiry)
                VALUES (?, ?, ?)
            """,
                (key, value, expiry_time),
            )
            self.conn.commit()

        def expire(self, key: str, expiry: int) -> None:
            expiry_time = int(time.time() + expiry)
            self.conn.execute(
                """
                UPDATE cache SET expiry = ? WHERE key = ?
            """,
                (expiry_time, key),
            )
            self.conn.commit()

        def delete(self, key: str) -> None:
            self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self.conn.commit()

    if os.path.exists("/.dockerenv"):
        logger.info("Using in-memory cache for local development.")
        _backend = SimpleCache()
    elif os.environ.get('GITHUB_ACTIONS') == 'true':
        logger.info("Using in-memory cache for GitHub Actions.")
        _backend = SimpleCache()
    else:
        logger.info("Using SQLite cache for local development.")
        _backend = SQLiteCache()


def get(key: str) -> str | None:
    """Get a value from the cache by key."""
    return _backend.get(key)


def setex(key: str, expiry: int, value: str) -> None:
    """Set a value in the cache with an expiry time."""
    _backend.setex(key, expiry, value)


def expire(key: str, expiry: int) -> None:
    """Set the expiry time for a key in the cache."""
    _backend.expire(key, expiry)


def delete(key: str) -> None:
    """Delete a key from the cache."""
    _backend.delete(key)


def zadd(key: str, mapping: dict) -> None:
    """Add elements to a sorted set."""
    _backend.zadd(key, mapping)


def zremrangebyscore(key: str, min: int, max: int) -> None:
    """Remove elements from a sorted set by score."""
    _backend.zremrangebyscore(key, min, max)


def zcount(key: str, min: int, max: int) -> int:
    """Count elements in a sorted set by score."""
    return _backend.zcount(key, min, max)
