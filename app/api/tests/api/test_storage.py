import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, status, Request

from agentops.api.storage import BaseObjectUploadView, ObjectUploadResponse
from agentops.api.environment import (
    SUPABASE_URL,
)


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
    return request


class ConcreteObjectUploadView(BaseObjectUploadView):
    """Concrete implementation for testing BaseObjectUploadView"""

    bucket_name = "test-bucket"

    @property
    def filename(self) -> str:
        return f"test-file-{self.token['project_id']}.txt"


class TestBaseObjectUploadView:
    """Tests for the BaseObjectUploadView class"""

    def test_bucket_name_assertion(self, mock_jwt_payload, mock_request):
        """Test that bucket_name assertion works"""
        view = ConcreteObjectUploadView(mock_request)
        view.bucket_name = None

        async def async_stream_generator():
            for chunk in [b'test content']:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with pytest.raises(AssertionError, match="`bucket_name` must be provided"):
            import asyncio

            asyncio.run(view(token=mock_jwt_payload))

    @pytest.mark.asyncio
    async def test_successful_upload(self, mock_jwt_payload, mock_s3_client, mock_request):
        """Test successful file upload"""
        view = ConcreteObjectUploadView(mock_request)

        # Mock request stream
        test_content = b'test file content'

        async def async_stream_generator():
            for chunk in [test_content]:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with patch('agentops.api.storage.get_s3_client', return_value=mock_s3_client):
            response = await view(token=mock_jwt_payload)

            assert isinstance(response, ObjectUploadResponse)
            assert response.size == len(test_content)
            assert (
                response.url
                == f"{SUPABASE_URL}/storage/v1/object/public/test-bucket/test-file-test-project-123.txt"
            )

            # Verify S3 upload was called
            mock_s3_client.upload_fileobj.assert_called_once()
            args = mock_s3_client.upload_fileobj.call_args[0]
            assert isinstance(args[0], BytesIO)
            assert args[1] == "test-bucket"
            assert args[2] == "test-file-test-project-123.txt"

    @pytest.mark.asyncio
    async def test_file_size_limit_exceeded(self, mock_jwt_payload, mock_request):
        """Test that files exceeding size limit are rejected"""
        view = ConcreteObjectUploadView(mock_request)
        view.max_size = 10  # Set very small limit

        # Mock request stream with large content
        large_content = b'x' * 20  # Exceeds 10 byte limit

        async def async_stream_generator():
            for chunk in [large_content]:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with pytest.raises(HTTPException) as exc_info:
            await view(token=mock_jwt_payload)

        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "File size exceeds the maximum limit" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_chunked_upload(self, mock_jwt_payload, mock_s3_client, mock_request):
        """Test that chunked uploads work correctly"""
        view = ConcreteObjectUploadView(mock_request)

        # Mock request stream with multiple chunks
        chunks = [b'chunk1', b'chunk2', b'chunk3']

        async def async_stream_generator():
            for chunk in chunks:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with patch('agentops.api.storage.get_s3_client', return_value=mock_s3_client):
            response = await view(token=mock_jwt_payload)

            assert response.size == sum(len(chunk) for chunk in chunks)

            # Verify the complete content was uploaded
            uploaded_content = mock_s3_client.upload_fileobj.call_args[0][0]
            uploaded_content.seek(0)
            assert uploaded_content.read() == b''.join(chunks)

    @pytest.mark.asyncio
    async def test_chunked_upload_size_limit(self, mock_jwt_payload, mock_request):
        """Test size limit enforcement with chunked uploads"""
        view = ConcreteObjectUploadView(mock_request)
        view.max_size = 15

        # Create chunks that exceed limit when combined
        chunks = [b'chunk1', b'chunk2', b'chunk3']  # Total: 18 bytes

        async def async_stream_generator():
            for chunk in chunks:
                yield chunk

        mock_request.stream = lambda: async_stream_generator()

        with pytest.raises(HTTPException) as exc_info:
            await view(token=mock_jwt_payload)

        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_public_url_generation(self, mock_jwt_payload, mock_request):
        """Test that public URL is generated correctly"""
        view = ConcreteObjectUploadView(mock_request)
        view.token = mock_jwt_payload

        expected_url = f"{SUPABASE_URL}/storage/v1/object/public/test-bucket/test-file-test-project-123.txt"
        assert view.public_url == expected_url

    def test_filename_property_abstract(self, mock_request):
        """Test that filename property must be implemented"""

        class IncompleteView(BaseObjectUploadView):
            bucket_name = "test"
            # Missing filename property implementation - inherits ellipsis (...) from base

        view = IncompleteView(mock_request)
        view.token = {'project_id': 'test'}

        # The ellipsis (...) in the base class returns None (property implementation issue)
        # This test verifies that subclasses should implement their own filename property
        result = view.filename
        assert result is None, "Incomplete view returns None from base class ellipsis property"

    @pytest.mark.asyncio
    async def test_upload_body_method(self, mock_jwt_payload, mock_s3_client, mock_request):
        """Test the upload_body method directly"""
        view = ConcreteObjectUploadView(mock_request)
        view.token = mock_jwt_payload
        view.client = mock_s3_client

        test_body = BytesIO(b'test content')
        await view.upload_body(test_body)

        mock_s3_client.upload_fileobj.assert_called_once_with(
            test_body, "test-bucket", "test-file-test-project-123.txt"
        )


class TestObjectUploadResponse:
    """Tests for the ObjectUploadResponse model"""

    def test_object_upload_response_creation(self):
        """Test creating ObjectUploadResponse"""
        response = ObjectUploadResponse(url="https://example.com/file.txt", size=1024)

        assert response.url == "https://example.com/file.txt"
        assert response.size == 1024

    def test_object_upload_response_serialization(self):
        """Test that ObjectUploadResponse can be serialized"""
        response = ObjectUploadResponse(url="https://example.com/file.txt", size=1024)

        # Should be able to convert to dict (for JSON serialization)
        response_dict = response.model_dump()
        assert response_dict == {"url": "https://example.com/file.txt", "size": 1024}
