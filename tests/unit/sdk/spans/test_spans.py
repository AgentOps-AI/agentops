import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID
import json

from opentelemetry.trace import StatusCode

from agentops.sdk.types import TracingConfig
from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.spans.agent import AgentSpan
from agentops.sdk.spans.tool import ToolSpan
from agentops.sdk.spans.custom import CustomSpan


class TestSessionSpan(unittest.TestCase):
    """Test the SessionSpan class."""

    @patch("agentops.sdk.spans.session.TracingCore")
    def test_init(self, mock_tracing_core):
        """Test initialization."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        config = {"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000}
        
        # Test
        span = SessionSpan(
            name="test_session",
            config=config,
            tags=["tag1", "tag2"],
            host_env={"os": "linux"}
        )
        
        # Verify
        self.assertEqual(span.name, "test_session")
        self.assertEqual(span.kind, "session")
        self.assertEqual(span._config, config)
        self.assertEqual(span._tags, ["tag1", "tag2"])
        self.assertEqual(span._host_env, {"os": "linux"})
        self.assertEqual(span._state, "INITIALIZING")
        self.assertIsNone(span._state_reason)
        mock_core.initialize_from_config.assert_called_once_with(config)

    def test_start(self):
        """Test starting a session span."""
        # Set up
        span = SessionSpan(
            name="test_session",
            config={"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000}
        )
        span.set_state = MagicMock()
        super_start = MagicMock()
        with patch("agentops.sdk.spans.session.SpannedBase.start", super_start):
            # Test
            result = span.start()
            
            # Verify
            self.assertEqual(result, span)
            super_start.assert_called_once()
            span.set_state.assert_called_once()

    def test_end(self):
        """Test ending a session span."""
        # Set up
        span = SessionSpan(
            name="test_session",
            config={"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000}
        )
        span.set_state = MagicMock()
        super_end = MagicMock()
        with patch("agentops.sdk.spans.session.SpannedBase.end", super_end):
            # Test with default state
            result = span.end()
            
            # Verify
            span.set_state.assert_called_once_with("SUCCEEDED")
            super_end.assert_called_once_with(StatusCode.OK)
            
            # Test with custom state
            span.set_state.reset_mock()
            super_end.reset_mock()
            result = span.end("FAILED")
            
            # Verify
            span.set_state.assert_called_once_with("FAILED")
            super_end.assert_called_once_with(StatusCode.ERROR)

    def test_set_state(self):
        """Test setting the session state."""
        # Set up
        span = SessionSpan(
            name="test_session",
            config={"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000}
        )
        span.set_attribute = MagicMock()
        span.set_status = MagicMock()
        
        # Import constants
        from agentops.semconv.core import CoreAttributes
        
        # Test with simple state
        span.set_state("RUNNING")
        self.assertEqual(span._state, "RUNNING")
        self.assertIsNone(span._state_reason)
        span.set_attribute.assert_called_once_with("session.state", "RUNNING")
        span.set_status.assert_not_called()
        
        # Test with state and reason
        span.set_attribute.reset_mock()
        span.set_state("FAILED", "Something went wrong")
        self.assertEqual(span._state, "FAILED")
        self.assertEqual(span._state_reason, "Something went wrong")
        # Check that set_attribute was called twice (once for state, once for error message)
        self.assertEqual(span.set_attribute.call_count, 2)
        # Check that the first call was for session.state
        self.assertEqual(span.set_attribute.call_args_list[0][0][0], "session.state")
        self.assertEqual(span.set_attribute.call_args_list[0][0][1], "FAILED(Something went wrong)")
        # Check that the second call was for error.message
        self.assertEqual(span.set_attribute.call_args_list[1][0][0], CoreAttributes.ERROR_MESSAGE)
        self.assertEqual(span.set_attribute.call_args_list[1][0][1], "Something went wrong")
        
        # Test with normalized state
        span.set_attribute.reset_mock()
        span.set_status.reset_mock()
        span.set_state("success")
        self.assertEqual(span._state, "SUCCEEDED")
        self.assertIsNone(span._state_reason)
        span.set_attribute.assert_called_once_with("session.state", "SUCCEEDED")
        span.set_status.assert_called_once_with(StatusCode.OK)

    def test_state_property(self):
        """Test the state property."""
        # Set up
        span = SessionSpan(
            name="test_session",
            config={"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000}
        )
        
        # Test without reason
        span._state = "RUNNING"
        span._state_reason = None
        self.assertEqual(span.state, "RUNNING")
        
        # Test with reason
        span._state = "FAILED"
        span._state_reason = "Something went wrong"
        self.assertEqual(span.state, "FAILED(Something went wrong)")

    def test_add_tag(self):
        """Test adding a tag."""
        # Set up
        span = SessionSpan(
            name="test_session",
            config={"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000},
            tags=["tag1"]
        )
        span.set_attribute = MagicMock()
        
        # Test adding a new tag
        span.add_tag("tag2")
        self.assertEqual(span._tags, ["tag1", "tag2"])
        span.set_attribute.assert_called_once_with("session.tags", json.dumps(["tag1", "tag2"]))
        
        # Test adding an existing tag
        span.set_attribute.reset_mock()
        span.add_tag("tag1")
        self.assertEqual(span._tags, ["tag1", "tag2"])
        span.set_attribute.assert_called_once_with("session.tags", json.dumps(["tag1", "tag2"]))

    def test_add_tags(self):
        """Test adding multiple tags."""
        # Set up
        span = SessionSpan(
            name="test_session",
            config={"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000},
            tags=["tag1"]
        )
        span.add_tag = MagicMock()
        
        # Test adding multiple tags
        span.add_tags(["tag2", "tag3"])
        self.assertEqual(span.add_tag.call_count, 2)
        span.add_tag.assert_any_call("tag2")
        span.add_tag.assert_any_call("tag3")

    def test_to_dict(self):
        """Test converting to dictionary."""
        # Set up
        config = {"service_name": "test_service", "max_queue_size": 512, "max_wait_time": 5000}
        span = SessionSpan(
            name="test_session",
            config=config,
            tags=["tag1", "tag2"],
            host_env={"os": "linux"}
        )
        span._state = "RUNNING"
        
        # Test
        result = span.to_dict()
        
        # Verify
        self.assertEqual(result["name"], "test_session")
        self.assertEqual(result["kind"], "session")
        self.assertEqual(result["tags"], ["tag1", "tag2"])
        # Only check host_env if it's in the result
        if "host_env" in result:
            self.assertEqual(result["host_env"], {"os": "linux"})
        self.assertEqual(result["state"], "RUNNING")
        # Only check config if it's in the result
        if "config" in result:
            self.assertEqual(result["config"], config)


class TestAgentSpan(unittest.TestCase):
    """Test the AgentSpan class."""

    def test_init(self):
        """Test initialization."""
        # Test
        span = AgentSpan(
            name="test_agent",
            agent_type="assistant",
            parent=None
        )
        
        # Verify
        self.assertEqual(span.name, "test_agent")
        self.assertEqual(span.kind, "agent")
        self.assertEqual(span._agent_type, "assistant")
        self.assertTrue(span.immediate_export)
        
        # Import the constants at test time to avoid circular imports
        from agentops.semconv.agent import AgentAttributes
        self.assertEqual(span._attributes[AgentAttributes.AGENT_NAME], "test_agent")
        self.assertEqual(span._attributes[AgentAttributes.AGENT_ROLE], "assistant")

    def test_record_action(self):
        """Test recording an action."""
        # Set up
        span = AgentSpan(
            name="test_agent",
            agent_type="assistant"
        )
        span.set_attribute = MagicMock()
        span.update = MagicMock()
        
        # Test without details
        span.record_action("search")
        span.set_attribute.assert_called_once_with("agent.action", "search")
        span.update.assert_called_once()
        
        # Test with details
        span.set_attribute.reset_mock()
        span.update.reset_mock()
        span.record_action("search", {"query": "test query"})
        span.set_attribute.assert_any_call("agent.action", "search")
        span.set_attribute.assert_any_call("agent.action.query", "test query")
        span.update.assert_called_once()

    def test_record_thought(self):
        """Test recording a thought."""
        # Set up
        span = AgentSpan(
            name="test_agent",
            agent_type="assistant"
        )
        span.set_attribute = MagicMock()
        span.update = MagicMock()
        
        # Test
        span.record_thought("I should search for information")
        span.set_attribute.assert_called_once_with("agent.thought", "I should search for information")
        span.update.assert_called_once()

    def test_record_error(self):
        """Test recording an error."""
        # Set up
        span = AgentSpan(
            name="test_agent",
            agent_type="assistant"
        )
        span.set_attribute = MagicMock()
        span.update = MagicMock()
        
        # Test with string
        span.record_error("Something went wrong")
        span.set_attribute.assert_called_once_with("agent.error", "Something went wrong")
        span.update.assert_called_once()
        
        # Test with exception
        span.set_attribute.reset_mock()
        span.update.reset_mock()
        span.record_error(ValueError("Invalid value"))
        span.set_attribute.assert_called_once_with("agent.error", "Invalid value")
        span.update.assert_called_once()

    def test_to_dict(self):
        """Test converting to dictionary."""
        # Set up
        span = AgentSpan(
            name="test_agent",
            agent_type="assistant"
        )
        
        # Test
        result = span.to_dict()
        
        # Verify
        self.assertEqual(result["name"], "test_agent")
        self.assertEqual(result["kind"], "agent")
        self.assertEqual(result["agent_type"], "assistant")


class TestToolSpan(unittest.TestCase):
    """Test the ToolSpan class."""

    def test_init(self):
        """Test initialization."""
        # Test
        span = ToolSpan(
            name="test_tool",
            tool_type="search",
            parent=None
        )
        
        # Verify
        self.assertEqual(span.name, "test_tool")
        self.assertEqual(span.kind, "tool")
        self.assertEqual(span._tool_type, "search")
        self.assertFalse(span.immediate_export)
        
        # Import the constants at test time to avoid circular imports
        from agentops.semconv.tool import ToolAttributes
        self.assertEqual(span._attributes[ToolAttributes.TOOL_NAME], "test_tool")
        self.assertEqual(span._attributes[ToolAttributes.TOOL_DESCRIPTION], "search")
        self.assertIsNone(span._input)
        self.assertIsNone(span._output)

    def test_set_input(self):
        """Test setting input."""
        # Set up
        span = ToolSpan(
            name="test_tool",
            tool_type="search"
        )
        span.set_attribute = MagicMock()
        
        # Import the constants at test time to avoid circular imports
        from agentops.semconv.tool import ToolAttributes
        
        # Test with string
        span.set_input("test query")
        self.assertEqual(span._input, "test query")
        span.set_attribute.assert_called_once_with(ToolAttributes.TOOL_PARAMETERS, "test query")
        
        # Test with complex object
        span.set_attribute.reset_mock()
        input_data = {"query": "test query", "filters": ["filter1", "filter2"]}
        span.set_input(input_data)
        self.assertEqual(span._input, input_data)
        span.set_attribute.assert_called_once()
        self.assertEqual(span.set_attribute.call_args[0][0], ToolAttributes.TOOL_PARAMETERS)
        self.assertIsInstance(span.set_attribute.call_args[0][1], str)

    def test_set_output(self):
        """Test setting output."""
        # Set up
        span = ToolSpan(
            name="test_tool",
            tool_type="search"
        )
        span.set_attribute = MagicMock()
        
        # Import the constants at test time to avoid circular imports
        from agentops.semconv.tool import ToolAttributes
        
        # Test with string
        span.set_output("test result")
        self.assertEqual(span._output, "test result")
        span.set_attribute.assert_called_once_with(ToolAttributes.TOOL_RESULT, "test result")
        
        # Test with complex object
        span.set_attribute.reset_mock()
        output_data = {"results": ["result1", "result2"], "count": 2}
        span.set_output(output_data)
        self.assertEqual(span._output, output_data)
        span.set_attribute.assert_called_once()
        self.assertEqual(span.set_attribute.call_args[0][0], ToolAttributes.TOOL_RESULT)
        self.assertIsInstance(span.set_attribute.call_args[0][1], str)

    def test_to_dict(self):
        """Test converting to dictionary."""
        # Set up
        span = ToolSpan(
            name="test_tool",
            tool_type="search"
        )
        span._input = "test query"
        span._output = "test result"
        
        # Test
        result = span.to_dict()
        
        # Verify
        self.assertEqual(result["name"], "test_tool")
        self.assertEqual(result["kind"], "tool")
        self.assertEqual(result["tool_type"], "search")
        self.assertEqual(result["input"], "test query")
        self.assertEqual(result["output"], "test result")


class TestCustomSpan(unittest.TestCase):
    """Test the CustomSpan class."""

    def test_init(self):
        """Test initialization."""
        # Test
        span = CustomSpan(
            name="test_custom",
            kind="custom_kind",
            parent=None
        )
        
        # Verify
        self.assertEqual(span.name, "test_custom")
        self.assertEqual(span.kind, "custom_kind")
        self.assertEqual(span._attributes["custom.name"], "test_custom")
        self.assertEqual(span._attributes["custom.kind"], "custom_kind")

    def test_add_event(self):
        """Test adding an event."""
        # Set up
        span = CustomSpan(
            name="test_custom",
            kind="custom_kind"
        )
        span._span = MagicMock()
        span.update = MagicMock()
        
        # Test without attributes
        span.add_event("test_event")
        span._span.add_event.assert_called_once_with("test_event", None)
        span.update.assert_called_once()
        
        # Test with attributes
        span._span.reset_mock()
        span.update.reset_mock()
        attributes = {"key": "value"}
        span.add_event("test_event", attributes)
        span._span.add_event.assert_called_once_with("test_event", attributes)
        span.update.assert_called_once()


if __name__ == "__main__":
    unittest.main() 
