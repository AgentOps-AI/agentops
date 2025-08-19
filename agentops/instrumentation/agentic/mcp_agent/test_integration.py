"""
Tests for MCP Agent integration with AgentOps.

These tests verify that the integration works correctly and captures
the expected spans and attributes.
"""

import unittest
import logging
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestMCPAgentIntegration(unittest.TestCase):
    """Test cases for MCP Agent integration."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock AgentOps client
        self.mock_client = Mock()
        
        # Mock OpenTelemetry span
        self.mock_span = Mock()
        self.mock_span.set_attribute = Mock()
        self.mock_span.record_exception = Mock()
        self.mock_span.set_status = Mock()
        
        # Mock span context manager
        self.mock_span_context = Mock()
        self.mock_span_context.__enter__ = Mock(return_value=self.mock_span)
        self.mock_span_context.__exit__ = Mock(return_value=None)
    
    def test_mcp_agent_span_attributes(self):
        """Test MCP Agent span attributes are set correctly."""
        from agentops.instrumentation.agentic.mcp_agent.mcp_agent_span_attributes import (
            set_mcp_agent_span_attributes,
            set_mcp_agent_tool_attributes
        )
        
        # Test basic span attributes
        set_mcp_agent_span_attributes(
            self.mock_span,
            operation="test_operation",
            session_id="test_session",
            agent_name="test_agent"
        )
        
        # Verify attributes were set
        expected_calls = [
            (("mcp_agent.operation", "test_operation"),),
            (("mcp_agent.session_id", "test_session"),),
            (("mcp_agent.agent_name", "test_agent"),),
        ]
        
        for call_args in expected_calls:
            self.mock_span.set_attribute.assert_any_call(*call_args)
        
        # Test tool attributes
        set_mcp_agent_tool_attributes(
            self.mock_span,
            tool_name="test_tool",
            tool_arguments={"arg1": "value1"},
            tool_error=False
        )
        
        # Verify tool attributes were set
        tool_calls = [
            (("mcp_agent.tool_name", "test_tool"),),
            (("mcp_agent.tool_arguments", "{'arg1': 'value1'}"),),
            (("mcp_agent.tool_error", "False"),),
        ]
        
        for call_args in tool_calls:
            self.mock_span.set_attribute.assert_any_call(*call_args)
    
    @patch('agentops.instrumentation.agentic.mcp_agent.telemetry_hook.create_span')
    def test_mcp_agent_span_context_manager(self, mock_create_span):
        """Test MCP Agent span context manager."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import mcp_agent_span
        
        mock_create_span.return_value = self.mock_span_context
        
        with mcp_agent_span(
            "test_span",
            operation="test_operation",
            session_id="test_session"
        ):
            pass
        
        # Verify span was created with correct parameters
        mock_create_span.assert_called_once()
        call_args = mock_create_span.call_args
        self.assertEqual(call_args[0][0], "test_span")
        
        # Verify attributes were set
        self.mock_span.set_attribute.assert_called()
    
    @patch('agentops.instrumentation.agentic.mcp_agent.telemetry_hook.create_span')
    def test_mcp_agent_traced_decorator(self, mock_create_span):
        """Test MCP Agent traced decorator."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import mcp_agent_traced
        
        mock_create_span.return_value = self.mock_span_context
        
        @mcp_agent_traced(
            name="test_decorated",
            operation="test_operation",
            agent_name="test_agent"
        )
        def test_function():
            return "test_result"
        
        result = test_function()
        
        # Verify function executed
        self.assertEqual(result, "test_result")
        
        # Verify span was created
        mock_create_span.assert_called_once()
    
    @patch('agentops.instrumentation.agentic.mcp_agent.telemetry_hook.create_span')
    def test_mcp_agent_span_error_handling(self, mock_create_span):
        """Test error handling in MCP Agent spans."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import mcp_agent_span
        
        mock_create_span.return_value = self.mock_span_context
        
        test_exception = ValueError("Test error")
        
        with self.assertRaises(ValueError):
            with mcp_agent_span("test_error_span"):
                raise test_exception
        
        # Verify exception was recorded
        self.mock_span.record_exception.assert_called_once_with(test_exception)
        self.mock_span.set_status.assert_called_once()
    
    def test_enhance_mcp_agent_span(self):
        """Test enhancing existing spans with MCP Agent attributes."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import enhance_mcp_agent_span
        
        enhance_mcp_agent_span(
            self.mock_span,
            operation="enhanced_operation",
            session_id="enhanced_session"
        )
        
        # Verify AgentOps span kind was set
        self.mock_span.set_attribute.assert_any_call(
            "agentops.span.kind", "agentic"
        )
        
        # Verify MCP Agent attributes were set
        self.mock_span.set_attribute.assert_any_call(
            "mcp_agent.operation", "enhanced_operation"
        )
        self.mock_span.set_attribute.assert_any_call(
            "mcp_agent.session_id", "enhanced_session"
        )
    
    @patch('agentops.instrumentation.agentic.mcp_agent.telemetry_hook.MCPAgentTelemetryHook')
    def test_telemetry_hook_initialization(self, mock_hook_class):
        """Test telemetry hook initialization."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import (
            hook_mcp_agent_telemetry,
            unhook_mcp_agent_telemetry
        )
        
        mock_hook = Mock()
        mock_hook_class.return_value = mock_hook
        
        # Test hooking
        hook_mcp_agent_telemetry()
        mock_hook.hook_into_telemetry.assert_called_once()
        
        # Test unhooking
        unhook_mcp_agent_telemetry()
        mock_hook.unhook_from_telemetry.assert_called_once()
    
    def test_instrumentor_initialization(self):
        """Test MCP Agent instrumentor initialization."""
        from agentops.instrumentation.agentic.mcp_agent.instrumentation import (
            MCPAgentInstrumentor,
            instrument_mcp_agent,
            uninstrument_mcp_agent
        )
        
        # Test instrumentor creation
        instrumentor = MCPAgentInstrumentor()
        self.assertIsNotNone(instrumentor)
        self.assertEqual(instrumentor.config.library_name, "mcp-agent")
        
        # Test instrumentation functions exist
        self.assertTrue(callable(instrument_mcp_agent))
        self.assertTrue(callable(uninstrument_mcp_agent))


class TestMCPAgentIntegrationWithMocks(unittest.TestCase):
    """Test cases that mock MCP Agent dependencies."""
    
    def setUp(self):
        """Set up test environment with mocked dependencies."""
        self.mock_telemetry = Mock()
        self.mock_telemetry_manager = Mock()
        
        # Mock the telemetry module
        self.telemetry_patcher = patch.dict('sys.modules', {
            'mcp_agent.tracing.telemetry': Mock(),
            'mcp_agent.core.context': Mock(),
            'mcp': Mock(),
        })
        self.telemetry_patcher.start()
    
    def tearDown(self):
        """Clean up test environment."""
        self.telemetry_patcher.stop()
    
    @patch('agentops.instrumentation.agentic.mcp_agent.telemetry_hook.MCPAgentTelemetryHook')
    def test_auto_hook_with_mcp_agent_available(self, mock_hook_class):
        """Test auto-hooking when MCP Agent is available."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import _auto_hook
        
        mock_hook = Mock()
        mock_hook_class.return_value = mock_hook
        
        # Simulate MCP Agent being available
        with patch('builtins.__import__', return_value=Mock()):
            _auto_hook()
            mock_hook.hook_into_telemetry.assert_called_once()
    
    @patch('agentops.instrumentation.agentic.mcp_agent.telemetry_hook.MCPAgentTelemetryHook')
    def test_auto_hook_without_mcp_agent(self, mock_hook_class):
        """Test auto-hooking when MCP Agent is not available."""
        from agentops.instrumentation.agentic.mcp_agent.telemetry_hook import _auto_hook
        
        mock_hook = Mock()
        mock_hook_class.return_value = mock_hook
        
        # Simulate MCP Agent not being available
        with patch('builtins.__import__', side_effect=ImportError("No module named 'mcp_agent'")):
            _auto_hook()
            # Should not call hook_into_telemetry when MCP Agent is not available
            mock_hook.hook_into_telemetry.assert_not_called()


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)