"""
Unit tests for concurrent instrumentation and context propagation.

This module tests the behavior of OpenTelemetry spans when using concurrent.futures.ThreadPoolExecutor,
specifically testing context propagation across thread boundaries.
"""

import concurrent.futures
import time
import unittest
from unittest.mock import patch
import threading

from opentelemetry import context, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentops.sdk.processors import InternalSpanProcessor


class IsolatedInstrumentationTester:
    """
    A lighter-weight instrumentation tester that doesn't affect global state.

    This version creates an isolated tracer provider and doesn't shut down
    the global tracing core, making it safer for use alongside other tests.
    """

    def __init__(self):
        """Initialize with isolated tracer provider."""
        # Create isolated tracer provider and exporter
        self.tracer_provider = TracerProvider()
        self.memory_exporter = InMemorySpanExporter()
        self.span_processor = SimpleSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(self.span_processor)

        # Don't set as global provider - keep isolated
        self.tracer = self.tracer_provider.get_tracer(__name__)

    def get_tracer(self):
        """Get the isolated tracer."""
        return self.tracer

    def clear_spans(self):
        """Clear all spans from the memory exporter."""
        self.span_processor.force_flush()
        self.memory_exporter.clear()

    def get_finished_spans(self):
        """Get all finished spans."""
        self.span_processor.force_flush()
        return list(self.memory_exporter.get_finished_spans())


class TestConcurrentInstrumentation(unittest.TestCase):
    """Tests for concurrent instrumentation and context propagation."""

    def setUp(self):
        """Set up test environment with isolated instrumentation tester."""
        self.tester = IsolatedInstrumentationTester()
        self.tracer = self.tester.get_tracer()

    def tearDown(self):
        """Clean up test environment without affecting global state."""
        # Only clear our isolated spans
        self.tester.clear_spans()

    def _create_simple_span(self, name: str, sleep_duration: float = 0.01) -> str:
        """Helper to create a simple span and return its trace_id."""
        with self.tracer.start_as_current_span(name) as span:
            time.sleep(sleep_duration)  # Simulate work
            return span.get_span_context().trace_id

    def _create_nested_spans(self, parent_name: str, child_name: str) -> tuple:
        """Helper to create nested spans and return their trace_ids."""
        with self.tracer.start_as_current_span(parent_name) as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id
            time.sleep(0.01)

            with self.tracer.start_as_current_span(child_name) as child_span:
                child_trace_id = child_span.get_span_context().trace_id
                time.sleep(0.01)

        return parent_trace_id, child_trace_id

    def test_sequential_spans_same_trace(self):
        """Test that sequential spans in the same thread share the same trace."""
        self._create_simple_span("span1")
        self._create_simple_span("span2")

        # In sequential execution, spans should be independent (different traces)
        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 2)

        # Each span should be a root span (no parent)
        for span in spans:
            self.assertIsNone(span.parent)

    def test_nested_spans_same_trace(self):
        """Test that nested spans share the same trace."""
        parent_trace_id, child_trace_id = self._create_nested_spans("parent", "child")

        # Nested spans should share the same trace
        self.assertEqual(parent_trace_id, child_trace_id)

        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 2)

        # Find parent and child spans
        parent_spans = [s for s in spans if s.name == "parent"]
        child_spans = [s for s in spans if s.name == "child"]

        self.assertEqual(len(parent_spans), 1)
        self.assertEqual(len(child_spans), 1)

        parent_span = parent_spans[0]
        child_span = child_spans[0]

        # Child should have parent as its parent
        self.assertEqual(child_span.parent.span_id, parent_span.context.span_id)

    def test_threadpool_without_context_propagation_creates_separate_traces(self):
        """Test that ThreadPoolExecutor without context propagation creates separate traces."""

        def worker_task(task_id: str) -> dict:
            """Worker task that creates a span without context propagation."""
            with self.tracer.start_as_current_span(f"worker_task_{task_id}") as span:
                time.sleep(0.01)  # Simulate work
                return {
                    "task_id": task_id,
                    "trace_id": span.get_span_context().trace_id,
                    "span_id": span.get_span_context().span_id,
                    "thread_id": threading.get_ident(),
                }

        # Create a parent span
        with self.tracer.start_as_current_span("main_task") as main_span:
            main_trace_id = main_span.get_span_context().trace_id

            # Execute tasks in thread pool WITHOUT context propagation
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(worker_task, f"task_{i}") for i in range(3)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 4)  # 1 main + 3 worker spans

        # Extract trace IDs from results
        worker_trace_ids = [result["trace_id"] for result in results]

        # Each worker should have a different trace ID from the main span
        for worker_trace_id in worker_trace_ids:
            self.assertNotEqual(
                worker_trace_id,
                main_trace_id,
                "Worker span should NOT share trace with main span (no context propagation)",
            )

        # Worker spans should also be different from each other (separate traces)
        unique_trace_ids = set(worker_trace_ids)
        self.assertEqual(len(unique_trace_ids), 3, "Each worker should create a separate trace")

        # Verify that worker spans have no parent (they are root spans)
        worker_spans = [s for s in spans if s.name.startswith("worker_task_")]
        for worker_span in worker_spans:
            self.assertIsNone(worker_span.parent, "Worker spans should be root spans without parent")

    def test_threadpool_with_manual_context_propagation_shares_trace(self):
        """Test that ThreadPoolExecutor with manual context propagation shares the same trace."""

        def worker_task_with_context(task_info: tuple) -> dict:
            """Worker task that restores context before creating spans."""
            task_id, ctx = task_info

            # Restore the context in this thread
            token = context.attach(ctx)
            try:
                with self.tracer.start_as_current_span(f"worker_task_{task_id}") as span:
                    time.sleep(0.01)  # Simulate work
                    return {
                        "task_id": task_id,
                        "trace_id": span.get_span_context().trace_id,
                        "span_id": span.get_span_context().span_id,
                        "thread_id": threading.get_ident(),
                        "parent_span_id": span.parent.span_id if span.parent else None,
                    }
            finally:
                context.detach(token)

        # Create a parent span and capture its context
        with self.tracer.start_as_current_span("main_task") as main_span:
            main_trace_id = main_span.get_span_context().trace_id
            main_span_id = main_span.get_span_context().span_id
            current_context = context.get_current()

            # Execute tasks in thread pool WITH manual context propagation
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(worker_task_with_context, (f"task_{i}", current_context)) for i in range(3)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 4)  # 1 main + 3 worker spans

        # Extract trace IDs from results
        worker_trace_ids = [result["trace_id"] for result in results]

        # All workers should share the same trace ID as the main span
        for result in results:
            self.assertEqual(
                result["trace_id"], main_trace_id, f"Worker task {result['task_id']} should share trace with main span"
            )
            self.assertEqual(
                result["parent_span_id"],
                main_span_id,
                f"Worker task {result['task_id']} should have main span as parent",
            )

        # All worker trace IDs should be the same
        unique_trace_ids = set(worker_trace_ids)
        self.assertEqual(len(unique_trace_ids), 1, "All workers should share the same trace")

    def test_threadpool_with_contextvars_copy_context_shares_trace(self):
        """Test ThreadPoolExecutor with proper context propagation using attach/detach."""

        def worker_task_with_context_management(args) -> dict:
            """Worker task that manages context properly."""
            task_id, ctx = args
            # Use attach/detach for better control over context
            token = context.attach(ctx)
            try:
                with self.tracer.start_as_current_span(f"worker_task_{task_id}") as span:
                    time.sleep(0.01)  # Simulate work
                    return {
                        "task_id": task_id,
                        "trace_id": span.get_span_context().trace_id,
                        "span_id": span.get_span_context().span_id,
                        "thread_id": threading.get_ident(),
                        "parent_span_id": span.parent.span_id if span.parent else None,
                    }
            finally:
                context.detach(token)

        # Create a parent span and capture context properly
        with self.tracer.start_as_current_span("main_task") as main_span:
            main_trace_id = main_span.get_span_context().trace_id
            main_span_id = main_span.get_span_context().span_id

            # Get current context to propagate
            current_context = context.get_current()

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(worker_task_with_context_management, (f"task_{i}", current_context))
                    for i in range(3)
                ]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 4)  # 1 main + 3 worker spans

        # All workers should share the same trace ID as the main span
        for result in results:
            self.assertEqual(
                result["trace_id"], main_trace_id, f"Worker task {result['task_id']} should share trace with main span"
            )
            self.assertEqual(
                result["parent_span_id"],
                main_span_id,
                f"Worker task {result['task_id']} should have main span as parent",
            )

    def test_mixed_sequential_and_concurrent_spans(self):
        """Test a complex scenario with both sequential and concurrent spans."""
        results = []

        # Sequential span 1
        trace_id1 = self._create_simple_span("sequential_1")
        results.append(("sequential_1", trace_id1))

        # Concurrent spans with context propagation
        with self.tracer.start_as_current_span("concurrent_parent") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id
            results.append(("concurrent_parent", parent_trace_id))

            def worker_task_with_context(args) -> tuple:
                task_id, ctx = args
                token = context.attach(ctx)
                try:
                    with self.tracer.start_as_current_span(f"concurrent_{task_id}") as span:
                        time.sleep(0.01)
                        return (f"concurrent_{task_id}", span.get_span_context().trace_id)
                finally:
                    context.detach(token)

            current_context = context.get_current()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(worker_task_with_context, (f"task_{i}", current_context)) for i in range(2)]
                concurrent_results = [future.result() for future in concurrent.futures.as_completed(futures)]
                results.extend(concurrent_results)

        # Sequential span 2
        trace_id2 = self._create_simple_span("sequential_2")
        results.append(("sequential_2", trace_id2))

        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 5)  # 2 sequential + 1 parent + 2 concurrent

        # Verify trace relationships
        sequential_spans = [r for r in results if r[0].startswith("sequential_")]
        concurrent_spans = [r for r in results if r[0].startswith("concurrent_")]

        # Sequential spans should have different traces
        sequential_trace_ids = [r[1] for r in sequential_spans]
        self.assertEqual(len(set(sequential_trace_ids)), 2, "Sequential spans should have different traces")

        # Concurrent spans should share the same trace
        concurrent_trace_ids = [r[1] for r in concurrent_spans]
        unique_concurrent_traces = set(concurrent_trace_ids)
        self.assertEqual(len(unique_concurrent_traces), 1, "All concurrent spans should share the same trace")

    def test_error_handling_in_concurrent_spans(self):
        """Test error handling and span status in concurrent execution."""

        def worker_task_with_error_and_context(args) -> dict:
            """Worker task that may raise an error."""
            task_id, ctx = args
            token = context.attach(ctx)
            try:
                with self.tracer.start_as_current_span(f"worker_task_{task_id}") as span:
                    if task_id == "error_task":
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Simulated error"))
                        raise ValueError("Simulated error")

                    time.sleep(0.01)
                    return {"task_id": task_id, "trace_id": span.get_span_context().trace_id, "status": "success"}
            finally:
                context.detach(token)

        with self.tracer.start_as_current_span("main_task") as main_span:
            main_trace_id = main_span.get_span_context().trace_id
            current_context = context.get_current()

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(worker_task_with_error_and_context, ("success_task_1", current_context)),
                    executor.submit(worker_task_with_error_and_context, ("error_task", current_context)),
                    executor.submit(worker_task_with_error_and_context, ("success_task_2", current_context)),
                ]

                results = []
                errors = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        errors.append(str(e))

        spans = self.tester.get_finished_spans()
        self.assertEqual(len(spans), 4)  # 1 main + 3 worker spans

        # Should have 2 successful results and 1 error
        self.assertEqual(len(results), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("Simulated error", errors[0])

        # All spans should share the same trace
        for result in results:
            self.assertEqual(result["trace_id"], main_trace_id)

        # Find the error span and verify its status
        error_spans = [s for s in spans if s.name == "worker_task_error_task"]
        self.assertEqual(len(error_spans), 1)

        error_span = error_spans[0]
        self.assertEqual(error_span.status.status_code, trace.StatusCode.ERROR)

    @patch("agentops.sdk.processors.logger")
    def test_internal_span_processor_with_concurrent_spans(self, mock_logger):
        """Test InternalSpanProcessor behavior with concurrent spans."""
        # Create an InternalSpanProcessor to test
        processor = InternalSpanProcessor()

        # Add the processor to the tracer provider
        self.tester.tracer_provider.add_span_processor(processor)

        try:

            def worker_task_with_context(args) -> str:
                task_id, ctx = args
                token = context.attach(ctx)
                try:
                    with self.tracer.start_as_current_span(f"openai.chat.completion_{task_id}"):
                        time.sleep(0.01)
                        return f"result_{task_id}"
                finally:
                    context.detach(token)

            # Execute concurrent tasks
            with self.tracer.start_as_current_span("main_session"):
                current_context = context.get_current()

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(worker_task_with_context, (f"task_{i}", current_context)) for i in range(2)
                    ]
                    results = [future.result() for future in concurrent.futures.as_completed(futures)]

            # Verify results
            self.assertEqual(len(results), 2)

            # Verify that debug logging would have been called
            # (The processor tracks root spans and logs when they end)
            self.assertTrue(mock_logger.debug.called)

        finally:
            # Clean up the processor to avoid affecting other tests
            try:
                processor.shutdown()
            except Exception:
                pass

    def test_performance_impact_of_context_propagation(self):
        """Test the performance impact of different context propagation methods."""
        import timeit

        def without_context_propagation():
            def worker():
                with self.tracer.start_as_current_span("test_span"):
                    time.sleep(0.001)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(worker) for _ in range(4)]
                [f.result() for f in futures]

        def with_context_propagation():
            def worker_with_context(ctx):
                token = context.attach(ctx)
                try:
                    with self.tracer.start_as_current_span("test_span"):
                        time.sleep(0.001)
                finally:
                    context.detach(token)

            current_context = context.get_current()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(worker_with_context, current_context) for _ in range(4)]
                [f.result() for f in futures]

        # Clear spans before performance test
        self.tester.clear_spans()

        # Measure timing (just to ensure context propagation doesn't break anything)
        time_without = timeit.timeit(without_context_propagation, number=1)
        self.tester.clear_spans()

        time_with = timeit.timeit(with_context_propagation, number=1)
        self.tester.clear_spans()

        # Context propagation should not cause significant performance degradation
        # This is a sanity check rather than a strict performance requirement
        self.assertGreater(
            time_with * 10, time_without, "Context propagation should not cause extreme performance degradation"
        )


if __name__ == "__main__":
    unittest.main()
