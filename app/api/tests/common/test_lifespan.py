import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agentops.common.lifespan import lifespan


class TestLifespan:
    """Tests for the lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_normal_flow(self):
        """Test that lifespan yields control and closes all connections on exit."""
        # Create a mock FastAPI app
        mock_app = MagicMock()

        # Mock all the close functions
        with (
            patch('agentops.common.lifespan.close_postgres') as mock_close_postgres,
            patch('agentops.common.lifespan.close_clickhouse_clients') as mock_close_clickhouse,
            patch('agentops.common.lifespan.close_supabase_clients') as mock_close_supabase,
        ):
            # Make the async close functions return coroutines
            mock_close_clickhouse.return_value = AsyncMock()()
            mock_close_supabase.return_value = AsyncMock()()

            # Use the lifespan context manager
            async with lifespan(mock_app) as _:
                # Verify we're in the startup phase
                # (The function should yield here)
                pass

            # After exiting the context, all cleanup functions should be called
            mock_close_postgres.assert_called_once()
            mock_close_clickhouse.assert_called_once()
            mock_close_supabase.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_postgres_error_handling(self):
        """Test that lifespan continues cleanup even if PostgreSQL close fails."""
        mock_app = MagicMock()

        with (
            patch('agentops.common.lifespan.close_postgres') as mock_close_postgres,
            patch('agentops.common.lifespan.close_clickhouse_clients') as mock_close_clickhouse,
            patch('agentops.common.lifespan.close_supabase_clients') as mock_close_supabase,
            patch('agentops.common.lifespan.logger') as mock_logger,
        ):
            # Make PostgreSQL close raise an exception
            mock_close_postgres.side_effect = Exception("PostgreSQL connection error")

            # Make the async close functions return coroutines
            mock_close_clickhouse.return_value = AsyncMock()()
            mock_close_supabase.return_value = AsyncMock()()

            async with lifespan(mock_app):
                pass

            # Verify error was logged
            mock_logger.error.assert_any_call("Error closing PostgreSQL: PostgreSQL connection error")

            # Verify other cleanup functions were still called
            mock_close_clickhouse.assert_called_once()
            mock_close_supabase.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_clickhouse_error_handling(self):
        """Test that lifespan continues cleanup even if ClickHouse close fails."""
        mock_app = MagicMock()

        with (
            patch('agentops.common.lifespan.close_postgres') as mock_close_postgres,
            patch('agentops.common.lifespan.close_clickhouse_clients') as mock_close_clickhouse,
            patch('agentops.common.lifespan.close_supabase_clients') as mock_close_supabase,
            patch('agentops.common.lifespan.logger') as mock_logger,
        ):
            # Make ClickHouse close raise an exception
            async def raise_clickhouse_error():
                raise Exception("ClickHouse connection error")

            mock_close_clickhouse.side_effect = raise_clickhouse_error
            mock_close_supabase.return_value = AsyncMock()()

            async with lifespan(mock_app):
                pass

            # Verify error was logged
            mock_logger.error.assert_any_call("Error closing ClickHouse: ClickHouse connection error")

            # Verify other cleanup functions were still called
            mock_close_postgres.assert_called_once()
            mock_close_supabase.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_supabase_error_handling(self):
        """Test that lifespan handles Supabase close errors gracefully."""
        mock_app = MagicMock()

        with (
            patch('agentops.common.lifespan.close_postgres') as mock_close_postgres,
            patch('agentops.common.lifespan.close_clickhouse_clients') as mock_close_clickhouse,
            patch('agentops.common.lifespan.close_supabase_clients') as mock_close_supabase,
            patch('agentops.common.lifespan.logger') as mock_logger,
        ):
            # Make Supabase close raise an exception
            async def raise_supabase_error():
                raise Exception("Supabase client error")

            mock_close_clickhouse.return_value = AsyncMock()()
            mock_close_supabase.side_effect = raise_supabase_error

            async with lifespan(mock_app):
                pass

            # Verify error was logged
            mock_logger.error.assert_any_call("Error closing Supabase: Supabase client error")

            # Verify other cleanup functions were still called
            mock_close_postgres.assert_called_once()
            mock_close_clickhouse.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_all_errors(self):
        """Test that lifespan handles errors from all cleanup functions."""
        mock_app = MagicMock()

        with (
            patch('agentops.common.lifespan.close_postgres') as mock_close_postgres,
            patch('agentops.common.lifespan.close_clickhouse_clients') as mock_close_clickhouse,
            patch('agentops.common.lifespan.close_supabase_clients') as mock_close_supabase,
            patch('agentops.common.lifespan.logger') as mock_logger,
        ):
            # Make all close functions raise exceptions
            mock_close_postgres.side_effect = Exception("PostgreSQL error")

            async def raise_clickhouse_error():
                raise Exception("ClickHouse error")

            async def raise_supabase_error():
                raise Exception("Supabase error")

            mock_close_clickhouse.side_effect = raise_clickhouse_error
            mock_close_supabase.side_effect = raise_supabase_error

            async with lifespan(mock_app):
                pass

            # Verify all errors were logged
            mock_logger.error.assert_any_call("Error closing PostgreSQL: PostgreSQL error")
            mock_logger.error.assert_any_call("Error closing ClickHouse: ClickHouse error")
            mock_logger.error.assert_any_call("Error closing Supabase: Supabase error")

            # Verify all cleanup functions were attempted
            mock_close_postgres.assert_called_once()
            mock_close_clickhouse.assert_called_once()
            mock_close_supabase.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_logging(self):
        """Test that lifespan logs startup and shutdown messages."""
        mock_app = MagicMock()

        with (
            patch('agentops.common.lifespan.close_postgres'),
            patch('agentops.common.lifespan.close_clickhouse_clients') as mock_close_clickhouse,
            patch('agentops.common.lifespan.close_supabase_clients') as mock_close_supabase,
            patch('agentops.common.lifespan.logger') as mock_logger,
        ):
            # Make the async close functions return coroutines
            mock_close_clickhouse.return_value = AsyncMock()()
            mock_close_supabase.return_value = AsyncMock()()

            async with lifespan(mock_app):
                # Verify startup message was logged
                mock_logger.info.assert_called_with("Starting up AgentOps API...")

            # Verify shutdown messages were logged
            mock_logger.info.assert_any_call("Shutting down AgentOps API...")
            mock_logger.info.assert_any_call("PostgreSQL connections closed")
            mock_logger.info.assert_any_call("ClickHouse connections closed")
            mock_logger.info.assert_any_call("Supabase clients closed")
