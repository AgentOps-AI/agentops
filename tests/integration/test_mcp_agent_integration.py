"""Integration tests for MCP Agent instrumentation.

This module tests the integration between AgentOps and MCP Agent,
ensuring that telemetry is properly captured and integrated.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentops.instrumentation.providers.mcp_agent import MCPAgentInstrumentor
from agentops.instrumentation.providers.mcp_agent.config import Config


class TestMCPAgentIntegration:
    """Test suite for MCP Agent integration."""
    
    @pytest.fixture
    def setup_tracing(self):
        """Set up OpenTelemetry tracing for tests."""
        # Create in-memory exporter
        exporter = InMemorySpanExporter()
        
        # Set up tracer provider
        provider = TracerProvider()
        processor = SimpleSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        yield exporter
        
        # Clean up
        exporter.clear()
    
    @pytest.fixture
    def instrumentor(self):
        """Create an MCP Agent instrumentor instance."""
        config = Config(
            capture_prompts=True,
            capture_completions=True,
            capture_errors=True,
            capture_tool_calls=True,
            capture_workflows=True,
        )
        return MCPAgentInstrumentor(config)
    
    def test_instrumentor_initialization(self, instrumentor):
        """Test that the instrumentor initializes correctly."""
        assert instrumentor is not None
        assert instrumentor.library_name == "mcp-agent"
        assert instrumentor.config.capture_prompts is True
        assert instrumentor.config.capture_completions is True
    
    @patch("agentops.instrumentation.providers.mcp_agent.instrumentor.wrap_function_wrapper")
    def test_telemetry_manager_instrumentation(self, mock_wrap, instrumentor, setup_tracing):
        """Test that TelemetryManager is properly instrumented."""
        # Mock the mcp_agent module
        with patch.dict("sys.modules", {"mcp_agent.tracing.telemetry": MagicMock()}):
            # Instrument
            instrumentor.instrument()
            
            # Verify TelemetryManager.traced was wrapped
            calls = [call for call in mock_wrap.call_args_list 
                    if "TelemetryManager.traced" in str(call)]
            assert len(calls) > 0, "TelemetryManager.traced should be wrapped"
    
    @patch("agentops.instrumentation.providers.mcp_agent.instrumentor.wrap_function_wrapper")
    def test_tracer_config_instrumentation(self, mock_wrap, instrumentor, setup_tracing):
        """Test that TracingConfig is properly instrumented."""
        # Mock the mcp_agent module
        with patch.dict("sys.modules", {"mcp_agent.tracing.tracer": MagicMock()}):
            # Instrument
            instrumentor.instrument()
            
            # Verify TracingConfig.configure was wrapped
            calls = [call for call in mock_wrap.call_args_list 
                    if "TracingConfig.configure" in str(call)]
            assert len(calls) > 0, "TracingConfig.configure should be wrapped"
    
    def test_tool_call_wrapper(self, instrumentor, setup_tracing):
        """Test tool call wrapper functionality."""
        from agentops.instrumentation.providers.mcp_agent.wrappers import handle_tool_call_attributes
        
        tracer = trace.get_tracer("test")
        config = Config(capture_tool_calls=True, capture_prompts=True, capture_completions=True)
        
        # Create wrapper
        wrapper = handle_tool_call_attributes(tracer, None, config)
        
        # Mock function to wrap
        async def mock_tool_call(tool_name, arguments):
            return {"result": "success"}
        
        # Wrap the function
        wrapped = wrapper(mock_tool_call, None, ["test_tool", {"arg": "value"}], {})
        
        # Execute and verify
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(wrapped)
        
        assert result == {"result": "success"}
        
        # Check spans were created
        spans = setup_tracing.get_finished_spans()
        assert len(spans) > 0
        assert any("tool_call" in span.name for span in spans)
    
    def test_workflow_wrapper(self, instrumentor, setup_tracing):
        """Test workflow wrapper functionality."""
        from agentops.instrumentation.providers.mcp_agent.wrappers import handle_workflow_attributes
        
        tracer = trace.get_tracer("test")
        config = Config(capture_workflows=True, capture_prompts=True, capture_completions=True)
        
        # Create wrapper
        wrapper = handle_workflow_attributes(tracer, None, config)
        
        # Mock workflow class
        class MockWorkflow:
            async def run(self, input_data):
                return {"workflow_result": input_data}
        
        workflow = MockWorkflow()
        
        # Wrap the method
        wrapped = wrapper(workflow.run, workflow, ["test_input"], {})
        
        # Execute and verify
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(wrapped)
        
        assert result == {"workflow_result": "test_input"}
        
        # Check spans were created
        spans = setup_tracing.get_finished_spans()
        assert len(spans) > 0
        assert any("workflow" in span.name for span in spans)
    
    def test_agent_execution_wrapper(self, instrumentor, setup_tracing):
        """Test agent execution wrapper functionality."""
        from agentops.instrumentation.providers.mcp_agent.wrappers import handle_agent_execution_attributes
        
        tracer = trace.get_tracer("test")
        config = Config(
            capture_prompts=True,
            capture_completions=True,
            max_prompt_length=100,
            max_completion_length=100,
        )
        
        # Create wrapper
        wrapper = handle_agent_execution_attributes(tracer, None, config)
        
        # Mock agent class
        class MockAgent:
            name = "TestAgent"
            
            async def execute(self, prompt):
                return f"Response to: {prompt}"
        
        agent = MockAgent()
        
        # Wrap the method
        wrapped = wrapper(agent.execute, agent, ["Test prompt"], {})
        
        # Execute and verify
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(wrapped)
        
        assert result == "Response to: Test prompt"
        
        # Check spans were created
        spans = setup_tracing.get_finished_spans()
        assert len(spans) > 0
        assert any("agent_execution" in span.name for span in spans)
        
        # Check attributes
        for span in spans:
            if "agent_execution" in span.name:
                attrs = span.attributes
                assert attrs.get("agent.name") == "TestAgent"
                assert "gen_ai.prompt" in attrs
    
    def test_config_filtering(self):
        """Test configuration filtering for tools and workflows."""
        config = Config(
            capture_tool_calls=True,
            capture_workflows=True,
            excluded_tools=["excluded_tool"],
            excluded_workflows=["ExcludedWorkflow"],
        )
        
        # Test tool filtering
        assert config.should_capture_tool("allowed_tool") is True
        assert config.should_capture_tool("excluded_tool") is False
        
        # Test workflow filtering
        assert config.should_capture_workflow("AllowedWorkflow") is True
        assert config.should_capture_workflow("ExcludedWorkflow") is False
    
    def test_config_truncation(self):
        """Test configuration truncation for prompts and completions."""
        config = Config(
            max_prompt_length=10,
            max_completion_length=10,
        )
        
        # Test prompt truncation
        long_prompt = "This is a very long prompt that should be truncated"
        truncated = config.truncate_prompt(long_prompt)
        assert truncated == "This is a ... [truncated]"
        
        # Test completion truncation
        long_completion = "This is a very long completion that should be truncated"
        truncated = config.truncate_completion(long_completion)
        assert truncated == "This is a ... [truncated]"
    
    def test_uninstrument(self, instrumentor):
        """Test that uninstrumentation works correctly."""
        with patch("agentops.instrumentation.providers.mcp_agent.instrumentor.wrap_function_wrapper"):
            # Instrument first
            instrumentor.instrument()
            
            # Then uninstrument
            instrumentor.uninstrument()
            
            # Verify state is cleaned up
            assert instrumentor._original_telemetry_manager is None
            assert instrumentor._original_tracer_config is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])