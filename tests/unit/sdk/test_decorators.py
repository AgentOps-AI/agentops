from typing import TYPE_CHECKING, cast, AsyncGenerator, Generator
import asyncio

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan

from agentops.sdk.decorators import agent, operation, session, workflow, task
from agentops.semconv import SpanKind
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv import SpanAttributes
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
            if span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'main_operation':
                main_operation = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'nested_operation':
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

    def test_async_operations(self, instrumentation: InstrumentationTester):
        """Test that async operations are properly nested."""

        # Define the test agent with async operations
        @agent
        class AsyncAgent:
            def __init__(self):
                pass

            @operation
            async def nested_async_operation(self, message):
                """Async operation that should appear as a child of the main operation"""
                await asyncio.sleep(0.01)  # Small delay to simulate async work
                return f"Processed async: {message}"

            @operation
            async def main_async_operation(self):
                """Main async operation that calls the nested async operation"""
                result = await self.nested_async_operation("test async")
                return result

        # Test session with the async agent
        @session
        async def test_async_session():
            agent = AsyncAgent()
            return await agent.main_async_operation()

        # Run the async test
        result = asyncio.run(test_async_session())

        # Verify the result
        assert result == "Processed async: test async"

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # Print detailed span information for debugging
        print("\nDetailed span information for async test:")
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
            if span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'main_async_operation':
                main_operation = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'nested_async_operation':
                nested_operation = span
        
        assert main_operation is not None, "main_async_operation span not found"
        assert nested_operation is not None, "nested_async_operation span not found"
        
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

    def test_generator_operations(self, instrumentation: InstrumentationTester):
        """Test that generator operations are properly nested."""

        # Define the test agent with generator operations
        @agent
        class GeneratorAgent:
            def __init__(self):
                pass

            @operation
            def nested_generator(self, count):
                """Generator operation that should appear as a child of the main operation"""
                for i in range(count):
                    yield f"Item {i}"

            @operation
            def main_generator_operation(self, count):
                """Main operation that calls the nested generator"""
                results = []
                for item in self.nested_generator(count):
                    results.append(item)
                return results

        # Test session with the generator agent
        @session
        def test_generator_session():
            agent = GeneratorAgent()
            return agent.main_generator_operation(3)

        # Run the test
        result = test_generator_session()

        # Verify the result
        assert result == ["Item 0", "Item 1", "Item 2"]

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # Print detailed span information for debugging
        print("\nDetailed span information for generator test:")
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
            if span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'main_generator_operation':
                main_operation = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'nested_generator':
                nested_operation = span
        
        assert main_operation is not None, "main_generator_operation span not found"
        assert nested_operation is not None, "nested_generator span not found"
        
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

    def test_async_generator_operations(self, instrumentation: InstrumentationTester):
        """Test that async generator operations are properly nested."""

        # Define the test agent with async generator operations
        @agent
        class AsyncGeneratorAgent:
            def __init__(self):
                pass

            @operation
            async def nested_async_generator(self, count) -> AsyncGenerator[str, None]:
                """Async generator operation that should appear as a child of the main operation"""
                for i in range(count):
                    await asyncio.sleep(0.01)  # Small delay to simulate async work
                    yield f"Async Item {i}"

            @operation
            async def main_async_generator_operation(self, count):
                """Main async operation that calls the nested async generator"""
                results = []
                async for item in self.nested_async_generator(count):
                    results.append(item)
                return results

        # Test session with the async generator agent
        @session
        async def test_async_generator_session():
            agent = AsyncGeneratorAgent()
            return await agent.main_async_generator_operation(3)

        # Run the async test
        result = asyncio.run(test_async_generator_session())

        # Verify the result
        assert result == ["Async Item 0", "Async Item 1", "Async Item 2"]

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # Print detailed span information for debugging
        print("\nDetailed span information for async generator test:")
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
            if span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'main_async_generator_operation':
                main_operation = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'nested_async_generator':
                nested_operation = span
        
        assert main_operation is not None, "main_async_generator_operation span not found"
        assert nested_operation is not None, "nested_async_generator span not found"
        
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

    def test_complex_nesting(self, instrumentation: InstrumentationTester):
        """Test complex nesting with multiple levels of operations."""

        # Define the test agent with complex nesting
        @agent
        class ComplexAgent:
            def __init__(self):
                pass

            @operation
            def level3_operation(self, message):
                """Level 3 operation (deepest)"""
                return f"Level 3: {message}"

            @operation
            def level2_operation(self, message):
                """Level 2 operation that calls level 3"""
                result = self.level3_operation(message)
                return f"Level 2: {result}"

            @operation
            def level1_operation(self, message):
                """Level 1 operation that calls level 2"""
                result = self.level2_operation(message)
                return f"Level 1: {result}"

        # Test session with the complex agent
        @session
        def test_complex_session():
            agent = ComplexAgent()
            return agent.level1_operation("test message")

        # Run the test
        result = test_complex_session()

        # Verify the result
        assert result == "Level 1: Level 2: Level 3: test message"

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # Print detailed span information for debugging
        print("\nDetailed span information for complex nesting test:")
        for i, span in enumerate(spans):
            parent_id = span.parent.span_id if span.parent else "None"
            span_id = span.context.span_id if span.context else "None"
            print(f"Span {i}: name={span.name}, span_id={span_id}, parent_id={parent_id}")

        # We should have 5 spans: session, agent, and three operations
        assert len(spans) == 5

        # Verify span kinds
        session_spans = [s for s in spans if s.attributes and s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.SESSION]
        agent_spans = [s for s in spans if s.attributes and s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.AGENT]
        operation_spans = [s for s in spans if s.attributes and s.attributes.get(
            SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.TASK]

        assert len(session_spans) == 1
        assert len(agent_spans) == 1
        assert len(operation_spans) == 3

        # Find the operation spans
        level1_operation = None
        level2_operation = None
        level3_operation = None
        
        for span in operation_spans:
            if span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'level1_operation':
                level1_operation = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'level2_operation':
                level2_operation = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'level3_operation':
                level3_operation = span
        
        assert level1_operation is not None, "level1_operation span not found"
        assert level2_operation is not None, "level2_operation span not found"
        assert level3_operation is not None, "level3_operation span not found"
        
        # Verify the session span is the root
        session_span = session_spans[0]
        assert session_span.parent is None
        
        # Verify the agent span is a child of the session span
        agent_span = agent_spans[0]
        assert agent_span.parent is not None
        assert session_span.context is not None
        assert agent_span.parent.span_id == session_span.context.span_id
        
        # Verify level1_operation is a child of the agent span
        assert level1_operation.parent is not None
        assert agent_span.context is not None
        assert level1_operation.parent.span_id == agent_span.context.span_id
        
        # Verify level2_operation is a child of level1_operation
        assert level2_operation.parent is not None
        assert level1_operation.context is not None
        assert level2_operation.parent.span_id == level1_operation.context.span_id
        
        # Verify level3_operation is a child of level2_operation
        assert level3_operation.parent is not None
        assert level2_operation.context is not None
        assert level3_operation.parent.span_id == level2_operation.context.span_id

    def test_workflow_and_task_nesting(self, instrumentation: InstrumentationTester):
        """Test that workflow and task decorators create proper span nesting."""

        # Define a workflow with tasks
        @workflow
        def data_processing_workflow(data):
            """Main workflow that processes data through multiple tasks"""
            result = process_input(data)
            result = transform_data(result)
            return result

        @task
        def process_input(data):
            """Task to process input data"""
            return f"Processed: {data}"

        @task
        def transform_data(data):
            """Task to transform processed data"""
            return f"Transformed: {data}"

        # Test session with the workflow
        @session
        def test_workflow_session():
            return data_processing_workflow("test data")

        # Run the test
        result = test_workflow_session()

        # Verify the result
        assert result == "Transformed: Processed: test data"

        # Get all spans captured during the test
        spans = instrumentation.get_finished_spans()

        # Print detailed span information for debugging
        print("\nDetailed span information for workflow and task test:")
        for i, span in enumerate(spans):
            parent_id = span.parent.span_id if span.parent else "None"
            span_id = span.context.span_id if span.context else "None"
            print(f"Span {i}: name={span.name}, span_id={span_id}, parent_id={parent_id}")

        # We should have 4 spans: session, workflow, and two tasks
        assert len(spans) == 4

        # Verify span kinds
        session_spans = [s for s in spans if s.attributes and s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.SESSION]
        workflow_spans = [s for s in spans if s.attributes and s.attributes.get(SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.WORKFLOW]
        task_spans = [s for s in spans if s.attributes and s.attributes.get(
            SpanAttributes.AGENTOPS_SPAN_KIND) == SpanKind.TASK]

        assert len(session_spans) == 1
        assert len(workflow_spans) == 1
        assert len(task_spans) == 2

        # Find the workflow and task spans
        workflow_span = None
        process_task = None
        transform_task = None
        
        for span in spans:
            if span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'data_processing_workflow':
                workflow_span = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'process_input':
                process_task = span
            elif span.attributes and span.attributes.get(SpanAttributes.OPERATION_NAME) == 'transform_data':
                transform_task = span
        
        assert workflow_span is not None, "workflow span not found"
        assert process_task is not None, "process_input task span not found"
        assert transform_task is not None, "transform_data task span not found"
        
        # Verify the session span is the root
        session_span = session_spans[0]
        assert session_span.parent is None
        
        # Verify the workflow span is a child of the session span
        assert workflow_span.parent is not None
        assert session_span.context is not None
        assert workflow_span.parent.span_id == session_span.context.span_id
        
        # Verify process_task is a child of the workflow span
        assert process_task.parent is not None
        assert workflow_span.context is not None
        assert process_task.parent.span_id == workflow_span.context.span_id
        
        # Verify transform_task is a child of the workflow span
        assert transform_task.parent is not None
        assert workflow_span.context is not None
        assert transform_task.parent.span_id == workflow_span.context.span_id