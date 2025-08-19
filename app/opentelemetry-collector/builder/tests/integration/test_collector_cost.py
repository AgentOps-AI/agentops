import json
import os
import pytest
import time
import uuid
import subprocess
import docker
import requests
import jwt
import secrets
from decimal import Decimal
from typing import Dict, Any, List, Optional


@pytest.fixture(scope="module")
def docker_client():
    """Create a docker client."""
    return docker.from_env()


@pytest.fixture(scope="module")
def jwt_secret():
    """Generate a JWT secret for testing."""
    return secrets.token_urlsafe(64)


@pytest.fixture(scope="module")
def jwt_token(jwt_secret):
    """Generate a JWT token for authentication with the collector."""
    # Test payload matching the expected format
    payload = {
        "exp": int(time.time()) + 3600,  # Expires in 1 hour
        "aud": "authenticated",
        "project_id": "test-project-id",
        "api_key": "test-api-key"
    }
    
    # Generate the JWT token
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    
    # Write to .jwt file for the collector to use
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    jwt_path = os.path.join(project_root, '.jwt')
    with open(jwt_path, 'w') as f:
        f.write(token)
    
    return token


@pytest.fixture(scope="module")
def docker_compose_up(docker_client, jwt_secret):
    """Start the docker-compose services."""
    # Get the project root directory (4 levels up from this file)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    # Path to main project's migrations
    migrations_path = os.path.join(os.path.dirname(project_root), "clickhouse", "migrations")

    print("Starting docker-compose services...")
    # Set the JWT_SECRET environment variable for the collector
    env = os.environ.copy()
    env["JWT_SECRET"] = jwt_secret
    subprocess.run(["docker-compose", "up", "-d"], cwd=project_root, check=True, env=env)
    print("Docker compose started, waiting for services to be ready...")
    time.sleep(10)  # Give services time to start

    retry_count = 0
    while retry_count < 5:
        result = subprocess.run(
            ["docker-compose", "ps", "otelcollector"], cwd=project_root, capture_output=True, text=True
        )

        if "Up" in result.stdout and "otelcollector" in result.stdout:
            print("Collector service is running!")
            break

        time.sleep(5)
        retry_count += 1
        if retry_count == 5:
            raise Exception("Collector service did not start successfully")

    # Verify ClickHouse is running
    retry_count = 0
    while retry_count < 5:
        response = requests.get("http://localhost:8123/ping")
        if response.status_code == 200:
            print("ClickHouse service is running!")
            break

        time.sleep(5)
        retry_count += 1
        if retry_count == 5:
            raise Exception("ClickHouse service did not start successfully")

    # Apply migrations from the parent project
    print("Applying ClickHouse migrations...")
    migration_files = sorted([f for f in os.listdir(migrations_path) if f.endswith('.sql')])
    for migration_file in migration_files:
        print(f"  Running migration: {migration_file}")
        with open(os.path.join(migrations_path, migration_file), 'r') as f:
            sql = f.read()
            for command in sql.split(';'):
                if command.strip():
                    requests.post(
                        "http://localhost:8123/?database=otel_2", auth=("default", "password"), data=command
                    )

    print("Test environment is ready!")
    yield

    # Clean up after tests
    print("Cleaning up docker-compose services...")
    subprocess.run(["docker-compose", "down"], cwd=project_root, check=True)
    print("Cleanup complete!")


def create_span_data(
    project_id: str = "1c0ffdac-e7f7-494d-93f9-cac955f25de8",
    model: str = "gpt-4",
    prompt_tokens: int = 100,
    completion_tokens: int = 1000,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create span data for testing purposes.

    Args:
        project_id: The project ID to use
        model: LLM model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        trace_id: Optional trace ID, generates random one if not provided
        span_id: Optional span ID, generates random one if not provided

    Returns:
        Dictionary with the OTLP span data
    """
    # Generate random IDs if not provided
    if trace_id is None:
        trace_id = uuid.uuid4().hex.replace('-', '')
        # Ensure it's 16 bytes (32 hex chars)
        trace_id = trace_id[:32]

    if span_id is None:
        span_id = uuid.uuid4().hex.replace('-', '')[:16]  # 8 bytes (16 hex chars)

    # Current time in nanoseconds
    current_time_ns = int(time.time() * 1_000_000_000)

    # Create the span data structure
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": [{"key": "ProjectId", "value": {"stringValue": project_id}}]},
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "name": "test-span",
                                "traceId": trace_id,
                                "spanId": span_id,
                                "kind": 1,
                                "startTimeUnixNano": str(current_time_ns),
                                "endTimeUnixNano": str(current_time_ns + 100_000_000),  # 100ms later
                                "attributes": [
                                    {"key": "gen_ai.response.model", "value": {"stringValue": model}},
                                    {
                                        "key": "gen_ai.usage.prompt_tokens",
                                        "value": {"intValue": prompt_tokens},
                                    },
                                    {
                                        "key": "gen_ai.usage.completion_tokens",
                                        "value": {"intValue": completion_tokens},
                                    },
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }


def send_span(span_data: Dict[str, Any], jwt_token: str) -> requests.Response:
    """
    Send a span to the collector.

    Args:
        span_data: The span data to send
        jwt_token: JWT token for authentication

    Returns:
        Response from the collector
    """
    return requests.post(
        "http://localhost:4318/v1/traces",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {jwt_token}"},
        json=span_data,
    )


def generate_ids():
    """Generate a random trace ID and span ID for testing."""
    trace_id = uuid.uuid4().hex
    span_id = trace_id[:16]  # Use first 16 chars of trace_id for span_id
    return trace_id, span_id


def query_clickhouse(query: str) -> List[Dict[str, Any]]:
    """
    Query the ClickHouse database.

    Args:
        query: SQL query to execute

    Returns:
        List of dictionaries with query results
    """
    # Get ClickHouse connection parameters from environment or use defaults
    endpoint = "http://localhost:8123"
    username = "default"
    password = "password"
    database = "otel_2"

    # Execute the query
    url = f"{endpoint}/?database={database}"
    response = requests.post(
        url,
        auth=(username, password),
        data=query,
        params={"default_format": "JSONEachRow"},
    )

    # Parse the response
    if response.status_code == 200:
        results = []
        response_text = response.text.strip()

        if not response_text:
            return []

        for line in response_text.split('\n'):
            if line:
                results.append(json.loads(line))
        return results
    else:
        raise Exception(f"Query failed: {response.status_code} {response.text}")


@pytest.mark.usefixtures("docker_compose_up")
class TestCollectorCost:
    """Integration tests for the cost calculation in the collector."""

    def test_gpt4_span_cost_calculation(self, jwt_token):
        """Test that costs are calculated correctly for GPT-4."""
        # Generate unique IDs for this test
        trace_id, span_id = generate_ids()

        # Create span data for GPT-4
        span_data = create_span_data(
            model="gpt-4", prompt_tokens=100, completion_tokens=1000, trace_id=trace_id, span_id=span_id
        )

        # Send the span to the collector
        response = send_span(span_data, jwt_token)
        assert response.status_code == 200, f"Failed to send span: {response.text}"

        # Wait for the span to be processed
        time.sleep(5)

        # Query ClickHouse for the span using trace_id
        query = f"""
        SELECT
            SpanName,
            TraceId,
            SpanAttributes['gen_ai.response.model'] as model,
            SpanAttributes['gen_ai.usage.prompt_tokens'] as prompt_tokens,
            SpanAttributes['gen_ai.usage.completion_tokens'] as completion_tokens,
            SpanAttributes['gen_ai.usage.prompt_cost'] as prompt_cost,
            SpanAttributes['gen_ai.usage.completion_cost'] as completion_cost
        FROM otel_traces
        WHERE
            TraceId = '{trace_id}'
        LIMIT 1
        """

        results = query_clickhouse(query)
        span = results[0]

        assert span["model"] == "gpt-4"
        assert int(span["prompt_tokens"]) == 100
        assert int(span["completion_tokens"]) == 1000

        prompt_cost = Decimal(span["prompt_cost"])
        completion_cost = Decimal(span["completion_cost"])
        assert prompt_cost > 0, "Prompt cost should be positive"
        assert completion_cost > 0, "Completion cost should be positive"

    def test_claude3_span_cost_calculation(self, jwt_token):
        """Test that costs are calculated correctly for Claude-3 models."""
        # Generate unique IDs for this test
        trace_id, span_id = generate_ids()

        # Create span data for Claude-3-opus
        span_data = create_span_data(
            model="claude-3-opus-20240229",
            prompt_tokens=200,
            completion_tokens=500,
            trace_id=trace_id,
            span_id=span_id,
        )

        # Send the span to the collector
        response = send_span(span_data, jwt_token)
        assert response.status_code == 200, f"Failed to send span: {response.text}"

        # Wait for the span to be processed
        time.sleep(5)

        # Query ClickHouse for the span using trace_id
        query = f"""
        SELECT
            SpanName,
            TraceId,
            SpanAttributes['gen_ai.response.model'] as model,
            SpanAttributes['gen_ai.usage.prompt_tokens'] as prompt_tokens,
            SpanAttributes['gen_ai.usage.completion_tokens'] as completion_tokens,
            SpanAttributes['gen_ai.usage.prompt_cost'] as prompt_cost,
            SpanAttributes['gen_ai.usage.completion_cost'] as completion_cost
        FROM otel_traces
        WHERE
            TraceId = '{trace_id}'
        LIMIT 1
        """

        results = query_clickhouse(query)
        span = results[0]

        assert span["model"] == "claude-3-opus-20240229"
        assert int(span["prompt_tokens"]) == 200
        assert int(span["completion_tokens"]) == 500

        prompt_cost = Decimal(span["prompt_cost"])
        completion_cost = Decimal(span["completion_cost"])
        assert prompt_cost > 0, "Prompt cost should be positive"
        assert completion_cost > 0, "Completion cost should be positive"

    def test_unknown_model_no_cost_calculation(self, jwt_token):
        """Test that no costs are calculated for unknown models."""
        # Generate unique IDs for this test
        trace_id, span_id = generate_ids()

        # Create span data for an unknown model
        span_data = create_span_data(
            model="unknown-model-xyz",
            prompt_tokens=100,
            completion_tokens=200,
            trace_id=trace_id,
            span_id=span_id,
        )

        # Send the span to the collector
        response = send_span(span_data, jwt_token)
        assert response.status_code == 200, f"Failed to send span: {response.text}"

        # Wait for the span to be processed
        time.sleep(5)

        # Query ClickHouse for the span using trace_id
        query = f"""
        SELECT
            SpanName,
            TraceId,
            SpanAttributes['gen_ai.response.model'] as model,
            SpanAttributes['gen_ai.usage.prompt_tokens'] as prompt_tokens,
            SpanAttributes['gen_ai.usage.completion_tokens'] as completion_tokens,
            SpanAttributes['gen_ai.usage.prompt_cost'] as prompt_cost,
            SpanAttributes['gen_ai.usage.completion_cost'] as completion_cost
        FROM otel_traces
        WHERE
            TraceId = '{trace_id}'
        LIMIT 1
        """

        results = query_clickhouse(query)

        span = results[0]
        assert span["model"] == "unknown-model-xyz"
        assert int(span["prompt_tokens"]) == 100
        assert int(span["completion_tokens"]) == 200

        # Check that cost attributes don't exist for unknown models
        attr_query = f"""
        SELECT SpanAttributes
        FROM otel_traces
        WHERE TraceId = '{trace_id}'
        LIMIT 1
        """
        attr_results = query_clickhouse(attr_query)
        if attr_results:
            span_attrs = attr_results[0]["SpanAttributes"]
            assert (
                "gen_ai.usage.prompt_cost" not in span_attrs
            ), "Prompt cost attribute should not exist for unknown model"
            assert (
                "gen_ai.usage.completion_cost" not in span_attrs
            ), "Completion cost attribute should not exist for unknown model"
