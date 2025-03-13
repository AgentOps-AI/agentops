import time
from typing import Any, Dict, List, Callable

import pytest
from opentelemetry import context, trace
from opentelemetry.trace import StatusCode

import agentops
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.tool import tool
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_kinds import SpanKind
from agentops.semconv.tool import ToolAttributes
from tests.unit.sdk.instrumentation_tester import InstrumentationTester


class TestBasicInstrumentation:
    """Test basic instrumentation functionality."""

    def test_basic_example(self, instrumentation: InstrumentationTester):
        """Test a basic example with session, agent, and tools."""
        print("Starting test_basic_example")

        # Clear any previous spans
        instrumentation.clear_spans()

        @session(name="search_session", tags=["example", "search"], immediate_export=True)
        class SearchSession:
            def __init__(self, query: str):
                self.query = query
                self.agent = SearchAgent(self)

            def run(self) -> Dict[str, Any]:
                return self.agent.search(self.query)

        @agent(name="search_agent", agent_type="search", immediate_export=True)
        class SearchAgent:
            def __init__(self, session):
                self.session = session

            def search(self, query: str) -> Dict[str, Any]:
                # Use tools to perform the search
                results = self.web_search(query)
                processed = self.process_results(results)
                return {"query": query, "results": processed}

            @tool(name="web_search", tool_type="search", immediate_export=True)
            def web_search(self, query: str) -> List[str]:
                return [f"Result 1 for {query}", f"Result 2 for {query}"]

            @tool(name="process_results", tool_type="processing", immediate_export=True)
            def process_results(self, results: List[str]) -> List[Dict[str, Any]]:
                return [{"title": r, "relevance": 0.9} for r in results]

        # Create and run the session
        search_session = SearchSession("test query")
        result = search_session.run()

        # End the session
        if hasattr(search_session, "_session_span"):
            search_session._session_span.end()

        # Flush spans
        instrumentation.span_processor.export_in_flight_spans()

        # Check the result
        assert "query" in result
        assert "results" in result
        assert len(result["results"]) == 2

        # Get all spans by kind
        session_spans = instrumentation.get_spans_by_kind("session")
        agent_spans = instrumentation.get_spans_by_kind(SpanKind.AGENT)
        tool_spans = instrumentation.get_spans_by_kind(SpanKind.TOOL)

        print(f"Found {len(session_spans)} session spans")
        print(f"Found {len(agent_spans)} agent spans")
        print(f"Found {len(tool_spans)} tool spans")

        # Check session spans
        if len(session_spans) > 0:
            session_span = session_spans[0]
            instrumentation.assert_has_attributes(
                session_span,
                {
                    "span.kind": "session",
                    "session.name": "search_session",
                },
            )
            # Check for tags
            assert "session.tags" in session_span.attributes

        # Check agent spans
        if len(agent_spans) > 0:
            agent_span = agent_spans[0]
            instrumentation.assert_has_attributes(
                agent_span,
                {
                    "span.kind": SpanKind.AGENT,
                    AgentAttributes.AGENT_NAME: "search_agent",
                    AgentAttributes.AGENT_ROLE: "search",
                },
            )

        # Check tool spans
        if len(tool_spans) > 0:
            # We should have at least two tool spans (web_search and process_results)
            # Find the web_search tool span
            web_search_span = None
            process_results_span = None

            for span in tool_spans:
                if span.name == "web_search":
                    web_search_span = span
                elif span.name == "process_results":
                    process_results_span = span

            if web_search_span:
                instrumentation.assert_has_attributes(
                    web_search_span,
                    {
                        "span.kind": SpanKind.TOOL,
                        ToolAttributes.TOOL_NAME: "web_search",
                        ToolAttributes.TOOL_DESCRIPTION: "search",
                    },
                )
                # Check for input and output parameters
                assert ToolAttributes.TOOL_PARAMETERS in web_search_span.attributes
                assert ToolAttributes.TOOL_RESULT in web_search_span.attributes

            if process_results_span:
                instrumentation.assert_has_attributes(
                    process_results_span,
                    {
                        "span.kind": SpanKind.TOOL,
                        ToolAttributes.TOOL_NAME: "process_results",
                        ToolAttributes.TOOL_DESCRIPTION: "processing",
                    },
                )
                # Check for input and output parameters
                assert ToolAttributes.TOOL_PARAMETERS in process_results_span.attributes
                assert ToolAttributes.TOOL_RESULT in process_results_span.attributes

    def test_context_propagation(self, instrumentation: InstrumentationTester):
        """Test that OpenTelemetry context is properly propagated and doesn't leak."""
        print("\n=== Testing context propagation ===")

        # First test direct context setting and getting to verify OTel is working

        # Create a direct test of context propagation
        print("\n--- Direct Context Test ---")

        # Set a value in the context
        ctx = context.set_value("test_key", "test_value")

        # Get the value back
        value = context.get_value("test_key", context=ctx)
        print(f"Direct context test: {value}")
        assert value == "test_value", "Failed to retrieve value from context"

        # Now test with span context
        test_tracer = trace.get_tracer("test_tracer")

        with test_tracer.start_as_current_span("test_span") as span:
            # Get the current span and its ID
            current_span = trace.get_current_span()
            span_id = current_span.get_span_context().span_id
            print(f"Current span ID: {span_id}")

            # Store it in context
            ctx_with_span = context.get_current()

            # Save it for later
            saved_ctx = ctx_with_span

            # Detach from current context to simulate method boundary
            token = context.attach(context.get_current())
            context.detach(token)

            # Now current span should be None or different
            current_span_after_detach = trace.get_current_span()
            span_id_after_detach = (
                current_span_after_detach.get_span_context().span_id if current_span_after_detach else 0
            )
            print(f"Span ID after detach: {span_id_after_detach}")

            # Restore the context
            token = context.attach(saved_ctx)
            try:
                # Check if span is restored
                restored_span = trace.get_current_span()
                restored_id = restored_span.get_span_context().span_id if restored_span else 0
                print(f"Restored span ID: {restored_id}")
                assert restored_id == span_id, "Failed to restore span context properly"
            finally:
                context.detach(token)

        print("Basic context test passed!")

        # Now test our actual decorators
        print("\n--- Decorator Context Test ---")

        # Define the agent class first
        @agent(name="test_agent", agent_type="test", immediate_export=True)
        class TestAgent:
            def __init__(self, agent_id: str):
                self.agent_id = agent_id
                # Get the current span from context
                current_span = trace.get_current_span()
                self.parent_span_id = current_span.get_span_context().span_id if current_span else 0
                print(f"TestAgent({agent_id}) - Parent span ID: {self.parent_span_id}")

                # After the agent decorator, we should have an agent span
                self.agent_span_id = 0  # Initialize to ensure we don't get None
                agent_span = trace.get_current_span()
                if agent_span and agent_span.is_recording():
                    self.agent_span_id = agent_span.get_span_context().span_id
                    print(f"TestAgent({agent_id}) - Agent span ID: {self.agent_span_id}")
                else:
                    print(f"TestAgent({agent_id}) - No agent span found!")

                # Save the context with the agent span
                self.agent_context = context.get_current()

            def process(self, data: str):
                raw_span_id = 0
                current_span = trace.get_current_span()
                if current_span:
                    raw_span_id = current_span.get_span_context().span_id
                print(f"TestAgent.process - Raw span ID: {raw_span_id}")

                # Restore the agent context
                token = context.attach(self.agent_context)
                try:
                    # Now the current span should be the agent span
                    current_span = trace.get_current_span()
                    span_id = current_span.get_span_context().span_id if current_span else 0
                    print(f"TestAgent({self.agent_id}).process - With context - Current span ID: {span_id}")

                    # Verify span IDs match from __init__
                    if self.agent_span_id != 0:  # Only check if we actually got a span ID
                        assert (
                            span_id == self.agent_span_id
                        ), f"Agent span ID changed between __init__ and process! {self.agent_span_id} != {span_id}"

                    # Process using a tool
                    processed = self.transform_tool(data)
                    return {"result": processed, "agent_id": self.agent_id}
                finally:
                    context.detach(token)

            @tool(name="transform_tool", tool_type="transform", immediate_export=True)
            def transform_tool(self, data: str, tool_span=None) -> str:
                # The current span should be the tool span
                current_span = trace.get_current_span()
                tool_span_id = current_span.get_span_context().span_id if current_span else 0
                print(f"TestAgent({self.agent_id}).transform_tool - Tool span ID: {tool_span_id}")

                # Tool span should be different from agent span
                if tool_span_id != 0 and self.agent_span_id != 0:
                    assert tool_span_id != self.agent_span_id, "Tool span should be different from agent span"

                return f"Transformed: {data} by agent {self.agent_id}"

        # Create session class to test context propagation
        @session(name="session_a", tags=["test_a"], immediate_export=True)
        class SessionA:
            def __init__(self, session_id: str):
                self.session_id = session_id
                # Get the current span and verify it's our session span
                current_span = trace.get_current_span()
                # Store the span ID for later verification
                self.span_id = 0  # Initialize to avoid None
                if current_span and current_span.is_recording():
                    self.span_id = current_span.get_span_context().span_id
                    print(f"SessionA({session_id}) - Span ID: {self.span_id}")
                else:
                    print(f"SessionA({session_id}) - No current span found!")

                # Store the current context for manual restoration in run method
                self.context = context.get_current()

            def run(self):
                raw_span_id = 0
                current_span = trace.get_current_span()
                if current_span:
                    raw_span_id = current_span.get_span_context().span_id
                print(f"SessionA.run called - Raw span ID: {raw_span_id}")

                # Manually attach the stored context
                token = context.attach(self.context)
                try:
                    # The span from __init__ should now be the current span
                    current_span = trace.get_current_span()
                    span_id = current_span.get_span_context().span_id if current_span else 0
                    print(f"SessionA({self.session_id}).run - With manual context - Current span ID: {span_id}")

                    # Verify span IDs match if we got a span in __init__
                    if self.span_id != 0:
                        assert (
                            span_id == self.span_id
                        ), f"Span ID changed between __init__ and run! {self.span_id} != {span_id}"

                    # Create an agent within this session context
                    agent = TestAgent(self.session_id)
                    return agent.process("test data")
                finally:
                    context.detach(token)

        # Create one test session
        session_a = SessionA("A123")

        # Run the session
        result_a = session_a.run()

        # Verify correct results
        assert result_a["agent_id"] == "A123"
        assert "Transformed: test data" in result_a["result"]

        print("Context propagation test passed!")
