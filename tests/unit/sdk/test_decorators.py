from typing import TYPE_CHECKING, cast

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan

from agentops.sdk.decorators import agent, operation, session, workflow
from agentops.semconv import SpanKind
from agentops.semconv.span_attributes import SpanAttributes
from tests.unit.sdk.instrumentation_tester import InstrumentationTester


class TestSpanNesting:
    """Tests for proper nesting of spans in the tracing hierarchy."""

    def test_operation_nests_under_agent(self, instrumentation: InstrumentationTester):
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

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # Print detailed span information for debugging
        print("\nDetailed span information:")
        for i, span in enumerate(spans):
            parent_id = span.parent.span_id if span.parent else "None"
            span_id = span.context.span_id if span.context else "None"
            print(f"Span {i}: name={span.name}, span_id={span_id}, parent_id={parent_id}")

        # We should have 4 spans: session, agent, and two operations
        assert len(spans) == 4

        # Verify span kinds
        session_spans = [s for s in spans if s.attributes and s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.SESSION]
        agent_spans = [s for s in spans if s.attributes and s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.AGENT]
        operation_spans = [s for s in spans if s.attributes and s.attributes.get(
            SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.TASK]

        assert len(session_spans) == 1
        assert len(agent_spans) == 1
        assert len(operation_spans) == 2

        # Find the main_operation and nested_operation spans
        main_operation = None
        nested_operation = None
        
        for span in operation_spans:
            if span.attributes and span.attributes.get('agentops.operation.name') == 'main_operation':
                main_operation = span
            elif span.attributes and span.attributes.get('agentops.operation.name') == 'nested_operation':
                nested_operation = span
        
        assert main_operation is not None, "main_operation span not found"
        assert nested_operation is not None, "nested_operation span not found"
        
        # Verify the session span is the root
        session_span = session_spans[0]
        assert session_span.parent is None
        
        # Verify the agent span is a child of the session span
        agent_span = agent_spans[0]
        assert agent_span.parent is not None
        assert session_span.context is not None
        assert agent_span.parent.span_id == session_span.context.span_id
        
        # Verify main_operation is a child of the agent span
        assert main_operation.parent is not None
        assert agent_span.context is not None
        assert main_operation.parent.span_id == agent_span.context.span_id
        
        # Verify nested_operation is a child of main_operation
        assert nested_operation.parent is not None
        assert main_operation.context is not None
        assert nested_operation.parent.span_id == main_operation.context.span_id

    
