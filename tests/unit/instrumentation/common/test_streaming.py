import pytest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from agentops.instrumentation.common.streaming import (
    BaseStreamWrapper,
    SyncStreamWrapper,
    AsyncStreamWrapper,
    create_stream_wrapper_factory,
    StreamingResponseHandler,
)
from agentops.instrumentation.common.token_counting import TokenUsage


class TestBaseStreamWrapper:
    """Test the BaseStreamWrapper class."""

    def test_init(self):
        """Test BaseStreamWrapper initialization."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        extract_attrs = lambda x: {"key": "value"}

        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content, extract_attrs)

        assert wrapper.stream is mock_stream
        assert wrapper.span is mock_span
        assert wrapper.extract_chunk_content is extract_content
        assert wrapper.extract_chunk_attributes is extract_attrs
        assert wrapper.start_time > 0
        assert wrapper.first_token_time is None
        assert wrapper.chunks_received == 0
        assert wrapper.accumulated_content == []
        assert isinstance(wrapper.token_usage, TokenUsage)

    def test_init_without_extract_chunk_attributes(self):
        """Test BaseStreamWrapper initialization without extract_chunk_attributes."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"

        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        assert wrapper.extract_chunk_attributes is not None
        assert wrapper.extract_chunk_attributes({}) == {}

    def test_process_chunk_first_token(self):
        """Test processing the first chunk (first token timing)."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        # Mock the token usage extraction to avoid type errors
        with patch(
            "agentops.instrumentation.common.token_counting.TokenUsageExtractor.extract_from_response"
        ) as mock_extract:
            mock_extract.return_value = Mock(prompt_tokens=None, completion_tokens=None)

            with patch("time.time", return_value=100.0):
                wrapper._process_chunk(Mock())

        assert wrapper.first_token_time == 100.0
        assert wrapper.chunks_received == 1
        assert wrapper.accumulated_content == ["test"]

    def test_process_chunk_subsequent_tokens(self):
        """Test processing subsequent chunks (no first token timing)."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)
        wrapper.first_token_time = 50.0

        # Mock the token usage extraction
        with patch(
            "agentops.instrumentation.common.token_counting.TokenUsageExtractor.extract_from_response"
        ) as mock_extract:
            mock_extract.return_value = Mock(prompt_tokens=None, completion_tokens=None)

            wrapper._process_chunk(Mock())

        assert wrapper.chunks_received == 1
        assert wrapper.accumulated_content == ["test"]

    def test_process_chunk_with_attributes(self):
        """Test processing chunk with custom attributes."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        extract_attrs = lambda x: {"custom_key": "custom_value"}
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content, extract_attrs)

        # Mock the token usage extraction
        with patch(
            "agentops.instrumentation.common.token_counting.TokenUsageExtractor.extract_from_response"
        ) as mock_extract:
            mock_extract.return_value = Mock(prompt_tokens=None, completion_tokens=None)

            wrapper._process_chunk(Mock())

        mock_span.set_attribute.assert_called_with("custom_key", "custom_value")

    def test_process_chunk_with_token_usage(self):
        """Test processing chunk with token usage information."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        # Mock chunk with usage
        mock_chunk = Mock()
        mock_chunk.usage = {"prompt_tokens": 10, "completion_tokens": 5}

        with patch(
            "agentops.instrumentation.common.token_counting.TokenUsageExtractor.extract_from_response"
        ) as mock_extract:
            mock_usage = Mock()
            mock_usage.prompt_tokens = 10
            mock_usage.completion_tokens = 5
            mock_extract.return_value = mock_usage

            wrapper._process_chunk(mock_chunk)

        assert wrapper.token_usage.prompt_tokens == 10
        assert wrapper.token_usage.completion_tokens == 5

    def test_process_chunk_with_usage_metadata(self):
        """Test processing chunk with usage_metadata attribute."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        # Mock chunk with usage_metadata
        mock_chunk = Mock()
        mock_chunk.usage_metadata = {"prompt_tokens": 10, "completion_tokens": 5}

        with patch(
            "agentops.instrumentation.common.token_counting.TokenUsageExtractor.extract_from_response"
        ) as mock_extract:
            mock_usage = Mock()
            mock_usage.prompt_tokens = 10
            mock_usage.completion_tokens = 5
            mock_extract.return_value = mock_usage

            wrapper._process_chunk(mock_chunk)

        assert wrapper.token_usage.prompt_tokens == 10
        assert wrapper.token_usage.completion_tokens == 5

    def test_process_chunk_accumulate_completion_tokens(self):
        """Test that completion tokens are accumulated across chunks."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        # Mock chunks with usage
        mock_chunk1 = Mock()
        mock_chunk2 = Mock()

        with patch(
            "agentops.instrumentation.common.token_counting.TokenUsageExtractor.extract_from_response"
        ) as mock_extract:
            mock_usage1 = Mock()
            mock_usage1.prompt_tokens = 10
            mock_usage1.completion_tokens = 3
            mock_usage2 = Mock()
            mock_usage2.prompt_tokens = 10
            mock_usage2.completion_tokens = 2
            mock_extract.side_effect = [mock_usage1, mock_usage2]

            wrapper._process_chunk(mock_chunk1)
            wrapper._process_chunk(mock_chunk2)

        assert wrapper.token_usage.prompt_tokens == 10
        assert wrapper.token_usage.completion_tokens == 5  # 3 + 2

    def test_finalize_success(self):
        """Test successful finalization of stream."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        # Add some content
        wrapper.accumulated_content = ["Hello", " ", "World"]
        wrapper.chunks_received = 3
        wrapper.first_token_time = 99.0  # Set a specific time

        with patch("time.time", return_value=100.0):
            wrapper._finalize()

        # Check that all attributes were set
        mock_span.set_attribute.assert_any_call("streaming.final_content", "Hello World")
        mock_span.set_attribute.assert_any_call("streaming.chunk_count", 3)
        mock_span.set_attribute.assert_any_call("streaming.total_duration", 100.0 - wrapper.start_time)
        mock_span.set_attribute.assert_any_call("streaming.generation_duration", 1.0)
        mock_span.set_status.assert_called_once()
        mock_span.end.assert_called_once()

    def test_finalize_with_exception(self):
        """Test finalization with exception handling."""
        mock_stream = Mock()
        mock_span = Mock()
        extract_content = lambda x: "test"
        wrapper = BaseStreamWrapper(mock_stream, mock_span, extract_content)

        with patch(
            "agentops.instrumentation.common.span_management.safe_set_attribute", side_effect=Exception("Test error")
        ):
            wrapper._finalize()

        mock_span.set_status.assert_called()
        mock_span.end.assert_called_once()


class TestSyncStreamWrapper:
    """Test the SyncStreamWrapper class."""

    def test_iteration_success(self):
        """Test successful iteration through sync stream."""
        mock_stream = ["chunk1", "chunk2", "chunk3"]
        mock_span = Mock()
        extract_content = lambda x: x
        wrapper = SyncStreamWrapper(mock_stream, mock_span, extract_content)

        result = list(wrapper)

        assert result == ["chunk1", "chunk2", "chunk3"]
        assert wrapper.chunks_received == 3
        assert wrapper.accumulated_content == ["chunk1", "chunk2", "chunk3"]
        mock_span.end.assert_called_once()

    def test_iteration_with_exception(self):
        """Test iteration with exception handling."""

        def failing_stream():
            yield "chunk1"
            raise ValueError("Test error")

        mock_span = Mock()
        extract_content = lambda x: x
        wrapper = SyncStreamWrapper(failing_stream(), mock_span, extract_content)

        with pytest.raises(ValueError, match="Test error"):
            list(wrapper)

        mock_span.set_status.assert_called()
        mock_span.record_exception.assert_called_once()
        mock_span.end.assert_called_once()


class TestAsyncStreamWrapper:
    """Test the AsyncStreamWrapper class."""

    @pytest.mark.asyncio
    async def test_async_iteration_success(self):
        """Test successful async iteration through stream."""

        async def async_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        mock_span = Mock()
        extract_content = lambda x: x
        wrapper = AsyncStreamWrapper(async_stream(), mock_span, extract_content)

        result = []
        async for chunk in wrapper:
            result.append(chunk)

        assert result == ["chunk1", "chunk2", "chunk3"]
        assert wrapper.chunks_received == 3
        assert wrapper.accumulated_content == ["chunk1", "chunk2", "chunk3"]
        mock_span.end.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_iteration_with_exception(self):
        """Test async iteration with exception handling."""

        async def failing_async_stream():
            yield "chunk1"
            raise ValueError("Test error")

        mock_span = Mock()
        extract_content = lambda x: x
        wrapper = AsyncStreamWrapper(failing_async_stream(), mock_span, extract_content)

        with pytest.raises(ValueError, match="Test error"):
            async for chunk in wrapper:
                pass

        mock_span.set_status.assert_called()
        mock_span.record_exception.assert_called_once()
        mock_span.end.assert_called_once()


class TestCreateStreamWrapperFactory:
    """Test the create_stream_wrapper_factory function."""

    def test_create_sync_wrapper(self):
        """Test creating a sync stream wrapper."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        def mock_stream():
            yield "chunk1"
            yield "chunk2"

        def mock_wrapped(*args, **kwargs):
            return mock_stream()

        extract_content = lambda x: x
        factory = create_stream_wrapper_factory(mock_tracer, "test_span", extract_content)

        result = factory(mock_wrapped, None, (), {})

        assert isinstance(result, SyncStreamWrapper)
        mock_tracer.start_span.assert_called_with("test_span")

    def test_create_async_wrapper(self):
        """Test creating an async stream wrapper."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        async def mock_async_stream():
            yield "chunk1"
            yield "chunk2"

        def mock_wrapped(*args, **kwargs):
            return mock_async_stream()

        extract_content = lambda x: x
        factory = create_stream_wrapper_factory(mock_tracer, "test_span", extract_content)

        result = factory(mock_wrapped, None, (), {})

        assert isinstance(result, AsyncStreamWrapper)
        mock_tracer.start_span.assert_called_with("test_span")

    def test_create_wrapper_with_initial_attributes(self):
        """Test creating a wrapper with initial attributes."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        def mock_stream():
            yield "chunk1"

        def mock_wrapped(*args, **kwargs):
            return mock_stream()

        extract_content = lambda x: x
        initial_attrs = {"initial_key": "initial_value"}
        factory = create_stream_wrapper_factory(
            mock_tracer, "test_span", extract_content, initial_attributes=initial_attrs
        )

        factory(mock_wrapped, None, (), {})

        mock_span.set_attribute.assert_called_with("initial_key", "initial_value")

    def test_create_wrapper_with_exception(self):
        """Test creating a wrapper when wrapped function raises exception."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        def mock_wrapped(*args, **kwargs):
            raise ValueError("Test error")

        extract_content = lambda x: x
        factory = create_stream_wrapper_factory(mock_tracer, "test_span", extract_content)

        with pytest.raises(ValueError, match="Test error"):
            factory(mock_wrapped, None, (), {})

        mock_span.set_status.assert_called()
        mock_span.record_exception.assert_called_once()
        mock_span.end.assert_called_once()


class TestStreamingResponseHandler:
    """Test the StreamingResponseHandler class."""

    def test_extract_openai_chunk_content_with_choices(self):
        """Test extracting content from OpenAI-style chunk with choices."""
        mock_choice = Mock()
        mock_delta = Mock()
        mock_delta.content = "Hello"
        mock_choice.delta = mock_delta

        mock_chunk = Mock()
        mock_chunk.choices = [mock_choice]

        result = StreamingResponseHandler.extract_openai_chunk_content(mock_chunk)
        assert result == "Hello"

    def test_extract_openai_chunk_content_without_choices(self):
        """Test extracting content from OpenAI-style chunk without choices."""
        mock_chunk = Mock()
        mock_chunk.choices = []

        result = StreamingResponseHandler.extract_openai_chunk_content(mock_chunk)
        assert result is None

    def test_extract_openai_chunk_content_without_delta(self):
        """Test extracting content from OpenAI-style chunk without delta."""
        mock_choice = Mock()
        mock_choice.delta = None

        mock_chunk = Mock()
        mock_chunk.choices = [mock_choice]

        result = StreamingResponseHandler.extract_openai_chunk_content(mock_chunk)
        assert result is None

    def test_extract_openai_chunk_content_without_content(self):
        """Test extracting content from OpenAI-style chunk without content."""
        mock_choice = Mock()
        mock_delta = Mock()
        del mock_delta.content  # Remove content attribute
        mock_choice.delta = mock_delta

        mock_chunk = Mock()
        mock_chunk.choices = [mock_choice]

        result = StreamingResponseHandler.extract_openai_chunk_content(mock_chunk)
        assert result is None

    def test_extract_anthropic_chunk_content_content_block_delta(self):
        """Test extracting content from Anthropic content_block_delta chunk."""
        mock_delta = Mock()
        mock_delta.text = "Hello"

        mock_chunk = Mock()
        mock_chunk.type = "content_block_delta"
        mock_chunk.delta = mock_delta

        result = StreamingResponseHandler.extract_anthropic_chunk_content(mock_chunk)
        assert result == "Hello"

    def test_extract_anthropic_chunk_content_message_delta(self):
        """Test extracting content from Anthropic message_delta chunk."""
        mock_delta = Mock()
        mock_delta.content = "Hello"

        mock_chunk = Mock()
        mock_chunk.type = "message_delta"
        mock_chunk.delta = mock_delta

        result = StreamingResponseHandler.extract_anthropic_chunk_content(mock_chunk)
        assert result == "Hello"

    def test_extract_anthropic_chunk_content_other_type(self):
        """Test extracting content from Anthropic chunk with other type."""
        mock_chunk = Mock()
        mock_chunk.type = "other_type"

        result = StreamingResponseHandler.extract_anthropic_chunk_content(mock_chunk)
        assert result is None

    def test_extract_anthropic_chunk_content_without_delta(self):
        """Test extracting content from Anthropic chunk without delta."""
        mock_chunk = Mock()
        mock_chunk.type = "content_block_delta"
        mock_chunk.delta = None

        result = StreamingResponseHandler.extract_anthropic_chunk_content(mock_chunk)
        assert result is None

    def test_extract_generic_chunk_content_with_content(self):
        chunk = SimpleNamespace(content="Hello")
        result = StreamingResponseHandler.extract_generic_chunk_content(chunk)
        assert result == "Hello"

    def test_extract_generic_chunk_content_with_text(self):
        chunk = SimpleNamespace(text="Hello")
        result = StreamingResponseHandler.extract_generic_chunk_content(chunk)
        assert result == "Hello"

    def test_extract_generic_chunk_content_with_delta_content(self):
        delta = SimpleNamespace(content="Hello")
        chunk = SimpleNamespace(delta=delta)
        result = StreamingResponseHandler.extract_generic_chunk_content(chunk)
        assert result == "Hello"

    def test_extract_generic_chunk_content_with_delta_text(self):
        delta = SimpleNamespace(text="Hello")
        chunk = SimpleNamespace(delta=delta)
        result = StreamingResponseHandler.extract_generic_chunk_content(chunk)
        assert result == "Hello"

    def test_extract_generic_chunk_content_string(self):
        """Test extracting content from string chunk."""
        chunk = "Hello"

        result = StreamingResponseHandler.extract_generic_chunk_content(chunk)
        assert result == "Hello"

    def test_extract_generic_chunk_content_no_match(self):
        """Test extracting content from chunk with no matching pattern."""
        mock_chunk = Mock()
        # Remove all potential attributes
        del mock_chunk.content
        del mock_chunk.text
        del mock_chunk.delta

        result = StreamingResponseHandler.extract_generic_chunk_content(mock_chunk)
        assert result is None

    def test_extract_generic_chunk_content_delta_without_content_or_text(self):
        delta = SimpleNamespace()
        chunk = SimpleNamespace(delta=delta)
        result = StreamingResponseHandler.extract_generic_chunk_content(chunk)
        assert result is None


class TestStreamingIntegration:
    """Integration tests for streaming functionality."""

    def test_full_sync_stream_processing(self):
        """Test complete sync stream processing workflow."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        def mock_stream():
            yield "Hello"
            yield " "
            yield "World"

        def mock_wrapped(*args, **kwargs):
            return mock_stream()

        extract_content = lambda x: x
        factory = create_stream_wrapper_factory(mock_tracer, "test_span", extract_content)
        wrapper = factory(mock_wrapped, None, (), {})

        result = list(wrapper)

        assert result == ["Hello", " ", "World"]
        assert wrapper.accumulated_content == ["Hello", " ", "World"]
        assert wrapper.chunks_received == 3
        mock_span.set_attribute.assert_any_call("streaming.final_content", "Hello World")
        mock_span.set_attribute.assert_any_call("streaming.chunk_count", 3)

    @pytest.mark.asyncio
    async def test_full_async_stream_processing(self):
        """Test complete async stream processing workflow."""
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        async def mock_async_stream():
            yield "Hello"
            yield " "
            yield "World"

        def mock_wrapped(*args, **kwargs):
            return mock_async_stream()

        extract_content = lambda x: x
        factory = create_stream_wrapper_factory(mock_tracer, "test_span", extract_content)
        wrapper = factory(mock_wrapped, None, (), {})

        result = []
        async for chunk in wrapper:
            result.append(chunk)

        assert result == ["Hello", " ", "World"]
        assert wrapper.accumulated_content == ["Hello", " ", "World"]
        assert wrapper.chunks_received == 3
        mock_span.set_attribute.assert_any_call("streaming.final_content", "Hello World")
        mock_span.set_attribute.assert_any_call("streaming.chunk_count", 3)
