import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from agentops.config import Config
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators import session, agent, tool, llm


class TestIntegration(unittest.TestCase):
    """Test the integration of all components."""

    def setUp(self):
        """Set up the test."""
        # Reset the singleton instance
        TracingCore._instance = None
        
        # Create a mock for the span factory
        self.mock_factory_patcher = patch("agentops.sdk.core.SpanFactory")
        self.mock_factory = self.mock_factory_patcher.start()
        
        # Create mock spans
        self.mock_session_span = MagicMock()
        self.mock_agent_span = MagicMock()
        self.mock_tool_span = MagicMock()
        self.mock_llm_span = MagicMock()
        
        # Configure the factory to return the mock spans
        self.mock_factory.create_span.side_effect = lambda **kwargs: {
            "session": self.mock_session_span,
            "agent": self.mock_agent_span,
            "tool": self.mock_tool_span,
            "llm": self.mock_llm_span
        }.get(kwargs["kind"])
        
        # Create a mock for the current session
        self.mock_get_current_session_patcher = patch("agentops.sdk.decorators.agent.get_current_session")
        self.mock_get_current_session = self.mock_get_current_session_patcher.start()
        self.mock_get_current_session.return_value = MagicMock()
        self.mock_get_current_session.return_value.span = self.mock_session_span
        
        # Create a mock for the tool decorator
        self.mock_get_current_session_tool_patcher = patch("agentops.sdk.decorators.tool.get_current_session")
        self.mock_get_current_session_tool = self.mock_get_current_session_tool_patcher.start()
        self.mock_get_current_session_tool.return_value = MagicMock()
        self.mock_get_current_session_tool.return_value.span = self.mock_session_span
        
        # Create a mock for the llm decorator
        self.mock_get_current_session_llm_patcher = patch("agentops.sdk.decorators.llm.get_current_session")
        self.mock_get_current_session_llm = self.mock_get_current_session_llm_patcher.start()
        self.mock_get_current_session_llm.return_value = MagicMock()
        self.mock_get_current_session_llm.return_value.span = self.mock_session_span
    
    def tearDown(self):
        """Tear down the test."""
        self.mock_factory_patcher.stop()
        self.mock_get_current_session_patcher.stop()
        self.mock_get_current_session_tool_patcher.stop()
        self.mock_get_current_session_llm_patcher.stop()

    def test_full_workflow(self):
        """Test a full workflow with all decorators."""
        # Define the decorated components
        @session(name="test_session")
        class TestSession:
            def __init__(self):
                self.agent = TestAgent()
            
            def run(self):
                return self.agent.run("What is the capital of France?")
        
        @agent(name="test_agent", agent_type="assistant")
        class TestAgent:
            def run(self, query):
                self._agent_span.record_thought("I should search for information about France")
                result = self.search(query)
                response = self.generate_response(result)
                return response
            
            @tool(name="search", tool_type="search")
            def search(self, query):
                return f"Search results for: {query}"
            
            @llm(name="generate", model="gpt-4")
            def generate_response(self, context):
                return {
                    "choices": [{"text": f"Based on {context}, the capital of France is Paris."}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 30}
                }
        
        # Run the workflow
        session = TestSession()
        result = session.run()
        
        # Verify
        self.assertEqual(result["choices"][0]["text"], "Based on Search results for: What is the capital of France?, the capital of France is Paris.")
        
        # Verify session span
        self.mock_factory.create_span.assert_any_call(
            kind="session",
            name="test_session",
            parent=None,
            attributes={"export.immediate": True},
            auto_start=True,
            immediate_export=True,
            config=unittest.mock.ANY,
            tags=None
        )
        
        # Verify agent span
        self.mock_factory.create_span.assert_any_call(
            kind="agent",
            name="test_agent",
            parent=self.mock_session_span,
            attributes={"export.immediate": True},
            auto_start=True,
            immediate_export=True,
            agent_type="assistant"
        )
        
        # Verify tool span
        self.mock_factory.create_span.assert_any_call(
            kind="tool",
            name="search",
            parent=self.mock_agent_span,
            attributes={},
            auto_start=True,
            immediate_export=False,
            tool_type="search"
        )
        
        # Verify LLM span
        self.mock_factory.create_span.assert_any_call(
            kind="llm",
            name="generate",
            parent=self.mock_agent_span,
            attributes={"export.immediate": True},
            auto_start=True,
            immediate_export=True,
            model="gpt-4"
        )
        
        # Verify agent thought was recorded
        self.mock_agent_span.record_thought.assert_called_once_with("I should search for information about France")
        
        # Verify tool input/output was recorded
        self.mock_tool_span.set_input.assert_called_once()
        self.mock_tool_span.set_output.assert_called_once_with("Search results for: What is the capital of France?")
        
        # Verify LLM prompt/response was recorded
        self.mock_llm_span.set_prompt.assert_called_once()
        self.mock_llm_span.set_response.assert_called_once_with("Based on Search results for: What is the capital of France?, the capital of France is Paris.")
        self.mock_llm_span.set_tokens.assert_called_once_with(20, 30)


if __name__ == "__main__":
    unittest.main() 