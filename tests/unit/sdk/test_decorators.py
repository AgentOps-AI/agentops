import pytest
from opentelemetry import trace

from agentops.sdk.decorators.agentops import agent, operation, session
from agentops.semconv import SpanKind


class TestSpanNesting:
    """Tests for proper nesting of spans in the tracing hierarchy."""

    def test_operation_nests_under_agent(self, instrumentation):
        """Test that operation spans are properly nested under their agent spans."""
        
        # Define the test agent with nested operations
        @agent
        class NestedAgent:
            def __init__(self):
                pass  # No logic needed
            
            @operation
            def nested_operation(self, message):
                """Nested operation that should appear as a child of the agent"""
                return f"Processed: {message}"
            
            @operation
            def main_operation(self):
                """Main operation that calls the nested operation"""
                # Call the nested operation
                result = self.nested_operation("test message")
                return result
        
        # Test session with the agent
        @session
        def test_session():
            agent = NestedAgent()
            return agent.main_operation()
        
        # Run the test with our instrumentor
        result = test_session()
        
        # Verify the result
        assert result == "Processed: test message"
        
        # Get all spans from the instrumentation
        spans = instrumentation.get_finished_spans()
        
        # Verify we have the expected number of spans (1 session + 1 agent + 2 operations)
        assert len(spans) == 4
        
        # Find the spans by their names
        session_span = None
        agent_span = None
        main_op_span = None
        nested_op_span = None
        
        for span in spans:
            if span.name.endswith(f".{SpanKind.SESSION}"):
                session_span = span
            elif span.name.endswith(f".{SpanKind.AGENT}"):
                agent_span = span
            elif span.name == "main_operation.operation":
                main_op_span = span
            elif span.name == "nested_operation.operation":
                nested_op_span = span
        
        # Verify all spans were found
        assert session_span is not None, "Session span not found"
        assert agent_span is not None, "Agent span not found"
        assert main_op_span is not None, "Main operation span not found"
        assert nested_op_span is not None, "Nested operation span not found"
        
        # Verify the hierarchy:
        # 1. Session span is the root
        # 2. Agent span is a child of the session span
        # 3. Main operation span is a child of the agent span
        # 4. Nested operation span is a child of the agent span
        
        # Check parent-child relationships using span's context
        # ReadableSpan doesn't have parent_span_id attribute directly, 
        # use parent_span_id from span context or attributes
        assert session_span.parent is None, "Session span should not have a parent"
        
        # Agent should be a child of session
        assert agent_span.parent is not None
        assert agent_span.parent.span_id == session_span.context.span_id
        
        # Main operation should be a child of agent
        assert main_op_span.parent is not None
        assert main_op_span.parent.span_id == agent_span.context.span_id
        
        # Nested operation should be a child of its immediate caller (main operation)
        assert nested_op_span.parent is not None
        assert nested_op_span.parent.span_id == main_op_span.context.span_id
        
        # All spans should have the same trace ID
        trace_id = session_span.context.trace_id
        assert agent_span.context.trace_id == trace_id
        assert main_op_span.context.trace_id == trace_id
        assert nested_op_span.context.trace_id == trace_id
        
        # Check proper span nesting timing (a parent's time range should contain its children)
        assert session_span.start_time <= agent_span.start_time
        assert agent_span.end_time <= session_span.end_time
        
        assert agent_span.start_time <= main_op_span.start_time
        assert main_op_span.end_time <= agent_span.end_time
        
        assert main_op_span.start_time <= nested_op_span.start_time
        assert nested_op_span.end_time <= main_op_span.end_time
        
        # Verify span attributes for proper classification
        assert session_span.attributes.get("agentops.span.kind") == SpanKind.SESSION
        assert agent_span.attributes.get("agentops.span.kind") == SpanKind.AGENT
        assert main_op_span.attributes.get("agentops.span.kind") == SpanKind.OPERATION
        assert nested_op_span.attributes.get("agentops.span.kind") == SpanKind.OPERATION


    def test_nested_operations_maintain_proper_hierarchy(self, instrumentation):
        """Test that deeply nested operations maintain the correct parent-child hierarchy."""
        
        @agent
        class DeepNestedAgent:
            def __init__(self):
                pass
            
            @operation
            def level3_operation(self, message):
                """Deepest level operation (level 3)"""
                return f"L3: {message}"
            
            @operation
            def level2_operation(self, message):
                """Level 2 operation that calls level 3"""
                result = self.level3_operation(f"{message} → L3")
                return f"L2: {result}"
            
            @operation
            def level1_operation(self, message):
                """Level 1 operation that calls level 2"""
                result = self.level2_operation(f"{message} → L2")
                return f"L1: {result}"
            
            @operation
            def root_operation(self):
                """Root operation that starts the chain"""
                result = self.level1_operation("start")
                return result
        
        # Run the test
        @session
        def deep_test_session():
            agent = DeepNestedAgent()
            return agent.root_operation()
        
        result = deep_test_session()
        
        # Verify result
        assert result == "L1: L2: L3: start → L2 → L3"
        
        # Get spans
        spans = instrumentation.get_finished_spans()
        
        # Expect 6 spans (session + agent + 4 operations)
        assert len(spans) == 6
        
        # Extract spans by name
        spans_by_name = {}
        
        # We need to find the spans more carefully since they might have different formats
        session_span = None
        agent_span = None
        root_op_span = None
        l1_op_span = None
        l2_op_span = None
        l3_op_span = None
        
        for span in spans:
            if span.attributes.get("agentops.span.kind") == SpanKind.SESSION:
                session_span = span
            elif span.attributes.get("agentops.span.kind") == SpanKind.AGENT:
                agent_span = span
            elif span.name == "root_operation.operation":
                root_op_span = span
            elif span.name == "level1_operation.operation":
                l1_op_span = span
            elif span.name == "level2_operation.operation":
                l2_op_span = span
            elif span.name == "level3_operation.operation":
                l3_op_span = span

        assert session_span is not None, "Session span not found"
        assert agent_span is not None, "Agent span not found"
        assert root_op_span is not None, "Root operation span not found"
        assert l1_op_span is not None, "Level 1 operation span not found"
        assert l2_op_span is not None, "Level 2 operation span not found"
        assert l3_op_span is not None, "Level 3 operation span not found"
        
        # Check the chain of parents
        assert session_span.parent is None
        assert agent_span.parent is not None
        assert agent_span.parent.span_id == session_span.context.span_id
        assert root_op_span.parent is not None
        assert root_op_span.parent.span_id == agent_span.context.span_id
        assert l1_op_span.parent is not None
        assert l1_op_span.parent.span_id == root_op_span.context.span_id
        assert l2_op_span.parent is not None
        assert l2_op_span.parent.span_id == l1_op_span.context.span_id
        assert l3_op_span.parent is not None
        assert l3_op_span.parent.span_id == l2_op_span.context.span_id
        
        # Same trace ID for all spans
        trace_id = session_span.context.trace_id
        all_spans = [session_span, agent_span, root_op_span, l1_op_span, l2_op_span, l3_op_span]
        for span in all_spans:
            assert span.context.trace_id == trace_id
