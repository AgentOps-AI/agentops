import atexit
import signal
import logging
from psycopg_pool import ConnectionPool
from .environment import (
    SUPABASE_HOST,
    SUPABASE_PORT,
    SUPABASE_DATABASE,
    SUPABASE_USER,
    SUPABASE_PASSWORD,
    SUPABASE_MIN_POOL_SIZE,
    SUPABASE_MAX_POOL_SIZE,
    SUPABASE_SSLMODE,
)

logger = logging.getLogger(__name__)
_supabase_pool: ConnectionPool | None = None


class ConnectionConfig:
    """
    Connection configuration for Supabase.

    This is an intermediary because it allows us to easily modify the vars in tests.
    """

    host: str = SUPABASE_HOST
    port: str | int = SUPABASE_PORT
    database: str = SUPABASE_DATABASE
    user: str = SUPABASE_USER
    password: str = SUPABASE_PASSWORD

    def __init__(self) -> None:
        """Non-instantiable class has a lower chance of being printed."""
        raise NotImplementedError("Cannot instantiate ConnectionConfig.")

    @classmethod
    def to_connection_string(cls, protocol: str = "postgresql") -> str:
        """Format config as a URL connection string."""
        return f"{protocol}://{cls.user}:{cls.password}@{cls.host}:{cls.port}/{cls.database}?sslmode={SUPABASE_SSLMODE}"


def _cleanup_handler(signum=None, frame=None):
    """Universal cleanup handler for both signals and atexit."""
    logger.info(f"Cleanup handler called (signal: {signum})")
    close_connection()


def get_connection(config: type[ConnectionConfig] = ConnectionConfig) -> ConnectionPool:
    """
    Get the global Supabase Postgres connection pool.
    """
    global _supabase_pool

    if _supabase_pool is None:
        _supabase_pool = ConnectionPool(
            config.to_connection_string(),
            min_size=SUPABASE_MIN_POOL_SIZE,
            max_size=SUPABASE_MAX_POOL_SIZE,
        )

        # Register cleanup handlers
        atexit.register(_cleanup_handler)
        signal.signal(signal.SIGTERM, _cleanup_handler)
        signal.signal(signal.SIGINT, _cleanup_handler)

        logger.info(f"PostgreSQL pool created: min={SUPABASE_MIN_POOL_SIZE}, max={SUPABASE_MAX_POOL_SIZE}")

    return _supabase_pool


def close_connection() -> None:
    """
    Close the global Supabase Postgres connection pool.
    """
    global _supabase_pool

    if _supabase_pool is not None:
        try:
            _supabase_pool.close()
            logger.info("PostgreSQL connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing PostgreSQL pool: {e}")
        finally:
            _supabase_pool = None
