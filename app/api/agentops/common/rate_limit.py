import time

from . import cache
from .environment import (
    RATE_LIMIT_ENABLE,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_COUNT,
    RATE_LIMIT_EXPIRY,
)

WINDOW_US = RATE_LIMIT_WINDOW * 1_000_000  # convert to microseconds


def _key(ip: str) -> str:
    """Create a Redis key for the IP address."""
    return f"agentops.rate:{ip}"


def _now_us() -> int:
    """Get the current time in microseconds."""
    return int(time.time() * 1_000_000)


def record_interaction(ip: str) -> None:
    """
    Record an interaction from the given IP address.
    Uses a sliding window approach with sorted sets in Redis.
    """
    key, now = _key(ip), _now_us()

    cache.zremrangebyscore(key, 0, now - WINDOW_US)
    cache.zadd(key, {str(now): now})
    cache.expire(key, RATE_LIMIT_EXPIRY)


def is_blocked(ip: str) -> bool:
    """
    Check if the IP address is rate-limited.
    Returns True if the number of recent requests exceeds RATE_LIMIT_COUNT.
    Always returns False if RATE_LIMIT_ENABLE is False.
    """
    if not RATE_LIMIT_ENABLE:
        return False

    key, now = _key(ip), _now_us()

    count = cache.zcount(key, now - WINDOW_US, now)
    return count > RATE_LIMIT_COUNT


def clear(ip: str) -> None:
    """
    Clear rate limit records for the given IP.
    This is primarily used for testing.
    """
    key = _key(ip)
    cache.delete(key)


def get_count(ip: str) -> int:
    """
    Get the current count of requests for the given IP within the rate limit window.
    This is primarily used for testing.
    """
    key, now = _key(ip), _now_us()
    return cache.zcount(key, now - WINDOW_US, now)
