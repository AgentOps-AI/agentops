import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from agentops.config import Config
from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.tool import tool
from agentops.sdk.decorators.llm import llm


class TestSessionDecorator(unittest.TestCase):
    """Test the session decorator."""

    @patch("agentops.sdk.decorators.session.TracingCore")
    def test_class_decoration(self, mock_tracing_core):
        """Test decorating a class."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        mock_span = MagicMock()
        mock_core.create_span.return_value = mock_span
        
        # Define a class to decorate
        @session(name="test_session", tags=["tag1", "tag2"])
        class TestClass:
            def __init__(self, arg1, arg2=None):
                self.arg1 = arg1
                self.arg2 = arg2
        
        # Test
        instance = TestClass("value1", arg2="value2")
        
        # Verify
        self.assertEqual(instance.arg1, "value1")
        self.assertEqual(instance.arg2, "value2")
        self.assertEqual(instance._session_span, mock_span)
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        self.assertEqual(mock_core.create_span.call_args[1]["kind"], "session")
        self.assertEqual(mock_core.create_span.call_args[1]["name"], "test_session")
        self.assertEqual(mock_core.create_span.call_args[1]["tags"], ["tag1", "tag2"])
        self.assertTrue(mock_core.create_span.call_args[1]["immediate_export"])
        
        # Test get_session_span method
        self.assertEqual(instance.get_session_span(), mock_span)

    @patch("agentops.sdk.decorators.session.TracingCore")
    def test_function_decoration(self, mock_tracing_core):
        """Test decorating a function."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        mock_span = MagicMock()
        mock_core.create_span.return_value = mock_span
        
        # Define a function to decorate
        @session(name="test_session", tags=["tag1", "tag2"])
        def test_function(arg1, arg2=None, session_span=None):
            return {
                "arg1": arg1,
                "arg2": arg2,
                "session_span": session_span
            }
        
        # Test
        result = test_function("value1", arg2="value2")
        
        # Verify
        self.assertEqual(result["arg1"], "value1")
        self.assertEqual(result["arg2"], "value2")
        self.assertEqual(result["session_span"], mock_span)
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        self.assertEqual(mock_core.create_span.call_args[1]["kind"], "session")
        self.assertEqual(mock_core.create_span.call_args[1]["name"], "test_session")
        self.assertEqual(mock_core.create_span.call_args[1]["tags"], ["tag1", "tag2"])
        self.assertTrue(mock_core.create_span.call_args[1]["immediate_export"])


class TestAgentDecorator(unittest.TestCase):
    """Test the agent decorator."""

    @patch("agentops.sdk.decorators.agent.get_current_session")
    @patch("agentops.sdk.decorators.agent.TracingCore")
    def test_class_decoration(self, mock_tracing_core, mock_get_current_session):
        """Test decorating a class."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        mock_agent_span = MagicMock()
        mock_core.create_span.return_value = mock_agent_span
        mock_session = MagicMock()
        mock_session.span = MagicMock()
        mock_get_current_session.return_value = mock_session
        
        # Define a class to decorate
        @agent(name="test_agent", agent_type="assistant")
        class TestAgent:
            def __init__(self, arg1, arg2=None):
                self.arg1 = arg1
                self.arg2 = arg2
        
        # Test
        instance = TestAgent("value1", arg2="value2")
        
        # Verify
        self.assertEqual(instance.arg1, "value1")
        self.assertEqual(instance.arg2, "value2")
        self.assertEqual(instance._agent_span, mock_agent_span)
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        self.assertEqual(mock_core.create_span.call_args[1]["kind"], "agent")
        self.assertEqual(mock_core.create_span.call_args[1]["name"], "test_agent")
        self.assertEqual(mock_core.create_span.call_args[1]["parent"], mock_session.span)
        self.assertEqual(mock_core.create_span.call_args[1]["agent_type"], "assistant")
        self.assertTrue(mock_core.create_span.call_args[1]["immediate_export"])
        
        # Test get_agent_span method
        self.assertEqual(instance.get_agent_span(), mock_agent_span)
        
        # Test with no active session
        mock_get_current_session.return_value = None
        mock_tracing_core.reset_mock()
        mock_core.reset_mock()
        
        instance = TestAgent("value1", arg2="value2")
        
        # Verify no span was created
        mock_tracing_core.get_instance.assert_not_called()
        mock_core.create_span.assert_not_called()
        self.assertFalse(hasattr(instance, "_agent_span"))

    @patch("agentops.sdk.decorators.agent.get_current_session")
    @patch("agentops.sdk.decorators.agent.TracingCore")
    def test_function_decoration(self, mock_tracing_core, mock_get_current_session):
        """Test decorating a function."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        mock_agent_span = MagicMock()
        mock_core.create_span.return_value = mock_agent_span
        mock_session = MagicMock()
        mock_session.span = MagicMock()
        mock_get_current_session.return_value = mock_session
        
        # Define a function to decorate
        @agent(name="test_agent", agent_type="assistant")
        def test_function(arg1, arg2=None, agent_span=None):
            return {
                "arg1": arg1,
                "arg2": arg2,
                "agent_span": agent_span
            }
        
        # Test
        result = test_function("value1", arg2="value2")
        
        # Verify
        self.assertEqual(result["arg1"], "value1")
        self.assertEqual(result["arg2"], "value2")
        self.assertEqual(result["agent_span"], mock_agent_span)
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        self.assertEqual(mock_core.create_span.call_args[1]["kind"], "agent")
        self.assertEqual(mock_core.create_span.call_args[1]["name"], "test_agent")
        self.assertEqual(mock_core.create_span.call_args[1]["parent"], mock_session.span)
        self.assertEqual(mock_core.create_span.call_args[1]["agent_type"], "assistant")
        self.assertTrue(mock_core.create_span.call_args[1]["immediate_export"])
        
        # Test with no active session
        mock_get_current_session.return_value = None
        mock_tracing_core.reset_mock()
        mock_core.reset_mock()
        
        result = test_function("value1", arg2="value2")
        
        # Verify no span was created
        mock_tracing_core.get_instance.assert_not_called()
        mock_core.create_span.assert_not_called()
        self.assertIsNone(result["agent_span"])


class TestToolDecorator(unittest.TestCase):
    """Test the tool decorator."""

    @patch("agentops.sdk.decorators.tool.get_current_session")
    @patch("agentops.sdk.decorators.tool.TracingCore")
    def test_function_decoration(self, mock_tracing_core, mock_get_current_session):
        """Test decorating a function."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        mock_span = MagicMock()
        mock_core.create_span.return_value = mock_span
        
        # Define a function to decorate
        @tool(name="test_tool", tool_type="search")
        def test_function(arg1, arg2=None, tool_span=None):
            return {
                "arg1": arg1,
                "arg2": arg2,
                "tool_span": tool_span
            }
        
        # Test
        result = test_function("value1", arg2="value2")
        
        # Verify
        self.assertEqual(result["arg1"], "value1")
        self.assertEqual(result["arg2"], "value2")
        self.assertEqual(result["tool_span"], mock_span)
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        self.assertEqual(mock_core.create_span.call_args[1]["kind"], "tool")
        self.assertEqual(mock_core.create_span.call_args[1]["name"], "test_tool")
        self.assertEqual(mock_core.create_span.call_args[1]["tool_type"], "search")
        self.assertTrue(mock_core.create_span.call_args[1]["immediate_export"])


class TestLLMDecorator(unittest.TestCase):
    """Test the LLM decorator."""

    @patch("agentops.sdk.decorators.llm.get_current_session")
    @patch("agentops.sdk.decorators.llm.TracingCore")
    def test_function_decoration(self, mock_tracing_core, mock_get_current_session):
        """Test decorating a function."""
        # Set up
        mock_core = MagicMock()
        mock_tracing_core.get_instance.return_value = mock_core
        mock_llm_span = MagicMock()
        mock_core.create_span.return_value = mock_llm_span
        mock_session = MagicMock()
        mock_session.span = MagicMock()
        mock_get_current_session.return_value = mock_session
        
        # Define a function to decorate
        @llm(name="test_llm", model="gpt-4")
        def test_function(prompt=None, messages=None):
            if prompt:
                return {
                    "choices": [{"text": f"Response to: {prompt}"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20}
                }
            elif messages:
                return {
                    "choices": [{"message": {"content": f"Response to: {messages[-1]['content']}"}}],
                    "usage": {"prompt_tokens": 15, "completion_tokens": 25}
                }
            return None
        
        # Test with prompt
        result = test_function(prompt="What is the capital of France?")
        
        # Verify
        self.assertEqual(result["choices"][0]["text"], "Response to: What is the capital of France?")
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        self.assertEqual(mock_core.create_span.call_args[1]["kind"], "llm")
        self.assertEqual(mock_core.create_span.call_args[1]["name"], "test_llm")
        self.assertEqual(mock_core.create_span.call_args[1]["parent"], mock_session.span)
        self.assertEqual(mock_core.create_span.call_args[1]["model"], "gpt-4")
        self.assertTrue(mock_core.create_span.call_args[1]["immediate_export"])
        
        # Verify prompt, response, and tokens were recorded
        mock_llm_span.set_prompt.assert_called_once_with("What is the capital of France?")
        mock_llm_span.set_response.assert_called_once_with("Response to: What is the capital of France?")
        mock_llm_span.set_tokens.assert_called_once_with(10, 20)
        
        # Test with messages
        mock_tracing_core.reset_mock()
        mock_core.reset_mock()
        mock_llm_span.reset_mock()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]
        result = test_function(messages=messages)
        
        # Verify
        self.assertEqual(result["choices"][0]["message"]["content"], "Response to: What is the capital of France?")
        mock_tracing_core.get_instance.assert_called_once()
        mock_core.create_span.assert_called_once()
        
        # Verify messages, response, and tokens were recorded
        mock_llm_span.set_prompt.assert_called_once_with(messages)
        mock_llm_span.set_response.assert_called_once_with("Response to: What is the capital of France?")
        mock_llm_span.set_tokens.assert_called_once_with(15, 25)
        
        # Test with no active session
        mock_get_current_session.return_value = None
        mock_tracing_core.reset_mock()
        mock_core.reset_mock()
        mock_llm_span.reset_mock()
        
        result = test_function(prompt="What is the capital of France?")
        
        # Verify no span was created
        self.assertEqual(result["choices"][0]["text"], "Response to: What is the capital of France?")
        mock_tracing_core.get_instance.assert_not_called()
        mock_core.create_span.assert_not_called()
        mock_llm_span.set_prompt.assert_not_called()
        mock_llm_span.set_response.assert_not_called()
        mock_llm_span.set_tokens.assert_not_called()


if __name__ == "__main__":
    unittest.main() 