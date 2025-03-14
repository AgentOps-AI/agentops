from typing import TYPE_CHECKING

import pytest
from opentelemetry import trace

from agentops.sdk.decorators import agent, operation, session
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

        instrumentation.get_finished_spans()

        # Verify the result
        assert result == "Processed: test message"

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # We should have 3 spans: session, agent, and two operations
        assert len(spans) == 4

        # Verify span kinds
        session_spans = [s for s in spans if s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.SESSION]
        agent_spans = [s for s in spans if s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.AGENT]
        operation_spans = [s for s in spans if s.attributes.get(
            SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.OPERATION]

        assert len(session_spans) == 1
        assert len(agent_spans) == 1
        assert len(operation_spans) == 2

        # Verify span hierarchy by checking parent-child relationships
        # The session span should be the root
        session_span = session_spans[0]
        assert session_span.parent is None

        # The agent span should be a child of the session span
        agent_span = agent_spans[0]
        assert agent_span.parent.span_id == session_span.context.span_id

        # The operation spans should be children of the agent span
        for op_span in operation_spans:
            assert op_span.parent.span_id == agent_span.context.span_id
