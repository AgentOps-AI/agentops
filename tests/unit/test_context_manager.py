import unittest
from unittest.mock import Mock, patch
import threading
import time
import asyncio

from agentops import start_trace
from agentops.sdk.core import TraceContext
from opentelemetry.trace import StatusCode


class TestContextManager(unittest.TestCase):
    """Test the context manager functionality of TraceContext"""

    def test_trace_context_has_context_manager_methods(self):
        """Test that TraceContext has __enter__ and __exit__ methods"""
        # TraceContext should have context manager protocol methods
        assert hasattr(TraceContext, "__enter__")
        assert hasattr(TraceContext, "__exit__")

    @patch("agentops.sdk.core.tracer")
    def test_trace_context_enter_returns_self(self, mock_tracer):
        """Test that __enter__ returns the TraceContext instance"""
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # __enter__ should return self
        result = trace_context.__enter__()
        assert result is trace_context

    @patch("agentops.sdk.core.tracer")
    def test_trace_context_exit_calls_end_trace(self, mock_tracer):
        """Test that __exit__ calls end_trace with appropriate state"""
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # Test normal exit (no exception)
        trace_context.__exit__(None, None, None)
        mock_tracer.end_trace.assert_called_once_with(trace_context, StatusCode.OK)

    @patch("agentops.sdk.core.tracer")
    def test_trace_context_exit_with_exception_sets_error_state(self, mock_tracer):
        """Test that __exit__ sets ERROR state when exception occurs"""
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # Test exit with exception
        mock_tracer.reset_mock()
        exc_type = ValueError
        exc_val = ValueError("test error")
        exc_tb = None

        trace_context.__exit__(exc_type, exc_val, exc_tb)
        mock_tracer.end_trace.assert_called_once_with(trace_context, StatusCode.ERROR)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_usage_pattern(self, mock_agentops_tracer, mock_core_tracer):
        """Test using start_trace as a context manager"""
        # Create a mock TraceContext
        mock_span = Mock()
        mock_token = Mock()
        mock_trace_context = TraceContext(span=mock_span, token=mock_token)

        # Mock the tracer's start_trace method to return our TraceContext
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace_context

        # Use as context manager
        with start_trace("test_trace") as trace:
            assert trace is mock_trace_context
            assert trace.span is mock_span
            assert trace.token is mock_token

        # Verify start_trace was called
        mock_agentops_tracer.start_trace.assert_called_once_with(trace_name="test_trace", tags=None)
        # Verify end_trace was called
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace_context, StatusCode.OK)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_exception(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager handles exceptions properly"""
        # Create a mock TraceContext
        mock_span = Mock()
        mock_token = Mock()
        mock_trace_context = TraceContext(span=mock_span, token=mock_token)

        # Mock the tracer's start_trace method
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace_context

        # Test exception handling
        with self.assertRaises(ValueError):
            with start_trace("test_trace"):
                raise ValueError("Test exception")

        # Verify end_trace was called with ERROR state
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace_context, StatusCode.ERROR)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    @patch("agentops.init")
    def test_start_trace_auto_initializes_if_needed(self, mock_init, mock_agentops_tracer, mock_core_tracer):
        """Test that start_trace attempts to initialize SDK if not initialized"""
        # First call: SDK not initialized
        mock_agentops_tracer.initialized = False

        # After init() is called, set initialized to True
        def set_initialized():
            mock_agentops_tracer.initialized = True

        mock_init.side_effect = set_initialized

        # Create a mock TraceContext for when start_trace is called after init
        mock_span = Mock()
        mock_token = Mock()
        mock_trace_context = TraceContext(span=mock_span, token=mock_token)
        mock_agentops_tracer.start_trace.return_value = mock_trace_context

        # Call start_trace
        result = start_trace("test_trace")

        # Verify init was called
        mock_init.assert_called_once()
        # Verify start_trace was called on tracer
        mock_agentops_tracer.start_trace.assert_called_once_with(trace_name="test_trace", tags=None)
        assert result is mock_trace_context

    def test_no_wrapper_classes_needed(self):
        """Test that we don't need wrapper classes - TraceContext is the context manager"""
        # TraceContext itself implements the context manager protocol
        # No need for TraceContextManager wrapper
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # Can use directly as context manager
        assert hasattr(trace_context, "__enter__")
        assert hasattr(trace_context, "__exit__")
        assert callable(trace_context.__enter__)
        assert callable(trace_context.__exit__)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_parallel_traces_independence(self, mock_agentops_tracer, mock_core_tracer):
        """Test that multiple traces can run in parallel independently"""
        # Create mock TraceContexts
        mock_trace1 = TraceContext(span=Mock(), token=Mock())
        mock_trace2 = TraceContext(span=Mock(), token=Mock())

        # Mock the tracer to return different traces
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = [mock_trace1, mock_trace2]

        # Start two traces
        trace1 = start_trace("trace1")
        trace2 = start_trace("trace2")

        # They should be different instances
        assert trace1 is not trace2
        assert trace1 is mock_trace1
        assert trace2 is mock_trace2

        # End them independently using context manager protocol
        trace1.__exit__(None, None, None)
        trace2.__exit__(None, None, None)

        # Verify both were ended
        assert mock_core_tracer.end_trace.call_count == 2

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_nested_context_managers_create_parallel_traces(self, mock_agentops_tracer, mock_core_tracer):
        """Test that nested context managers create parallel traces, not parent-child"""
        # Create mock TraceContexts
        mock_outer = TraceContext(span=Mock(), token=Mock())
        mock_inner = TraceContext(span=Mock(), token=Mock())

        # Mock the tracer
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = [mock_outer, mock_inner]

        # Use nested context managers
        with start_trace("outer_trace") as outer:
            assert outer is mock_outer
            with start_trace("inner_trace") as inner:
                assert inner is mock_inner
                assert inner is not outer
                # Both traces are active
                assert mock_agentops_tracer.start_trace.call_count == 2

        # Verify both were ended
        assert mock_core_tracer.end_trace.call_count == 2
        # Inner trace ended first, then outer
        calls = mock_core_tracer.end_trace.call_args_list
        assert calls[0][0][0] is mock_inner
        assert calls[1][0][0] is mock_outer

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_exception_in_nested_traces(self, mock_agentops_tracer, mock_core_tracer):
        """Test exception handling in nested traces"""
        # Create mock TraceContexts
        mock_outer = TraceContext(span=Mock(), token=Mock())
        mock_inner = TraceContext(span=Mock(), token=Mock())

        # Mock the tracer
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = [mock_outer, mock_inner]

        # Test exception in inner trace
        with self.assertRaises(ValueError):
            with start_trace("outer_trace"):
                with start_trace("inner_trace"):
                    raise ValueError("Inner exception")

        # Both traces should be ended with ERROR state
        assert mock_core_tracer.end_trace.call_count == 2
        calls = mock_core_tracer.end_trace.call_args_list
        # Inner trace ended with ERROR
        assert calls[0][0][0] is mock_inner
        assert calls[0][0][1] == StatusCode.ERROR
        # Outer trace also ended with ERROR (exception propagated)
        assert calls[1][0][0] is mock_outer
        assert calls[1][0][1] == StatusCode.ERROR

    @patch("agentops.sdk.core.tracer")
    def test_trace_context_attributes_access(self, mock_tracer):
        """Test accessing span and token attributes of TraceContext"""
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # Direct attribute access
        assert trace_context.span is mock_span
        assert trace_context.token is mock_token

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_multiple_exceptions_in_sequence(self, mock_agentops_tracer, mock_core_tracer):
        """Test handling multiple exceptions in sequence"""
        # Mock the tracer
        mock_agentops_tracer.initialized = True

        # Create different mock traces for each attempt
        mock_traces = [TraceContext(span=Mock(), token=Mock()) for _ in range(3)]
        mock_agentops_tracer.start_trace.side_effect = mock_traces

        # Multiple traces with exceptions
        for i in range(3):
            with self.assertRaises(RuntimeError):
                with start_trace(f"trace_{i}"):
                    raise RuntimeError(f"Error {i}")

        # All should be ended with ERROR state
        assert mock_core_tracer.end_trace.call_count == 3
        for i, call in enumerate(mock_core_tracer.end_trace.call_args_list):
            assert call[0][0] is mock_traces[i]
            assert call[0][1] == StatusCode.ERROR

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_trace_with_tags_dict(self, mock_agentops_tracer, mock_core_tracer):
        """Test starting trace with tags as dictionary"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        tags = {"environment": "test", "version": "1.0"}
        with start_trace("tagged_trace", tags=tags) as trace:
            assert trace is mock_trace

        # Verify tags were passed
        mock_agentops_tracer.start_trace.assert_called_once_with(trace_name="tagged_trace", tags=tags)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_trace_with_tags_list(self, mock_agentops_tracer, mock_core_tracer):
        """Test starting trace with tags as list"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        tags = ["test", "v1.0", "experimental"]
        with start_trace("tagged_trace", tags=tags) as trace:
            assert trace is mock_trace

        # Verify tags were passed
        mock_agentops_tracer.start_trace.assert_called_once_with(trace_name="tagged_trace", tags=tags)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_trace_context_manager_thread_safety(self, mock_agentops_tracer, mock_core_tracer):
        """Test that context managers work correctly in multi-threaded environment"""
        # Mock the tracer
        mock_agentops_tracer.initialized = True

        # Create unique traces for each thread
        thread_traces = {}
        trace_lock = threading.Lock()

        def create_trace(trace_name=None, tags=None, **kwargs):
            trace = TraceContext(span=Mock(), token=Mock())
            with trace_lock:
                thread_traces[threading.current_thread().ident] = trace
            return trace

        mock_agentops_tracer.start_trace.side_effect = create_trace

        results = []
        errors = []

        def worker(thread_id):
            try:
                with start_trace(f"thread_{thread_id}_trace") as trace:
                    # Each thread should get its own trace
                    results.append((thread_id, trace))
                    time.sleep(0.01)  # Simulate some work
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check results
        assert len(errors) == 0, f"Errors in threads: {errors}"
        assert len(results) == 5

        # Each thread should have gotten a unique trace
        traces = [r[1] for r in results]
        assert len(set(id(t) for t in traces)) == 5  # All unique

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_early_return(self, mock_agentops_tracer, mock_core_tracer):
        """Test that context manager properly cleans up with early return"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        def function_with_early_return():
            with start_trace("early_return_trace"):
                if True:  # Early return condition
                    return "early"
                return "normal"

        result = function_with_early_return()
        assert result == "early"

        # Verify trace was still ended properly
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace, StatusCode.OK)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_finally_block(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager with try-finally block"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        finally_executed = False

        try:
            with start_trace("finally_trace"):
                try:
                    raise ValueError("Test")
                finally:
                    finally_executed = True
        except ValueError:
            pass

        assert finally_executed
        # Trace should be ended with ERROR due to exception
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace, StatusCode.ERROR)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_backwards_compatibility_existing_patterns(self, mock_agentops_tracer, mock_core_tracer):
        """Test that existing usage patterns continue to work"""
        # Create mock traces
        mock_traces = [TraceContext(span=Mock(), token=Mock()) for _ in range(3)]
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = mock_traces

        # Pattern 1: Basic context manager
        with start_trace("basic") as trace:
            assert trace is mock_traces[0]

        # Pattern 2: Manual start/end using context manager protocol
        trace = start_trace("manual")
        assert trace is mock_traces[1]
        trace.__exit__(None, None, None)  # Use context manager exit instead of end_trace

        # Pattern 3: With tags
        with start_trace("tagged", tags=["production", "v2"]) as trace:
            assert trace is mock_traces[2]

        # All patterns should work
        assert mock_agentops_tracer.start_trace.call_count == 3
        assert mock_core_tracer.end_trace.call_count == 3

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_edge_case_none_trace_context(self, mock_agentops_tracer, mock_core_tracer):
        """Test handling when start_trace returns None"""
        # Mock SDK not initialized and init fails
        mock_agentops_tracer.initialized = False

        # When start_trace is called on uninitialized tracer, it returns None
        with patch("agentops.init") as mock_init:
            mock_init.side_effect = Exception("Init failed")

            result = start_trace("test_trace")
            assert result is None

        # Verify start_trace was not called on tracer (since init failed)
        mock_agentops_tracer.start_trace.assert_not_called()

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_edge_case_tracing_core_not_initialized(self, mock_agentops_tracer, mock_core_tracer):
        """Test behavior when global tracer is not initialized"""
        mock_agentops_tracer.initialized = False

        # Mock init to succeed but tracer still not initialized
        with patch("agentops.init") as mock_init:
            mock_init.return_value = None  # init succeeds but doesn't set initialized

            result = start_trace("test")
            assert result is None

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_edge_case_exception_in_exit_method(self, mock_agentops_tracer, mock_core_tracer):
        """Test handling when exception occurs in __exit__ method"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        # Make end_trace raise an exception
        mock_core_tracer.end_trace.side_effect = RuntimeError("End trace failed")

        # The exception in __exit__ should be suppressed
        with start_trace("exception_in_exit"):
            pass  # Should not raise

        # Verify end_trace was attempted
        mock_core_tracer.end_trace.assert_called_once()

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_performance_many_sequential_traces(self, mock_agentops_tracer, mock_core_tracer):
        """Test performance with many sequential traces"""
        # Mock the tracer
        mock_agentops_tracer.initialized = True

        # Create traces on demand
        def create_trace(trace_name=None, tags=None, **kwargs):
            return TraceContext(span=Mock(), token=Mock())

        mock_agentops_tracer.start_trace.side_effect = create_trace

        # Create many traces sequentially
        start_time = time.time()
        for i in range(100):
            with start_trace(f"trace_{i}") as trace:
                assert trace is not None
                assert trace.span is not None

        elapsed = time.time() - start_time

        # Should complete reasonably quickly (< 1 second for 100 traces)
        assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s for 100 traces"

        # Verify all traces were started and ended
        assert mock_agentops_tracer.start_trace.call_count == 100
        assert mock_core_tracer.end_trace.call_count == 100

    @patch("agentops.sdk.core.tracer")
    def test_trace_context_state_management(self, mock_tracer):
        """Test that TraceContext properly manages its internal state"""
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # Initial state
        assert trace_context.span is mock_span
        assert trace_context.token is mock_token

        # Enter context
        result = trace_context.__enter__()
        assert result is trace_context

        # Exit context normally
        trace_context.__exit__(None, None, None)
        mock_tracer.end_trace.assert_called_once_with(trace_context, StatusCode.OK)

        # State should remain accessible after exit
        assert trace_context.span is mock_span
        assert trace_context.token is mock_token

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_async_context(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager works in async context"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        async def async_function():
            with start_trace("async_context") as trace:
                assert trace is mock_trace
                await asyncio.sleep(0.01)
                return "done"

        # Run async function
        result = asyncio.run(async_function())
        assert result == "done"

        # Verify trace was properly managed
        mock_agentops_tracer.start_trace.assert_called_once_with(trace_name="async_context", tags=None)
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace, StatusCode.OK)


class TestContextManagerBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility for context manager usage"""

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_existing_code_patterns_still_work(self, mock_agentops_tracer, mock_core_tracer):
        """Test that code using the old patterns still works"""
        # Create mock traces - need more than 3 for this test
        mock_traces = [TraceContext(span=Mock(), token=Mock()) for _ in range(5)]
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = mock_traces

        # Old pattern 1: Simple context manager
        with start_trace("basic") as trace:
            # Should work without changes
            assert trace.span is not None

        # Old pattern 2: Context manager with exception handling
        try:
            with start_trace("with_error") as trace:
                raise ValueError("test")
        except ValueError:
            pass

        # Old pattern 3: Nested traces
        with start_trace("outer") as outer:
            with start_trace("inner") as inner:
                assert outer is not inner

        # All should work - 4 calls total (basic, with_error, outer, inner)
        assert mock_agentops_tracer.start_trace.call_count == 4
        assert mock_core_tracer.end_trace.call_count == 4

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_api_compatibility(self, mock_agentops_tracer, mock_core_tracer):
        """Test that the API remains compatible"""
        # Create mock TraceContexts for each call
        mock_traces = [TraceContext(span=Mock(), token=Mock()) for _ in range(3)]
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = mock_traces

        # Test function signatures
        # start_trace(trace_name, tags=None)
        trace1 = start_trace("test1")
        assert trace1 is mock_traces[0]

        trace2 = start_trace("test2", tags=["tag1", "tag2"])
        assert trace2 is mock_traces[1]

        trace3 = start_trace("test3", tags={"key": "value"})
        assert trace3 is mock_traces[2]

        # Use context manager protocol to end traces
        trace1.__exit__(None, None, None)
        trace2.__exit__(ValueError, ValueError("test"), None)
        trace3.__exit__(None, None, None)

        # All calls should work
        assert mock_agentops_tracer.start_trace.call_count == 3
        assert mock_core_tracer.end_trace.call_count == 3

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_return_type_compatibility(self, mock_agentops_tracer, mock_core_tracer):
        """Test that return types are compatible with existing code"""
        mock_span = Mock()
        mock_token = Mock()
        mock_trace = TraceContext(span=mock_span, token=mock_token)
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        # start_trace returns TraceContext (or None)
        trace = start_trace("test")
        assert isinstance(trace, TraceContext)
        assert hasattr(trace, "span")
        assert hasattr(trace, "token")
        assert hasattr(trace, "__enter__")
        assert hasattr(trace, "__exit__")

        # Can be used as context manager
        with trace:
            pass

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_keyboard_interrupt(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager handles KeyboardInterrupt properly"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        # Test KeyboardInterrupt handling
        with self.assertRaises(KeyboardInterrupt):
            with start_trace("keyboard_interrupt_trace"):
                raise KeyboardInterrupt()

        # Verify end_trace was called with ERROR state
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace, StatusCode.ERROR)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_system_exit(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager handles SystemExit properly"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        # Test SystemExit handling
        with self.assertRaises(SystemExit):
            with start_trace("system_exit_trace"):
                raise SystemExit(1)

        # Verify end_trace was called with ERROR state
        mock_core_tracer.end_trace.assert_called_once_with(mock_trace, StatusCode.ERROR)

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_in_generator_function(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager works correctly in generator functions"""
        # Create mock traces
        mock_traces = [TraceContext(span=Mock(), token=Mock()) for _ in range(3)]
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.side_effect = mock_traces

        def trace_generator():
            with start_trace("generator_trace"):
                yield 1
                yield 2
                yield 3

        # Consume the generator
        results = list(trace_generator())
        assert results == [1, 2, 3]

        # Verify trace was properly managed
        mock_agentops_tracer.start_trace.assert_called_once()
        mock_core_tracer.end_trace.assert_called_once()

    @patch("agentops.sdk.core.tracer")
    def test_context_manager_exit_return_value(self, mock_tracer):
        """Test that __exit__ returns None (doesn't suppress exceptions)"""
        mock_span = Mock()
        mock_token = Mock()
        trace_context = TraceContext(span=mock_span, token=mock_token)

        # __exit__ should return None (or falsy) to not suppress exceptions
        result = trace_context.__exit__(None, None, None)
        assert result is None or not result

        # Also with exception
        result = trace_context.__exit__(ValueError, ValueError("test"), None)
        assert result is None or not result

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_very_large_data(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager with very large trace names and tags"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        # Very large trace name and tags
        large_trace_name = "x" * 10000
        large_tags = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        with start_trace(large_trace_name, tags=large_tags) as trace:
            assert trace is mock_trace

        # Should handle large data without issues
        mock_agentops_tracer.start_trace.assert_called_once()
        args, kwargs = mock_agentops_tracer.start_trace.call_args
        assert kwargs["trace_name"] == large_trace_name
        assert kwargs["tags"] == large_tags

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_with_asyncio_tasks(self, mock_agentops_tracer, mock_core_tracer):
        """Test context manager with multiple asyncio tasks"""
        # Mock the tracer
        mock_agentops_tracer.initialized = True

        # Create traces for each task
        trace_count = 0

        def create_trace(trace_name=None, tags=None, **kwargs):
            nonlocal trace_count
            trace_count += 1
            return TraceContext(span=Mock(name=f"span_{trace_count}"), token=Mock())

        mock_agentops_tracer.start_trace.side_effect = create_trace

        async def task_with_trace(task_id):
            with start_trace(f"async_task_{task_id}"):
                await asyncio.sleep(0.01)
                return task_id

        async def run_concurrent_tasks():
            tasks = [task_with_trace(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            return results

        # Run async tasks
        results = asyncio.run(run_concurrent_tasks())
        assert results == [0, 1, 2, 3, 4]

        # All traces should be started and ended
        assert mock_agentops_tracer.start_trace.call_count == 5
        assert mock_core_tracer.end_trace.call_count == 5

    @patch("agentops.sdk.core.tracer")
    @patch("agentops.tracer")
    def test_context_manager_resource_cleanup_on_exit_failure(self, mock_agentops_tracer, mock_core_tracer):
        """Test that resources are cleaned up even if __exit__ fails"""
        # Create a mock TraceContext
        mock_trace = TraceContext(span=Mock(), token=Mock())
        mock_agentops_tracer.initialized = True
        mock_agentops_tracer.start_trace.return_value = mock_trace

        # Make end_trace fail
        mock_core_tracer.end_trace.side_effect = Exception("Cleanup failed")

        # Should not raise exception from __exit__
        with start_trace("cleanup_test") as trace:
            assert trace is mock_trace

        # end_trace was attempted despite failure
        mock_core_tracer.end_trace.assert_called_once()


if __name__ == "__main__":
    unittest.main()
