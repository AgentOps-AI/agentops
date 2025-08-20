from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


"""
"this is a feature not a bug" LMAO
"""


# FIXME: Remove test skip after https://github.com/AgentOps-AI/agentops/issues/820
pytestmark = [pytest.mark.skip]


@pytest.mark.asyncio
async def test_metrics_dual_endpoints(async_test_client, valid_jwt):
    """
    Test that both /metrics and /meterics endpoints return the same response.
    This verifies our dual endpoint feature works correctly.

    Note: This test just verifies that both endpoints exist and return the same response.
    It's not testing the actual metrics functionality, just the routing.
    """
    # Mock token verification
    with patch('agentops.api.auth.get_jwt_token', return_value={'project_id': 'test-project'}):
        # Test the /metrics endpoint
        metrics_response = await async_test_client.get(
            "/v4/metrics/test", headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        # Test the /meterics endpoint
        meterics_response = await async_test_client.get(
            "/v4/meterics/test", headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        # Verify both endpoints return the same status code
        assert metrics_response.status_code == meterics_response.status_code

        # Verify both endpoints return the same response
        assert metrics_response.json() == meterics_response.json()

        # Verify the response content
        assert metrics_response.json() == {"message": "Test endpoint working"}


@pytest.mark.asyncio
async def test_metrics_other_endpoints_dual_behavior(async_test_client, valid_jwt):
    """
    Test that other metrics endpoints like /trace/{trace_id} are also
    accessible via both /metrics and /meterics paths.

    This test mocks the database calls to isolate the routing functionality.
    """
    # Mock data
    trace_id = "1234567890abcdef"
    # Create proper datetime objects for the timestamps
    start_time = datetime(2023, 1, 1, 0, 0, 0)
    end_time = datetime(2023, 1, 1, 0, 0, 1)

    mock_data = [
        {
            "SpanId": "span1",
            "TraceId": trace_id,
            "SpanName": "test-span",
            "ServiceName": "test-service",
            "Duration": 100000000,  # duration in nanoseconds
            "SpanAttributes": {
                "gen_ai.usage.prompt_tokens": 10,
                "gen_ai.usage.completion_tokens": 20,
                "gen_ai.usage.total_tokens": 30,
                "gen_ai.request.model": "test-model",
                "gen_ai.system": "test-system",
            },
            "ResourceAttributes": {"agentops.project.id": "test-project"},
            "StartTime": start_time,  # Use datetime object instead of string
            "EndTime": end_time,  # Use datetime object instead of string
        }
    ]

    # Create a completely mocked response for the async clickhouse client
    mock_result = MagicMock()
    mock_result.named_results.return_value = mock_data

    # Set up AsyncMock for query method
    mock_query = AsyncMock(return_value=mock_result)

    # Create patches for token and query building
    token_patch = patch('agentops.api.auth.get_jwt_token', return_value={'project_id': 'test-project'})
    query_patch = patch(
        'agentops.api.routes.v4.metrics.queries.build_span_metrics_query',
        return_value=("SELECT mock_query", {"trace_id": trace_id}),
    )

    # Patch the token_metrics and duration_metrics calculation functions
    token_metrics_patch = patch(
        'agentops.api.routes.v4.metrics.utils.calculate_token_metrics',
        return_value={"token_usage": 100, "model_usage": {}, "system_usage": {}},
    )
    duration_metrics_patch = patch(
        'agentops.api.routes.v4.metrics.utils.calculate_duration_metrics',
        return_value={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_duration_ns": 100000000,
        },
    )

    # This is the critical part - directly patch the clickhouse query method in the route
    query_method_patch = patch('clickhouse_connect.driver.asyncclient.AsyncClient.query', mock_query)

    with token_patch, query_patch, query_method_patch, token_metrics_patch, duration_metrics_patch:
        # Test the /metrics/trace/{trace_id} endpoint
        metrics_response = await async_test_client.get(
            f"/v4/metrics/trace/{trace_id}", headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        # Test the /meterics/trace/{trace_id} endpoint
        meterics_response = await async_test_client.get(
            f"/v4/meterics/trace/{trace_id}", headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        # Verify both endpoints return the same status code
        assert metrics_response.status_code == meterics_response.status_code

        # Both endpoints should return the same response
        assert metrics_response.json() == meterics_response.json()

        # Verify the mock was called
        assert (
            mock_query.call_count >= 2
        ), "The ClickHouse query method should be called at least twice (once for each endpoint)"

        # If the status is 404, ensure that both endpoints return the same error message
        if metrics_response.status_code == 404:
            assert "not_found" in metrics_response.json()["detail"]["error"]
            assert trace_id in metrics_response.json()["detail"]["message"]
