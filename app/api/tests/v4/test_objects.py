"""
Tests for v4 objects API endpoints including ObjectUploadView.
"""

import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request

from agentops.api.routes.v4.objects import ObjectUploadView
from agentops.api.storage import ObjectUploadResponse
from agentops.api.environment import SUPABASE_S3_BUCKET


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


class TestObjectUploadView:
    """Tests for the ObjectUploadView class"""

    def test_bucket_name_configuration(self, mock_request):
        """Test that ObjectUploadView has correct bucket configuration"""
        view = ObjectUploadView(mock_request)
        assert view.bucket_name == SUPABASE_S3_BUCKET

    @pytest.mark.asyncio
    async def test_successful_object_upload(self, mock_jwt_payload, mock_s3_client, mock_request):
        """Test successful object upload with generated filename"""
        view = ObjectUploadView(mock_request)

        # Mock request stream
        test_content = b'{"key": "value", "data": [1, 2, 3]}'

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

            # Verify the URL contains the project ID and UUID format
            assert f"/{SUPABASE_S3_BUCKET}/test-project-123/" in response.url

            # Verify S3 upload was called
            mock_s3_client.upload_fileobj.assert_called_once()
            args = mock_s3_client.upload_fileobj.call_args[0]
            assert isinstance(args[0], BytesIO)
            assert args[1] == SUPABASE_S3_BUCKET

    def test_filename_generation_uniqueness(self, mock_jwt_payload, mock_request):
        """Test that filename generation includes project ID and UUID"""
        view = ObjectUploadView(mock_request)
        view.token = mock_jwt_payload

        filename = view.filename

        # Should start with project ID
        assert filename.startswith("test-project-123/")

        # Should have UUID format after the slash
        uuid_part = filename.split('/', 1)[1]
        # UUID4 hex is 32 characters
        assert len(uuid_part) == 32
        # Should be valid hex
        assert all(c in '0123456789abcdef' for c in uuid_part)

    def test_filename_caching(self, mock_jwt_payload, mock_request):
        """Test that filename is cached and doesn't change between calls"""
        view = ObjectUploadView(mock_request)
        view.token = mock_jwt_payload

        # First call
        filename1 = view.filename
        # Second call should return the same value
        filename2 = view.filename

        assert filename1 == filename2

    @pytest.mark.asyncio
    async def test_chunked_object_upload(self, mock_jwt_payload, mock_s3_client, mock_request):
        """Test that chunked uploads work correctly for objects"""
        view = ObjectUploadView(mock_request)

        # Mock request stream with multiple chunks
        chunks = [b'{"part1":', b'"data",', b'"part2":123}']

        async def async_stream_generator():
            for chunk in chunks:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with (
            patch('agentops.api.storage.get_s3_client', return_value=mock_s3_client),
            patch('agentops.auth.views.API_URL', 'http://localhost:8000'),
        ):  # Bypass validation
            response = await view(token=mock_jwt_payload)

            assert response.size == sum(len(chunk) for chunk in chunks)

            # Verify the complete content was uploaded
            uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0]
            uploaded_content.seek(0)
            assert uploaded_content.read() == b''.join(chunks)