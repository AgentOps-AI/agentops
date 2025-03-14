from typing import TYPE_CHECKING

import pytest
from opentelemetry import trace

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
            SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.TASK]

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

    def test_multiple_nesting_levels(self, instrumentation: InstrumentationTester):
            """Test multiple levels of span nesting with different decorator types."""
            
            # Define a helper operation that will be the deepest in the chain
            @operation
            def helper_operation(value):
                return f"Helper: {value}"
            
            # Define a deeply nested agent structure
            @agent
            class NestedAgent:
                def __init__(self):
                    pass
                    
                @operation
                def level1_operation(self, value):
                    # First level of operation nesting
                    return self.level2_operation(value)
                    
                @operation
                def level2_operation(self, value):
                    # Second level of operation nesting
                    return self.level3_operation(value)
                    
                @operation
                def level3_operation(self, value):
                    # Third level of operation nesting that calls a standalone function
                    return helper_operation(value)
                    
            # Create a workflow that uses the agent
            @workflow
            def test_workflow():
                agent = NestedAgent()
                return agent.level1_operation("test_value")
                
            # Create a session that runs the workflow
            @session
            def test_session():
                return test_workflow()
                
            # Run the test
            result = test_session()
            
            # Verify the result
            assert result == "Helper: test_value"
            
            # Get all spans
            spans = instrumentation.get_finished_spans()
            
            # Group spans by kind
            session_spans = [s for s in spans if s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.SESSION]
            workflow_spans = [s for s in spans if s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.WORKFLOW]
            agent_spans = [s for s in spans if s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.AGENT]
            operation_spans = [s for s in spans if s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.TASK]
            
            # Verify we have the correct number of spans for each type
            assert len(session_spans) == 1, "Should have exactly one session span"
            assert len(workflow_spans) == 1, "Should have exactly one workflow span"
            assert len(agent_spans) == 1, "Should have exactly one agent span"
            # One standalone helper operation + three operations in the agent
            assert len(operation_spans) == 4, "Should have four operation spans"
            
            # Identify the spans by name for verification
            session_span = session_spans[0]
            workflow_span = workflow_spans[0]
            agent_span = agent_spans[0]
            
            # Find operation spans by name
            level1_span = next((s for s in operation_spans if s.name == "level1_operation.task"), None)
            level2_span = next((s for s in operation_spans if s.name == "level2_operation.task"), None)
            level3_span = next((s for s in operation_spans if s.name == "level3_operation.task"), None)
            helper_span = next((s for s in operation_spans if s.name == "helper_operation.task"), None)
            
            assert level1_span is not None, "level1_operation span not found"
            assert level2_span is not None, "level2_operation span not found"
            assert level3_span is not None, "level3_operation span not found"
            assert helper_span is not None, "helper_operation span not found"
            
            # Debug: Print spans and their parent IDs
            print("\nVerifying span hierarchy:")
            for span, name in [(session_span, "session"), (workflow_span, "workflow"), 
                              (agent_span, "agent"), (level1_span, "level1"),
                              (level2_span, "level2"), (level3_span, "level3"), 
                              (helper_span, "helper")]:
                parent_id = span.parent.span_id if span.parent else "None"
                span_id = span.context.span_id
                print(f"{name:<8} - ID: {span_id}, Parent ID: {parent_id}")
            
            # Verify the current nesting behavior (will need to change later):
            # session -> workflow -> agent -> (level1, level2, level3)
            # level3 -> helper
            
            # Session is the root
            assert session_span.parent is None
            
            # Workflow is a child of session
            assert workflow_span.parent.span_id == session_span.context.span_id
            
            # Agent is a child of workflow
            assert agent_span.parent.span_id == workflow_span.context.span_id
            
            # All agent operations are direct children of the agent
            for op_span in [level1_span, level2_span, level3_span]:
                assert op_span.parent.span_id == agent_span.context.span_id
            
            # Helper operation is a child of level3 since it's called from level3
            assert helper_span.parent.span_id == level3_span.context.span_id
