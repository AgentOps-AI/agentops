"""
Tests for v4 logs API endpoints including LogsUploadView and get_trace_logs.
"""

import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, status, Request

from agentops.api.routes.v4.logs import LogsUploadView, get_trace_logs, convert_trace_id
from agentops.api.storage import ObjectUploadResponse
from agentops.api.environment import SUPABASE_URL, SUPABASE_S3_LOGS_BUCKET


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload for testing"""
    return {
        'project_id': 'test-project-123',
        'project_prem_status': 'premium',
        'api_key': 'test-api-key',
        'aud': 'authenticated',
        'exp': 1234567890,
    }


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    client = MagicMock()
    client.upload_fileobj = MagicMock()
    client.get_object = MagicMock()
    client.exceptions.NoSuchKey = Exception
    return client


@pytest.fixture
def mock_request():
    """Mock FastAPI Request for testing"""
    request = MagicMock(spec=Request)

    # Create a proper async iterator for the stream method
    async def async_stream_generator(chunks):
        for chunk in chunks:
            yield chunk

    # Default stream that will be overridden in individual tests
    request.stream = AsyncMock(return_value=async_stream_generator([]))

    # Add required headers for public route validation
    request.headers = {
        "x-forwarded-for": "192.168.0.1",
        "x-forwarded-host": "api.agentops.ai",
        "origin": "https://app.agentops.ai",
        "referer": "https://app.agentops.ai/signin",
        "user-agent": "Mozilla/5.0 Chrome/91.0.4472.124",
    }
    return request


class TestLogsUploadView:
    """Tests for the LogsUploadView class"""

    def test_bucket_name_configuration(self, mock_request):
        """Test that LogsUploadView has correct bucket configuration"""
        view = LogsUploadView(mock_request)
        assert view.bucket_name == SUPABASE_S3_LOGS_BUCKET

    @pytest.mark.asyncio
    async def test_successful_log_upload(self, mock_jwt_payload, mock_s3_client, mock_request):
        """Test successful log file upload with trace ID"""
        view = LogsUploadView(mock_request)

        # Set trace ID header (merge with existing headers)
        trace_id = "test-trace-12345"
        mock_request.headers.update({"Trace-Id": trace_id})

        # Mock request stream
        test_content = b'[INFO] Test log content\n[ERROR] Test error message'

        async def async_stream_generator():
            for chunk in [test_content]:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with (
            patch('agentops.api.storage.get_s3_client', return_value=mock_s3_client),
            patch('agentops.auth.views.API_URL', 'http://localhost:8000'),
        ):  # Bypass validation
            response = await view(token=mock_jwt_payload)

            assert isinstance(response, ObjectUploadResponse)
            assert response.size == len(test_content)
            expected_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_S3_LOGS_BUCKET}/{trace_id}.log"
            assert response.url == expected_url

            # Verify S3 upload was called with correct parameters
            mock_s3_client.upload_fileobj.assert_called_once()
            args = mock_s3_client.upload_fileobj.call_args[0]
            assert isinstance(args[0], BytesIO)
            assert args[1] == SUPABASE_S3_LOGS_BUCKET
            assert args[2] == f"{trace_id}.log"

    def test_missing_trace_id(self, mock_jwt_payload, mock_request):
        """Test that missing trace ID raises appropriate error"""
        view = LogsUploadView(mock_request)
        view.token = mock_jwt_payload

        # Remove Trace-Id header while keeping others
        mock_request.headers = {k: v for k, v in mock_request.headers.items() if k != "Trace-Id"}

        with pytest.raises(HTTPException) as exc_info:
            _ = view.filename

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No trace ID provided" in exc_info.value.detail

    def test_invalid_trace_id_characters(self, mock_jwt_payload, mock_request):
        """Test that invalid characters in trace ID are rejected"""
        view = LogsUploadView(mock_request)
        view.token = mock_jwt_payload

        # Trace ID with invalid characters
        invalid_trace_ids = ["trace@123", "trace#456", "trace 789", "trace/abc", "trace\\def"]

        for invalid_id in invalid_trace_ids:
            mock_request.headers.update({"Trace-Id": invalid_id})

            with pytest.raises(HTTPException) as exc_info:
                _ = view.filename

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Trace ID contains invalid characters" in exc_info.value.detail

    def test_valid_trace_id_characters(self, mock_jwt_payload, mock_request):
        """Test that valid trace IDs are accepted"""
        view = LogsUploadView(mock_request)
        view.token = mock_jwt_payload

        valid_trace_ids = [
            "trace123",
            "trace-456",
            "trace_789",
            "trace.abc",
            "trace-123_456.def",
            "TRACE-UPPER-123",
        ]

        for valid_id in valid_trace_ids:
            mock_request.headers.update({"Trace-Id": valid_id})
            assert view.filename == f"{valid_id}.log"

    @pytest.mark.asyncio
    async def test_file_size_limit_enforcement(self, mock_jwt_payload, mock_request):
        """Test that file size limits are enforced for log uploads"""
        view = LogsUploadView(mock_request)
        view.max_size = 100  # Set small limit for testing

        mock_request.headers.update({"Trace-Id": "test-trace"})

        # Mock request stream with oversized content
        large_content = b'x' * 150  # Exceeds 100 byte limit

        async def async_stream_generator():
            for chunk in [large_content]:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with patch('agentops.auth.views.API_URL', 'http://localhost:8000'):  # Bypass validation
            with pytest.raises(HTTPException) as exc_info:
                await view(token=mock_jwt_payload)

            assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            assert "File size exceeds the maximum limit" in exc_info.value.detail


class TestGetTraceLogs:
    """Tests for the get_trace_logs endpoint"""

    def test_convert_trace_id_hex_to_int(self):
        """Test conversion of hex trace IDs to integers"""
        # Hex strings should be converted
        assert convert_trace_id("1a2b3c") == str(int("1a2b3c", 16))
        assert convert_trace_id("ABCDEF") == str(int("ABCDEF", 16))
        assert convert_trace_id("123abc") == str(int("123abc", 16))

        # Pure numeric strings should remain unchanged
        assert convert_trace_id("123456") == "123456"

        # Invalid hex should remain unchanged
        assert convert_trace_id("invalid") == "invalid"
        assert convert_trace_id("123xyz") == "123xyz"

    def test_convert_trace_id_edge_cases(self):
        """Test edge cases for trace ID conversion"""
        # Empty string
        assert convert_trace_id("") == ""

        # Mixed case hex
        assert convert_trace_id("1A2b3C") == str(int("1A2b3C", 16))

        # Long hex string
        long_hex = "abcdef1234567890"
        assert convert_trace_id(long_hex) == str(int(long_hex, 16))

    @pytest.mark.asyncio
    async def test_get_trace_logs_successful_retrieval(self, mock_s3_client):
        """Test successful log retrieval for valid trace"""
        trace_id = "test-trace-123"
        log_content = "INFO: Test log entry\nERROR: Test error"

        # Mock S3 response
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = log_content.encode('utf-8')
        mock_s3_client.get_object.return_value = mock_response

        # Mock request with session
        mock_request = MagicMock()
        mock_request.state.session.user_id = "user-123"

        # Mock ORM session
        mock_orm = MagicMock()

        # Mock trace model
        with (
            patch('agentops.api.routes.v4.logs.TraceModel') as mock_trace_model,
            patch('agentops.api.routes.v4.logs.ProjectModel') as mock_project_model,
            patch('agentops.api.routes.v4.logs.get_s3_client', return_value=mock_s3_client),
        ):
            # Setup trace mock with AsyncMock
            mock_trace = MagicMock()
            mock_trace.spans = ["span1", "span2"]  # Non-empty spans
            mock_trace.project_id = "project-123"
            mock_trace_model.select = AsyncMock(return_value=mock_trace)

            # Setup project mock
            mock_project = MagicMock()
            mock_project.is_freeplan = False
            mock_project.org.is_user_member.return_value = True
            mock_project_model.get_by_id.return_value = mock_project

            response = await get_trace_logs(request=mock_request, orm=mock_orm, trace_id=trace_id)

            # Function is decorated with @add_cors_headers which wraps it in JSONResponse
            assert hasattr(response, 'body')
            # Extract the JSON data from the response
            import json
            response_data = json.loads(response.body.decode())
            assert response_data['content'] == log_content
            assert response_data['trace_id'] == trace_id
            assert not response_data['freeplan_truncated']

            # Verify S3 was called with converted trace ID
            mock_s3_client.get_object.assert_called_once_with(
                Bucket=SUPABASE_S3_LOGS_BUCKET, Key=f"{trace_id}.log"
            )

    @pytest.mark.asyncio
    async def test_get_trace_logs_nonexistent_trace(self):
        """Test error when trace doesn't exist"""
        trace_id = "nonexistent-trace"

        mock_request = MagicMock()
        mock_orm = MagicMock()

        with patch('agentops.api.routes.v4.logs.TraceModel') as mock_trace_model:
            # Mock empty trace (no spans)
            mock_trace = MagicMock()
            mock_trace.spans = []  # Empty spans indicate no trace
            mock_trace_model.select = AsyncMock(return_value=mock_trace)

            with pytest.raises(HTTPException) as exc_info:
                await get_trace_logs(request=mock_request, orm=mock_orm, trace_id=trace_id)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "You do not have access to this trace" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_trace_logs_no_permission(self):
        """Test error when user doesn't have access to trace"""
        trace_id = "restricted-trace"

        mock_request = MagicMock()
        mock_request.state.session.user_id = "user-123"
        mock_orm = MagicMock()

        with (
            patch('agentops.api.routes.v4.logs.TraceModel') as mock_trace_model,
            patch('agentops.api.routes.v4.logs.ProjectModel') as mock_project_model,
        ):
            # Setup trace mock
            mock_trace = MagicMock()
            mock_trace.spans = ["span1"]  # Non-empty spans
            mock_trace.project_id = "project-123"
            mock_trace_model.select = AsyncMock(return_value=mock_trace)

            # Setup project mock - user is not a member
            mock_project = MagicMock()
            mock_project.org.is_user_member.return_value = False
            mock_project_model.get_by_id.return_value = mock_project

            with pytest.raises(HTTPException) as exc_info:
                await get_trace_logs(request=mock_request, orm=mock_orm, trace_id=trace_id)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "You do not have access to this trace" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_trace_logs_s3_file_not_found(self, mock_s3_client):
        """Test error when log file doesn't exist in S3"""
        trace_id = "trace-without-logs"

        # Mock S3 to raise NoSuchKey exception
        mock_s3_client.get_object.side_effect = mock_s3_client.exceptions.NoSuchKey()

        mock_request = MagicMock()
        mock_request.state.session.user_id = "user-123"
        mock_orm = MagicMock()

        with (
            patch('agentops.api.routes.v4.logs.TraceModel') as mock_trace_model,
            patch('agentops.api.routes.v4.logs.ProjectModel') as mock_project_model,
            patch('agentops.api.routes.v4.logs.get_s3_client', return_value=mock_s3_client),
        ):
            # Setup valid trace and project
            mock_trace = MagicMock()
            mock_trace.spans = ["span1"]
            mock_trace.project_id = "project-123"
            mock_trace_model.select = AsyncMock(return_value=mock_trace)

            mock_project = MagicMock()
            mock_project.org.is_user_member.return_value = True
            mock_project_model.get_by_id.return_value = mock_project

            with pytest.raises(HTTPException) as exc_info:
                await get_trace_logs(request=mock_request, orm=mock_orm, trace_id=trace_id)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert f"No logs found for trace ID: {trace_id}" in exc_info.value.detail