from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
from .postgres import close_connection as close_postgres
from ..api.db.clickhouse_client import close_clickhouse_clients
from ..api.db.supabase_client import close_supabase_clients

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting up AgentOps API...")

    yield

    logger.info("Shutting down AgentOps API...")

    try:
        close_postgres()
        logger.info("PostgreSQL connections closed")
    except Exception as e:
        logger.error(f"Error closing PostgreSQL: {e}")

    try:
        await close_clickhouse_clients()
        logger.info("ClickHouse connections closed")
    except Exception as e:
        logger.error(f"Error closing ClickHouse: {e}")

    try:
        await close_supabase_clients()
        logger.info("Supabase clients closed")
    except Exception as e:
        logger.error(f"Error closing Supabase: {e}")
