import asyncio
import threading
from typing import Annotated

from clickhouse_connect import get_async_client, get_client
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.client import Client
from fastapi import Depends

from agentops.api.environment import (
    CLICKHOUSE_DATABASE,
    CLICKHOUSE_HOST,
    CLICKHOUSE_PASSWORD,
    CLICKHOUSE_PORT,
    CLICKHOUSE_USER,
    CLICKHOUSE_SECURE,
)

# Global variables to store client instances
clickhouse = None
async_clickhouse = None


# Create locks for thread-safe initialization
_clickhouse_lock = threading.Lock()
_async_clickhouse_lock = asyncio.Lock()


class ConnectionConfig:
    """
    Connection configuration for Supabase.

    This is an intermediary because it allows us to easily modify the vars in tests.
    """

    host: str = CLICKHOUSE_HOST
    port: str | int = CLICKHOUSE_PORT
    database: str = CLICKHOUSE_DATABASE
    username: str = CLICKHOUSE_USER
    password: str = CLICKHOUSE_PASSWORD
    secure: bool = CLICKHOUSE_SECURE

    def __init__(self) -> None:
        """Non-instantiable class has a lower chance of being printed."""
        raise NotImplementedError("Cannot instantiate ConnectionConfig.")

    @classmethod
    def to_connection_dict(cls) -> dict[str, str | int]:
        """
        Convert the connection configuration to a dictionary that can be passed
        as kwargs to get_client and get_async_client.

        Returns:
            dict[str, str | int]: The connection configuration as a dictionary.
        """
        return {
            'host': cls.host,
            'port': cls.port,
            'database': cls.database,
            'username': cls.username,
            'password': cls.password,
            'secure': cls.secure,
        }


def get_clickhouse():
    """
    FastAPI dependency to get the synchronous ClickHouse client.
    This allows for proper dependency injection and easier testing.

    Returns:
        Client: The synchronous ClickHouse client instance
    """
    global clickhouse

    if clickhouse is None:
        with _clickhouse_lock:
            # Check again inside the lock to prevent race conditions
            if clickhouse is None:
                clickhouse = get_client(**ConnectionConfig.to_connection_dict())
    return clickhouse


async def get_async_clickhouse():
    """
    FastAPI dependency to get the async ClickHouse client.
    This allows for proper dependency injection and easier testing.

    Returns:
        AsyncClient: The async ClickHouse client instance
    """
    global async_clickhouse

    # Check again inside the lock to prevent race conditions
    if async_clickhouse is None:
        async with _async_clickhouse_lock:
            # Check again inside the lock to prevent race conditions
            if async_clickhouse is None:
                async_clickhouse = await get_async_client(**ConnectionConfig.to_connection_dict())
    return async_clickhouse


# Annotated dependencies for better type hinting
AsyncClickHouseClient = Annotated[AsyncClient, Depends(get_async_clickhouse)]
ClickHouseClient = Annotated[Client, Depends(get_clickhouse)]


async def close_clickhouse_clients():
    """
    Close the ClickHouse client connections.
    """
    global clickhouse, async_clickhouse

    try:
        if clickhouse is not None:
            clickhouse.close()
            clickhouse = None
    except Exception as e:
        # Log the error but don't raise - we still want to try closing the async client
        import logging

        logging.getLogger(__name__).error(f"Error closing ClickHouse sync client: {e}")

    try:
        if async_clickhouse is not None:
            await async_clickhouse.close()
            async_clickhouse = None
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Error closing ClickHouse async client: {e}")
