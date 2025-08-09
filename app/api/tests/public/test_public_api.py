import pytest
import jwt
import uuid
from datetime import datetime, timezone
from agentops.api.auth import generate_jwt, JWT_ALGO
from agentops.api.environment import JWT_SECRET_KEY
from agentops.opsboard.models import ProjectModel


@pytest.fixture
def test_api_key():
    """Generate a UUID for premium test project API key."""
    return str(uuid.uuid4())


@pytest.fixture
def test_free_api_key():
    """Generate a UUID for free plan test project API key."""
    return str(uuid.uuid4())


@pytest.fixture
def test_trace_id():
    """Generate a unique trace ID for testing."""
    import random

    return str(random.randint(10**37, 10**38 - 1))


@pytest.fixture
def test_span_id():
    """Generate a unique span ID for testing."""
    import random

    return str(random.randint(10**19, 10**20 - 1))


@pytest.fixture
def test_project_with_api_key(orm_session, test_user_org_owner_prem, test_api_key):
    """Create a test project with the specific API key for testing."""
    org = test_user_org_owner_prem

    project = ProjectModel(
        name="Test Public API Project",
        org_id=org.id,
        environment="development",
        api_key=test_api_key,
    )
    orm_session.add(project)
    orm_session.commit()

    project_obj = ProjectModel.get_by_id(orm_session, project.id)

    yield project_obj

    # Cleanup: delete the project after the test
    orm_session.delete(project_obj)
    orm_session.commit()


@pytest.fixture
def test_free_project_with_api_key(orm_session, test_user_org_owner, test_free_api_key):
    """Create a free plan test project for testing restrictions."""
    org = test_user_org_owner

    project = ProjectModel(
        name="Test Free Project",
        org_id=org.id,
        environment="development",
        api_key=test_free_api_key,
        # TODO the project org will dictate the plan
    )
    orm_session.add(project)
    orm_session.commit()

    project_obj = ProjectModel.get_by_id(orm_session, project.id)

    yield project_obj

    # Cleanup: delete the project after the test
    orm_session.delete(project_obj)
    orm_session.commit()


@pytest.fixture
async def test_trace_data(async_clickhouse_client, test_project_with_api_key, test_trace_id):
    """Create test trace data in ClickHouse."""
    import random

    project = test_project_with_api_key
    project_id_str = str(project.id)

    # Insert test trace
    trace_data = {
        "Timestamp": datetime.now(timezone.utc),
        "TraceId": test_trace_id,
        "SpanId": str(random.randint(10**19, 10**20 - 1)),  # Unique span ID for the root span
        "ParentSpanId": "",
        "TraceState": "",
        "SpanName": "test_trace",
        "SpanKind": "SPAN_KIND_INTERNAL",
        "ServiceName": "test_service",
        "ResourceAttributes": {"agentops.project.id": project_id_str},
        "ScopeName": "",
        "ScopeVersion": "",
        "SpanAttributes": {"tags": "test,public-api"},
        "Duration": 1000000,
        "StatusCode": "STATUS_CODE_OK",
        "StatusMessage": "",
        "Events.Timestamp": [],
        "Events.Name": [],
        "Events.Attributes": [],
        "Links.TraceId": [],
        "Links.SpanId": [],
        "Links.TraceState": [],
        "Links.Attributes": [],
    }

    await async_clickhouse_client.insert(
        table="otel_traces", data=[list(trace_data.values())], column_names=list(trace_data.keys())
    )

    yield trace_data

    # Cleanup: delete the trace data after the test
    await async_clickhouse_client.command(f"DELETE FROM otel_traces WHERE TraceId = '{test_trace_id}'")


@pytest.fixture
async def test_span_data(async_clickhouse_client, test_trace_data, test_span_id, test_trace_id):
    """Create test span data in ClickHouse."""
    # Use the same project ID as the trace data
    project_id_str = test_trace_data["ResourceAttributes"]["agentops.project.id"]

    # Insert test span
    span_data = {
        "Timestamp": datetime.now(timezone.utc),
        "TraceId": test_trace_id,
        "SpanId": test_span_id,
        "ParentSpanId": "",
        "TraceState": "",
        "SpanName": "test_span",
        "SpanKind": "SPAN_KIND_INTERNAL",
        "ServiceName": "test_service",
        "ResourceAttributes": {"agentops.project.id": project_id_str, "service.name": "test_service"},
        "ScopeName": "",
        "ScopeVersion": "",
        "SpanAttributes": {"operation": "test", "test": "value"},
        "Duration": 1000000,  # 1ms in nanoseconds
        "StatusCode": "STATUS_CODE_OK",
        "StatusMessage": "",
        "Events.Timestamp": [],
        "Events.Name": [],
        "Events.Attributes": [],
        "Links.TraceId": [],
        "Links.SpanId": [],
        "Links.TraceState": [],
        "Links.Attributes": [],
    }

    await async_clickhouse_client.insert(
        table="otel_traces", data=[list(span_data.values())], column_names=list(span_data.keys())
    )

    yield span_data

    # Cleanup: delete the span data after the test
    await async_clickhouse_client.command(f"DELETE FROM otel_traces WHERE SpanId = '{test_span_id}'")


@pytest.fixture
def valid_bearer_token(test_project_with_api_key):
    """Generate a valid JWT bearer token for testing."""
    project = test_project_with_api_key
    return generate_jwt(project)


class TestAuthenticationEndpoint:
    """Tests for POST /public/v1/auth/access_token"""

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, async_app_client, test_project_with_api_key, test_api_key):
        """Test successful API key to bearer token conversion."""
        response = await async_app_client.post("/public/v1/auth/access_token", json={"api_key": test_api_key})

        assert response.status_code == 200
        data = response.json()
        assert "bearer" in data

    @pytest.mark.asyncio
    async def test_get_access_token_invalid_api_key(self, async_app_client):
        """Test with invalid API key."""
        response = await async_app_client.post(
            "/public/v1/auth/access_token", json={"api_key": "invalid-key-123"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_access_token_missing_api_key(self, async_app_client):
        """Test with missing API key."""
        response = await async_app_client.post("/public/v1/auth/access_token", json={})

        assert response.status_code == 422
        # this is an internal fastapi thing

    @pytest.mark.skip(
        reason="Free plan blocking temporarily disabled - see BasePublicAPIView._verify_project_has_access"
    )
    @pytest.mark.asyncio
    async def test_get_access_token_free_plan_blocked(
        self, async_app_client, test_free_project_with_api_key, test_free_api_key
    ):
        """Test that free plan projects are blocked from accessing the API."""
        response = await async_app_client.post(
            "/public/v1/auth/access_token", json={"api_key": test_free_api_key}
        )

        assert response.status_code == 403
        assert "not available for free plan projects" in response.json()["detail"]


class TestProjectEndpoint:
    """Tests for GET /public/v1/project"""

    @pytest.mark.asyncio
    async def test_get_project_success(self, async_app_client, test_project_with_api_key, valid_bearer_token):
        """Test successful project details retrieval."""
        project = test_project_with_api_key
        token = valid_bearer_token

        response = await async_app_client.get(
            "/public/v1/project", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(project.id)
        assert data["name"] == project.name
        assert data["environment"] == project.environment

    @pytest.mark.asyncio
    async def test_get_project_missing_auth_header(self, async_app_client):
        """Test with missing Authorization header."""
        response = await async_app_client.get("/public/v1/project")

        assert response.status_code == 400
        assert "Missing or invalid Authorization header" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_project_invalid_bearer_token(self, async_app_client):
        """Test with invalid bearer token."""
        response = await async_app_client.get(
            "/public/v1/project", headers={"Authorization": "Bearer invalid-token-123"}
        )

        assert response.status_code == 400


class TestTraceEndpoints:
    """Tests for trace-related endpoints"""

    @pytest.mark.asyncio
    async def test_get_trace_success(
        self,
        async_app_client,
        test_trace_data,
        test_span_data,
        valid_bearer_token,
        test_trace_id,
        async_clickhouse_client,
        test_project_with_api_key,
    ):
        """Test successful trace retrieval."""
        token = valid_bearer_token

        response = await async_app_client.get(
            f"/public/v1/traces/{test_trace_id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["trace_id"] == test_trace_id
        assert "spans" in data
        assert "tags" in data

    @pytest.mark.asyncio
    async def test_get_trace_metrics_success(
        self, async_app_client, test_trace_data, valid_bearer_token, test_trace_id
    ):
        """Test successful trace metrics retrieval."""
        token = valid_bearer_token

        response = await async_app_client.get(
            f"/public/v1/traces/{test_trace_id}/metrics", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        # Metrics response structure will depend on TraceMetricsResponse model
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_trace_not_found(self, async_app_client, valid_bearer_token):
        """Test trace not found."""
        token = valid_bearer_token

        response = await async_app_client.get(
            "/public/v1/traces/nonexistent-trace-id", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "Trace not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_trace_missing_trace_id(self, async_app_client, valid_bearer_token):
        """Test with missing trace_id parameter."""
        token = valid_bearer_token

        response = await async_app_client.get(
            "/public/v1/traces/", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404  # Route not found


class TestSpanEndpoints:
    """Tests for span-related endpoints"""

    @pytest.mark.asyncio
    async def test_get_span_success(self, async_app_client, test_span_data, valid_bearer_token, test_span_id):
        """Test successful span retrieval."""
        token = valid_bearer_token

        response = await async_app_client.get(
            f"/public/v1/spans/{test_span_id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["span_id"] == test_span_id
        assert data["span_name"] == "test_span"
        assert data["span_kind"] == "SPAN_KIND_INTERNAL"
        assert "attributes" in data

    @pytest.mark.asyncio
    async def test_get_span_metrics_success(
        self, async_app_client, test_span_data, valid_bearer_token, test_span_id
    ):
        """Test successful span metrics retrieval."""
        token = valid_bearer_token

        response = await async_app_client.get(
            f"/public/v1/spans/{test_span_id}/metrics", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        # Metrics response structure will depend on SpanMetricsResponse model
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_get_span_not_found(self, async_app_client, valid_bearer_token):
        """Test span not found."""
        token = valid_bearer_token

        response = await async_app_client.get(
            "/public/v1/spans/nonexistent-span-id", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "Span not found" in response.json()["detail"]


class TestErrorCases:
    """Tests for various error scenarios"""

    @pytest.mark.asyncio
    async def test_malformed_bearer_token(self, async_app_client):
        """Test with malformed Authorization header."""
        response = await async_app_client.get(
            "/public/v1/project", headers={"Authorization": "NotBearer token123"}
        )

        assert response.status_code == 400
        assert "Missing or invalid Authorization header" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_expired_bearer_token(self, async_app_client):
        """Test with expired JWT token."""
        # Create an expired token (with past exp claim)
        import time

        expired_payload = {
            "project_id": "test-project-id",
            "is_premium": True,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGO)

        response = await async_app_client.get(
            "/public/v1/project", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 400
