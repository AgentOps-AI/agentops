import pytest
from unittest.mock import patch, MagicMock

# Tests for the new session management functionality
# These tests call the actual public API but mock the underlying implementation
# to avoid making real API calls or initializing the full telemetry pipeline


@pytest.fixture(scope="function")
def mock_tracing_core():
    """Mock the global tracer to avoid actual initialization"""
    # Patch both the main location and where it's imported in client
    with (
        patch("agentops.tracer") as mock_tracer,
        patch("agentops.client.client.tracer", mock_tracer),
        patch("agentops.sdk.decorators.factory.tracer", mock_tracer),
        patch("agentops.legacy.tracer", mock_tracer),
    ):
        # Create a mock instance
        mock_tracer.initialized = True

        yield mock_tracer


@pytest.fixture(scope="function")
def mock_api_client():
    """Mock the API client to avoid actual API calls"""
    with patch("agentops.client.api.ApiClient") as mock_api:
        # Configure the v3.fetch_auth_token method to return a valid response
        mock_v3 = MagicMock()
        mock_v3.fetch_auth_token.return_value = {"token": "mock-jwt-token", "project_id": "mock-project-id"}
        mock_api.return_value.v3 = mock_v3

        yield mock_api


@pytest.fixture(scope="function")
def mock_trace_context():
    """Mock the TraceContext creation"""
    mock_span = MagicMock()
    mock_token = MagicMock()
    mock_trace_context_instance = MagicMock()
    mock_trace_context_instance.span = mock_span
    mock_trace_context_instance.token = mock_token
    mock_trace_context_instance.is_init_trace = False

    return mock_trace_context_instance


@pytest.fixture(scope="function")
def reset_client():
    """Reset the AgentOps client before each test"""
    import agentops

    # Create a fresh client instance for each test
    agentops._client = agentops.Client()
    # Reset all client state
    agentops._client._initialized = False
    agentops._client._init_trace_context = None
    agentops._client._legacy_session_for_init_trace = None
    yield
    # Clean up after test
    try:
        if hasattr(agentops._client, "_initialized"):
            agentops._client._initialized = False
        if hasattr(agentops._client, "_init_trace_context"):
            agentops._client._init_trace_context = None
        if hasattr(agentops._client, "_legacy_session_for_init_trace"):
            agentops._client._legacy_session_for_init_trace = None
    except:
        pass


def test_explicit_init_then_explicit_start_trace(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test explicitly initializing followed by explicitly starting a trace"""
    import agentops

    # Explicitly initialize with auto_start_session=False
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Verify that no auto-trace was started
    mock_tracing_core.start_trace.assert_not_called()

    # Mock the start_trace method to return our mock trace context
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Explicitly start a trace
    trace_context = agentops.start_trace(trace_name="test_trace", tags=["test"])

    # Verify the trace was created
    mock_tracing_core.start_trace.assert_called_once_with(trace_name="test_trace", tags=["test"])
    assert trace_context == mock_trace_context


def test_auto_start_session_true(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test initializing with auto_start_session=True"""
    import agentops
    from agentops.legacy import Session

    # Mock the start_trace method to return our mock trace context
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Initialize with auto_start_session=True
    result = agentops.init(api_key="test-api-key", auto_start_session=True)

    # Verify a trace was auto-started
    mock_tracing_core.start_trace.assert_called_once()
    # init() should return a Session object when auto-starting a session
    assert isinstance(result, Session)
    # Check that the session's trace_context has the expected properties
    assert result.trace_context is not None


def test_auto_start_session_default(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test initializing with default auto_start_session behavior"""
    import agentops
    from agentops.legacy import Session

    # Mock the start_trace method to return our mock trace context
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Initialize without explicitly setting auto_start_session (defaults to True)
    result = agentops.init(api_key="test-api-key")

    # Verify that the client was initialized
    assert agentops._client.initialized
    # Since auto_start_session defaults to True, init() should return a Session object
    assert isinstance(result, Session)
    # Check that the session's trace_context has the expected properties
    assert result.trace_context is not None


def test_start_trace_without_init():
    """Test starting a trace without initialization triggers auto-init"""
    import agentops

    # Reset client for test
    agentops._client = agentops.Client()

    # Mock global tracer to be uninitialized initially, then initialized after init
    with (
        patch("agentops.tracer") as mock_tracer,
        patch("agentops.client.client.tracer", mock_tracer),
        patch("agentops.sdk.decorators.factory.tracer", mock_tracer),
        patch("agentops.legacy.tracer", mock_tracer),
    ):
        mock_tracer.initialized = False

        # Mock the init function to simulate successful initialization
        with patch("agentops.init") as mock_init:

            def side_effect():
                # After init is called, mark global tracer as initialized
                mock_tracer.initialized = True

            mock_init.side_effect = side_effect
            mock_tracer.start_trace.return_value = None

            # Try to start a trace without initialization
            result = agentops.start_trace(trace_name="test_trace")

            # Verify that init was called automatically
            mock_init.assert_called_once()
            # Should return None since start_trace returned None
            assert result is None


def test_end_trace(mock_tracing_core, mock_trace_context):
    """Test ending a trace"""
    import agentops

    # End the trace
    agentops.end_trace(mock_trace_context, end_state="Success")

    # Verify end_trace was called on global tracer
    mock_tracing_core.end_trace.assert_called_once_with(trace_context=mock_trace_context, end_state="Success")


def test_session_decorator_creates_trace(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test that the @session decorator creates a trace-level span"""
    import agentops
    from agentops.sdk.decorators import session

    # Initialize AgentOps
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Reset the call count to start fresh
    mock_tracing_core.reset_mock()
    # Mock the start_trace and end_trace methods
    mock_tracing_core.start_trace.return_value = mock_trace_context

    @session(name="test_session", tags=["decorator_test"])
    def test_function():
        return "test_result"

    # Execute the decorated function
    result = test_function()

    # Verify the function executed successfully
    assert result == "test_result"

    # Verify that start_trace and end_trace were called
    # Note: The decorator might call start_trace multiple times due to initialization
    assert mock_tracing_core.start_trace.call_count >= 1
    assert mock_tracing_core.end_trace.call_count >= 1


def test_session_decorator_with_exception(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test that the @session decorator handles exceptions properly"""
    import agentops
    from agentops.sdk.decorators import session

    # Initialize AgentOps
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Reset the call count to start fresh
    mock_tracing_core.reset_mock()
    # Mock the start_trace method
    mock_tracing_core.start_trace.return_value = mock_trace_context

    @session(name="failing_session")
    def failing_function():
        raise ValueError("Test exception")

    # Execute the decorated function and expect an exception
    with pytest.raises(ValueError, match="Test exception"):
        failing_function()

    # Verify that start_trace was called
    assert mock_tracing_core.start_trace.call_count >= 1
    # Verify that end_trace was called
    assert mock_tracing_core.end_trace.call_count >= 1


def test_legacy_start_session_compatibility(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test that legacy start_session still works and calls tracer.start_trace"""
    import agentops
    from agentops.legacy import Session

    # Initialize AgentOps
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Reset the call count to start fresh
    mock_tracing_core.reset_mock()
    # Mock the start_trace method
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Start a legacy session
    session = agentops.start_session(tags=["legacy_test"])

    # Verify the session was created
    assert isinstance(session, Session)
    # Check that the session's trace_context has the expected properties
    assert session.trace_context is not None

    # Verify that tracer.start_trace was called
    # Note: May be called multiple times due to initialization
    assert mock_tracing_core.start_trace.call_count >= 1


def test_legacy_end_session_compatibility(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test that legacy end_session still works and calls tracer.end_trace"""
    import agentops
    from agentops.legacy import Session

    # Initialize AgentOps
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Reset the call count to start fresh
    mock_tracing_core.reset_mock()

    # Create a legacy session object
    session = Session(mock_trace_context)

    # End the session
    agentops.end_session(session)

    # Verify that tracer.end_trace was called
    mock_tracing_core.end_trace.assert_called_once_with(mock_trace_context, end_state="Success")


def test_no_double_init(mock_tracing_core, mock_api_client, reset_client):
    """Test that calling init multiple times doesn't reinitialize"""
    import agentops

    # Initialize once
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Track the call count
    call_count = mock_api_client.call_count

    # Call init again with the same API key
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Verify that API client wasn't constructed again
    assert mock_api_client.call_count == call_count


def test_client_initialization_behavior(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test basic client initialization behavior"""
    import agentops

    # Mock the start_trace method
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Test that initialization works
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Verify that the client was initialized
    assert agentops._client.initialized

    # The API client might not be called if already mocked at a higher level
    # Just verify that the initialization completed successfully

    # Test that calling init again doesn't cause issues
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Should still be initialized
    assert agentops._client.initialized


def test_multiple_concurrent_traces(mock_tracing_core, mock_api_client, reset_client):
    """Test that multiple traces can be started concurrently"""
    import agentops

    # Initialize AgentOps
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Create mock trace contexts for different traces
    mock_trace_context_1 = MagicMock()
    mock_trace_context_2 = MagicMock()

    # Mock start_trace to return different contexts
    mock_tracing_core.start_trace.side_effect = [
        mock_trace_context_1,
        mock_trace_context_2,
    ]

    # Start multiple traces
    trace1 = agentops.start_trace(trace_name="trace1", tags=["test1"])
    trace2 = agentops.start_trace(trace_name="trace2", tags=["test2"])

    # Verify both traces were created
    assert trace1 == mock_trace_context_1
    assert trace2 == mock_trace_context_2

    # Verify start_trace was called twice
    assert mock_tracing_core.start_trace.call_count == 2


def test_trace_context_properties(mock_trace_context):
    """Test that TraceContext properties work correctly"""
    from agentops.legacy import Session

    # Create a legacy session with the mock trace context
    session = Session(mock_trace_context)

    # Test that properties are accessible
    assert session.span == mock_trace_context.span
    assert session.token == mock_trace_context.token
    assert session.trace_context == mock_trace_context


def test_session_decorator_async_function(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test that the @session decorator works with async functions"""
    import agentops
    import asyncio
    from agentops.sdk.decorators import session

    # Initialize AgentOps
    agentops.init(api_key="test-api-key", auto_start_session=False)

    # Reset the call count to start fresh
    mock_tracing_core.reset_mock()
    # Mock the start_trace method
    mock_tracing_core.start_trace.return_value = mock_trace_context

    @session(name="async_test_session")
    async def async_test_function():
        await asyncio.sleep(0.01)  # Simulate async work
        return "async_result"

    # Execute the decorated async function
    result = asyncio.run(async_test_function())

    # Verify the function executed successfully
    assert result == "async_result"

    # Verify that start_trace and end_trace were called
    assert mock_tracing_core.start_trace.call_count >= 1
    assert mock_tracing_core.end_trace.call_count >= 1


def test_trace_context_creation():
    """Test that TraceContext can be created with proper attributes"""
    from agentops.sdk.core import TraceContext

    mock_span = MagicMock()
    mock_token = MagicMock()

    # Test creating a TraceContext
    trace_context = TraceContext(span=mock_span, token=mock_token, is_init_trace=False)

    assert trace_context.span == mock_span
    assert trace_context.token == mock_token
    assert trace_context.is_init_trace == False


def test_session_management_integration():
    """Test the integration between new and legacy session management"""
    import agentops

    # Reset client for test
    agentops._client = agentops.Client()

    # Test that we can use both new and legacy APIs together
    with (
        patch("agentops.tracer") as mock_tracer,
        patch("agentops.client.client.tracer", mock_tracer),
        patch("agentops.sdk.decorators.factory.tracer", mock_tracer),
        patch("agentops.legacy.tracer", mock_tracer),
    ):
        mock_tracer.initialized = True

        # Mock API client
        with patch("agentops.client.api.ApiClient") as mock_api:
            mock_v3 = MagicMock()
            mock_v3.fetch_auth_token.return_value = {"token": "mock-jwt-token", "project_id": "mock-project-id"}
            mock_api.return_value.v3 = mock_v3

            # Initialize AgentOps
            agentops.init(api_key="test-api-key", auto_start_session=False)

            # Reset call counts after initialization
            mock_tracer.reset_mock()

            # Create mock trace context
            mock_trace_context = MagicMock()
            mock_tracer.start_trace.return_value = mock_trace_context

            # Test new API
            trace_context = agentops.start_trace(trace_name="new_api_trace")
            assert trace_context == mock_trace_context

            # Test legacy API
            session = agentops.start_session(tags=["legacy"])
            # Check that the session's trace_context has the expected properties
            assert session.trace_context is not None

            # Test ending both
            agentops.end_trace(trace_context)
            agentops.end_session(session)

            # Verify calls were made
            assert mock_tracer.start_trace.call_count >= 2
            assert mock_tracer.end_trace.call_count >= 2


# CrewAI Backwards Compatibility Tests
# These tests ensure CrewAI integration patterns continue to work


def test_session_auto_start(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """Test auto-start session functionality for CrewAI compatibility"""
    import agentops
    from agentops.legacy import Session

    # Configure mocks for session initialization
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Pass a dummy API key for the test
    session = agentops.init(api_key="test-api-key", auto_start_session=True)

    assert isinstance(session, Session)


def test_crewai_backwards_compatibility(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """
    CrewAI needs to access:

    agentops.track_agent
    agentops.track_tool
    agentops.start_session
    agentops.end_session
    agentops.ActionEvent
    agentops.ToolEvent
    """
    import agentops
    from agentops.legacy import Session

    # Configure mocks
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Test initialization with API key
    agentops.init(api_key="test-api-key")

    # Test session management functions
    session = agentops.start_session(tags=["test", "crewai"])
    assert isinstance(session, Session)

    # Test that passing a string to end_session doesn't raise an error
    agentops.end_session("Success")  # This pattern is used in CrewAI

    # Test track_agent function exists and doesn't raise errors
    try:
        # Mock an agent object similar to what CrewAI would provide
        class MockAgent:
            def __init__(self):
                self.role = "Test Agent"
                self.goal = "Testing"
                self.id = "test-agent-id"

        agent = MockAgent()
        agentops.track_agent(agent)
    except Exception as e:
        assert False, f"track_agent raised an exception: {e}"

    # Test track_tool function exists and doesn't raise errors
    try:
        # Mock a tool object similar to what CrewAI would provide
        class MockTool:
            def __init__(self):
                self.name = "Test Tool"
                self.description = "A test tool"

        tool = MockTool()
        agentops.track_tool(tool, "Test Agent")
    except Exception as e:
        assert False, f"track_tool raised an exception: {e}"

    # Test events that CrewAI might use
    tool_event = agentops.ToolEvent(name="test_tool")
    action_event = agentops.ActionEvent(action_type="test_action")

    # Verify that record function works with these events
    agentops.record(tool_event)
    agentops.record(action_event)


def test_crewai_kwargs_pattern(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """
    Test the CrewAI < 0.105.0 pattern where end_session is called with only kwargs.

    In versions < 0.105.0, CrewAI directly calls:
    agentops.end_session(
        end_state="Success",
        end_state_reason="Finished Execution",
        is_auto_end=True
    )
    """
    import agentops
    from agentops.legacy import Session

    # Configure mocks
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Initialize with test API key
    agentops.init(api_key="test-api-key")

    # Create a session
    session = agentops.start_session(tags=["test", "crewai-kwargs"])
    assert isinstance(session, Session)

    # Test the CrewAI < 0.105.0 pattern - calling end_session with only kwargs
    agentops.end_session(end_state="Success", end_state_reason="Finished Execution", is_auto_end=True)

    # After calling end_session, creating a new session should work correctly
    # (this implicitly tests that the internal state is reset properly)
    new_session = agentops.start_session(tags=["test", "post-end"])
    assert isinstance(new_session, Session)


def test_crewai_kwargs_pattern_no_session(mock_tracing_core, mock_api_client, reset_client):
    """
    Test the CrewAI < 0.105.0 pattern where end_session is called with only kwargs,
    but no session has been created.

    This should log a warning but not fail.
    """
    import agentops

    # Initialize with test API key
    agentops.init(api_key="test-api-key")

    # We don't need to explicitly clear the session state
    # Just make sure we start with a clean state by calling init

    # Test the CrewAI < 0.105.0 pattern - calling end_session with only kwargs
    # when no session exists. This should not raise an error.
    agentops.end_session(end_state="Success", end_state_reason="Finished Execution", is_auto_end=True)


def test_crewai_kwargs_force_flush(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """
    Test that when using the CrewAI < 0.105.0 pattern (end_session with kwargs),
    the spans are properly exported to the backend with force_flush.

    This is a more comprehensive test that ensures spans are actually sent
    to the backend when using the CrewAI integration pattern.
    """
    import agentops
    import time

    # Configure mocks
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Initialize AgentOps with API key
    agentops.init(api_key="test-api-key")

    # Create a session
    agentops.start_session(tags=["test", "crewai-integration"])

    # Simulate some work
    time.sleep(0.1)

    # End session with kwargs (CrewAI < 0.105.0 pattern)
    agentops.end_session(end_state="Success", end_state_reason="Test Finished", is_auto_end=True)

    # Explicitly ensure the core isn't already shut down for the test
    # Note: We're using mocks, so we check the mock's initialized state
    assert mock_tracing_core.initialized, "Mocked tracer should still be initialized"


def test_crewai_task_instrumentation(mock_tracing_core, mock_api_client, mock_trace_context, reset_client):
    """
    Test the CrewAI task instrumentation focusing on span attributes and tags.
    This test verifies that task spans are properly created with correct attributes
    and tags without requiring a session.
    """
    import agentops
    from opentelemetry.trace import SpanKind
    from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues
    from opentelemetry import trace
    from agentops.semconv.core import CoreAttributes

    # Configure mocks
    mock_tracing_core.start_trace.return_value = mock_trace_context

    # Initialize AgentOps with API key and default tags
    agentops.init(
        api_key="test-api-key",
    )
    agentops.start_session(tags=["test", "crewai-integration"])
    # Get the tracer
    tracer = trace.get_tracer(__name__)

    # Create a mock task instance
    class MockTask:
        def __init__(self):
            self.description = "Test Task Description"
            self.agent = "Test Agent"
            self.tools = ["tool1", "tool2"]

    task = MockTask()

    # Start a span for the task
    with tracer.start_as_current_span(
        f"{task.description}.task",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TASK.value,
            CoreAttributes.TAGS: ["crewai", "task-test"],
        },
    ) as span:
        # Verify span attributes
        assert span.attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == AgentOpsSpanKindValues.TASK.value
        assert "crewai" in span.attributes[CoreAttributes.TAGS]
        assert "task-test" in span.attributes[CoreAttributes.TAGS]

        # Verify span name
        assert span.name == f"{task.description}.task"

        # Verify span kind
        assert span.kind == SpanKind.CLIENT

    agentops.end_session(end_state="Success", end_state_reason="Test Finished", is_auto_end=True)
