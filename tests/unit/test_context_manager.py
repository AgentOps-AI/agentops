"""
Comprehensive tests for AgentOps context manager functionality.

This test suite validates the native TraceContext context manager implementation
including edge cases, parallel traces, backwards compatibility, and error scenarios.
"""

import pytest
import threading
import time
import asyncio
from unittest.mock import Mock, patch, call
from agentops.sdk.core import TraceContext
from agentops import start_trace, end_trace


class TestContextManager:
    """Comprehensive test suite for AgentOps context manager functionality."""

    def test_trace_context_has_context_manager_methods(self):
        """Test that TraceContext has native context manager methods."""
        mock_span = Mock()
        mock_span.get_span_context.return_value.span_id = "test_span_id"
        mock_span.get_span_context.return_value.trace_id = 12345

        trace_context = TraceContext(mock_span)

        # Verify it has context manager methods
        assert hasattr(trace_context, "__enter__")
        assert hasattr(trace_context, "__exit__")
        assert callable(trace_context.__enter__)
        assert callable(trace_context.__exit__)

    def test_trace_context_enter_returns_self(self):
        """Test that __enter__ returns the TraceContext instance."""
        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        result = trace_context.__enter__()
        assert result is trace_context

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_trace_context_exit_calls_end_trace(self, mock_get_instance):
        """Test that __exit__ calls end_trace on TracingCore."""
        mock_tracing_core = Mock()
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        # Call __exit__ without exception
        result = trace_context.__exit__(None, None, None)

        # Verify end_trace was called with Success state
        mock_tracing_core.end_trace.assert_called_once_with(trace_context, "Success")
        assert result is False  # Should not suppress exceptions

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_trace_context_exit_with_exception_sets_error_state(self, mock_get_instance):
        """Test that __exit__ sets Error state when exception occurs."""
        mock_tracing_core = Mock()
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        # Call __exit__ with exception
        exc_type = ValueError
        exc_val = ValueError("test error")
        exc_tb = None

        result = trace_context.__exit__(exc_type, exc_val, exc_tb)

        # Verify end_trace was called with Error state
        mock_tracing_core.end_trace.assert_called_once_with(trace_context, "Error")
        assert result is False  # Should not suppress exceptions

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_usage_pattern(self, mock_get_instance):
        """Test the actual context manager usage pattern."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_span.get_span_context.return_value.span_id = "test_span_id"
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_span.name = "test_trace"

        mock_trace_context = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace_context

        # Test the context manager pattern
        with start_trace("test_trace") as trace:
            assert trace is mock_trace_context
            # Do some work
            pass

        # Verify start_trace and end_trace were called
        mock_tracing_core.start_trace.assert_called_once_with(trace_name="test_trace", tags=None)
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace_context, "Success")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_exception(self, mock_get_instance):
        """Test context manager behavior when exception is raised."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace_context = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace_context

        # Test exception handling
        with pytest.raises(ValueError):
            with start_trace("test_trace"):
                raise ValueError("test error")

        # Verify end_trace was called with Error state
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace_context, "Error")

    @patch("agentops.init")
    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_start_trace_auto_initializes_if_needed(self, mock_get_instance, mock_init):
        """Test that start_trace auto-initializes if SDK not initialized."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = False
        mock_get_instance.return_value = mock_tracing_core

        # Mock the init call to set initialized to True
        def side_effect():
            mock_tracing_core.initialized = True

        mock_init.side_effect = side_effect

        mock_span = Mock()
        mock_trace_context = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace_context

        # Call start_trace
        result = start_trace("test_trace")

        # Verify init was called and trace was started
        mock_init.assert_called_once()
        mock_tracing_core.start_trace.assert_called_once_with(trace_name="test_trace", tags=None)
        assert result is mock_trace_context

    def test_no_wrapper_classes_needed(self):
        """Test that we don't need wrapper classes anymore."""
        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        # Should be able to use directly as context manager
        assert hasattr(trace_context, "__enter__")
        assert hasattr(trace_context, "__exit__")

        # Should not need any wrapper
        with trace_context as ctx:
            assert ctx is trace_context

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_parallel_traces_independence(self, mock_get_instance):
        """Test that parallel traces are independent and don't interfere."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        # Create mock spans for different traces
        mock_span1 = Mock()
        mock_span1.get_span_context.return_value.trace_id = 111
        mock_span1.name = "trace1"

        mock_span2 = Mock()
        mock_span2.get_span_context.return_value.trace_id = 222
        mock_span2.name = "trace2"

        mock_trace1 = TraceContext(mock_span1)
        mock_trace2 = TraceContext(mock_span2)

        # Mock start_trace to return different traces
        mock_tracing_core.start_trace.side_effect = [mock_trace1, mock_trace2]

        # Start two parallel traces
        trace1 = start_trace("trace1")
        trace2 = start_trace("trace2")

        assert trace1 is mock_trace1
        assert trace2 is mock_trace2
        assert trace1 is not trace2

        # Verify both traces were started independently
        assert mock_tracing_core.start_trace.call_count == 2
        mock_tracing_core.start_trace.assert_has_calls(
            [call(trace_name="trace1", tags=None), call(trace_name="trace2", tags=None)]
        )

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_nested_context_managers_create_parallel_traces(self, mock_get_instance):
        """Test that nested context managers create parallel traces, not parent-child."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        # Create mock traces
        mock_span1 = Mock()
        mock_span2 = Mock()
        mock_trace1 = TraceContext(mock_span1)
        mock_trace2 = TraceContext(mock_span2)

        mock_tracing_core.start_trace.side_effect = [mock_trace1, mock_trace2]

        # Test nested context managers
        with start_trace("outer_trace") as outer:
            assert outer is mock_trace1

            with start_trace("inner_trace") as inner:
                assert inner is mock_trace2
                assert inner is not outer

        # Verify both traces were started and ended independently
        assert mock_tracing_core.start_trace.call_count == 2
        assert mock_tracing_core.end_trace.call_count == 2

        # Verify the order of end_trace calls (inner first, then outer)
        mock_tracing_core.end_trace.assert_has_calls(
            [
                call(mock_trace2, "Success"),  # inner trace ends first
                call(mock_trace1, "Success"),  # outer trace ends second
            ]
        )

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_exception_in_nested_traces(self, mock_get_instance):
        """Test exception handling in nested traces."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span1 = Mock()
        mock_span2 = Mock()
        mock_trace1 = TraceContext(mock_span1)
        mock_trace2 = TraceContext(mock_span2)

        mock_tracing_core.start_trace.side_effect = [mock_trace1, mock_trace2]

        # Test exception in nested trace
        with pytest.raises(ValueError):
            with start_trace("outer_trace"):
                with start_trace("inner_trace"):
                    raise ValueError("inner error")

        # Verify both traces ended with appropriate states
        mock_tracing_core.end_trace.assert_has_calls(
            [
                call(mock_trace2, "Error"),  # inner trace ends with Error
                call(mock_trace1, "Error"),  # outer trace also ends with Error due to exception propagation
            ]
        )

    def test_trace_context_attributes_access(self):
        """Test that TraceContext attributes are accessible."""
        mock_span = Mock()
        mock_span.name = "test_span"
        mock_span.get_span_context.return_value.trace_id = 12345

        mock_token = Mock()

        trace_context = TraceContext(mock_span, token=mock_token, is_init_trace=True)

        # Test attribute access
        assert trace_context.span is mock_span
        assert trace_context.token is mock_token
        assert trace_context.is_init_trace is True
        assert trace_context._end_state == "Indeterminate"  # Default state before exit

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_multiple_exceptions_in_sequence(self, mock_get_instance):
        """Test handling multiple exceptions in sequence."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_spans = [Mock() for _ in range(3)]
        mock_traces = [TraceContext(span) for span in mock_spans]
        mock_tracing_core.start_trace.side_effect = mock_traces

        # Test multiple traces with exceptions
        for i, exception_type in enumerate([ValueError, TypeError, RuntimeError]):
            with pytest.raises(exception_type):
                with start_trace(f"trace_{i}"):
                    raise exception_type(f"error_{i}")

        # Verify all traces ended with Error state
        assert mock_tracing_core.end_trace.call_count == 3
        for i, mock_trace in enumerate(mock_traces):
            mock_tracing_core.end_trace.assert_any_call(mock_trace, "Error")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_trace_with_tags_dict(self, mock_get_instance):
        """Test trace creation with dictionary tags."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        tags = {"environment": "test", "version": "1.0", "priority": "high"}

        with start_trace("tagged_trace", tags=tags) as trace:
            assert trace is mock_trace

        # Verify tags were passed correctly
        mock_tracing_core.start_trace.assert_called_once_with(trace_name="tagged_trace", tags=tags)

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_trace_with_tags_list(self, mock_get_instance):
        """Test trace creation with list tags."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        tags = ["test", "integration", "high-priority"]

        with start_trace("tagged_trace", tags=tags) as trace:
            assert trace is mock_trace

        # Verify tags were passed correctly
        mock_tracing_core.start_trace.assert_called_once_with(trace_name="tagged_trace", tags=tags)

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_trace_context_manager_thread_safety(self, mock_get_instance):
        """Test that context managers work correctly in multi-threaded environment."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        results = []
        errors = []

        def create_mock_trace(name):
            mock_span = Mock()
            mock_span.name = name
            mock_span.get_span_context.return_value.trace_id = hash(name)
            return TraceContext(mock_span)

        # Create different mock traces for each thread
        mock_traces = [create_mock_trace(f"thread_{i}") for i in range(5)]
        mock_tracing_core.start_trace.side_effect = mock_traces

        def worker(thread_id):
            try:
                with start_trace(f"thread_{thread_id}") as trace:
                    # Simulate some work
                    time.sleep(0.01)
                    results.append((thread_id, trace.span.name))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors in threads: {errors}"

        # Verify all threads completed successfully
        assert len(results) == 5

        # Verify each thread got its own trace
        thread_names = [result[1] for result in results]
        expected_names = [f"thread_{i}" for i in range(5)]
        assert sorted(thread_names) == sorted(expected_names)

        # Verify all traces were started and ended
        assert mock_tracing_core.start_trace.call_count == 5
        assert mock_tracing_core.end_trace.call_count == 5

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_early_return(self, mock_get_instance):
        """Test context manager behavior with early return statements."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        def function_with_early_return():
            with start_trace("early_return_trace"):
                if True:  # Simulate condition for early return
                    return "early_result"
                # This code should not be reached
                return "normal_result"

        result = function_with_early_return()

        # Verify early return worked
        assert result == "early_result"

        # Verify trace was still properly ended
        mock_tracing_core.start_trace.assert_called_once()
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Success")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_finally_block(self, mock_get_instance):
        """Test context manager interaction with finally blocks."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        finally_executed = []

        try:
            with start_trace("finally_trace"):
                try:
                    raise ValueError("test error")
                finally:
                    finally_executed.append("finally_block")
        except ValueError:
            pass

        # Verify finally block was executed
        assert finally_executed == ["finally_block"]

        # Verify trace was ended with Error state
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Error")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_backwards_compatibility_existing_patterns(self, mock_get_instance):
        """Test that existing code patterns continue to work."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Test various existing patterns that should still work

        # Pattern 1: Basic usage
        with start_trace("basic") as trace:
            assert trace is not None
            assert hasattr(trace, "span")

        # Pattern 2: With tags
        with start_trace("tagged", tags=["test", "example"]) as trace:
            assert trace is not None

        # Pattern 3: Accessing trace properties
        with start_trace("properties") as trace:
            span = trace.span
            assert span is mock_span

        # Pattern 4: Manual end_trace (should still work)
        trace = start_trace("manual")
        end_trace(trace, "Success")

        # Verify all calls were made correctly
        assert mock_tracing_core.start_trace.call_count == 4
        assert mock_tracing_core.end_trace.call_count == 4

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_edge_case_none_trace_context(self, mock_get_instance):
        """Test edge case where start_trace returns None."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        # Mock start_trace to return None (edge case)
        mock_tracing_core.start_trace.return_value = None

        # This should not raise an exception
        result = start_trace("none_trace")
        assert result is None

        # Verify start_trace was called
        mock_tracing_core.start_trace.assert_called_once()

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_edge_case_tracing_core_not_initialized(self, mock_get_instance):
        """Test edge case where TracingCore is not initialized."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = False
        mock_get_instance.return_value = mock_tracing_core

        # Mock init to fail
        with patch("agentops.init") as mock_init:
            mock_init.side_effect = Exception("Init failed")

            # This should return None and not raise
            result = start_trace("uninitialized")
            assert result is None

            # Verify init was attempted
            mock_init.assert_called_once()

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_edge_case_exception_in_exit_method(self, mock_get_instance):
        """Test edge case where exception occurs in __exit__ method."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        # Mock end_trace to raise an exception
        mock_tracing_core.end_trace.side_effect = Exception("End trace failed")

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # The context manager should handle the exception gracefully
        with start_trace("exception_in_exit"):
            pass  # Normal execution

        # Verify end_trace was called despite the exception
        mock_tracing_core.end_trace.assert_called_once()

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_performance_many_sequential_traces(self, mock_get_instance):
        """Test performance with many sequential traces."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        def create_mock_trace(i):
            mock_span = Mock()
            mock_span.name = f"trace_{i}"
            return TraceContext(mock_span)

        # Create many mock traces
        num_traces = 100
        mock_traces = [create_mock_trace(i) for i in range(num_traces)]
        mock_tracing_core.start_trace.side_effect = mock_traces

        # Execute many sequential traces
        start_time = time.time()

        for i in range(num_traces):
            with start_trace(f"trace_{i}") as trace:
                assert trace is mock_traces[i]

        end_time = time.time()

        # Verify all traces were processed
        assert mock_tracing_core.start_trace.call_count == num_traces
        assert mock_tracing_core.end_trace.call_count == num_traces

        # Performance should be reasonable (less than 1 second for 100 traces)
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Execution took too long: {execution_time}s"

    def test_trace_context_state_management(self):
        """Test TraceContext internal state management."""
        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        # Test initial state
        assert trace_context._end_state == "Indeterminate"

        # Test state change on exception
        trace_context.__exit__(ValueError, ValueError("test"), None)
        assert trace_context._end_state == "Error"

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_async_context(self, mock_get_instance):
        """Test context manager behavior in async context (sync usage)."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        async def async_function():
            with start_trace("async_context") as trace:
                await asyncio.sleep(0.001)  # Simulate async work
                return trace

        # Run the async function
        result = asyncio.run(async_function())

        # Verify trace was handled correctly
        assert result is mock_trace
        mock_tracing_core.start_trace.assert_called_once()
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Success")


class TestContextManagerBackwardCompatibility:
    """Test backward compatibility with existing code patterns."""

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_existing_code_patterns_still_work(self, mock_get_instance):
        """Test that all existing code patterns continue to work."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Pattern 1: Basic context manager
        with start_trace("basic") as trace:
            assert trace is not None

        # Pattern 2: With tags as list
        with start_trace("list_tags", tags=["tag1", "tag2"]) as trace:
            assert trace is not None

        # Pattern 3: With tags as dict
        with start_trace("dict_tags", tags={"env": "test"}) as trace:
            assert trace is not None

        # Pattern 4: Accessing span
        with start_trace("span_access") as trace:
            span = trace.span
            assert span is mock_span

        # Pattern 5: Manual trace management (legacy)
        trace = start_trace("manual")
        end_trace(trace)

        # All patterns should work identically
        assert mock_tracing_core.start_trace.call_count == 5

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_api_compatibility(self, mock_get_instance):
        """Test that the API remains exactly the same."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Test function signatures haven't changed

        # start_trace with all parameters
        trace1 = start_trace("test", tags=["tag"])
        assert trace1 is mock_trace

        # start_trace with positional args
        trace2 = start_trace("test2")
        assert trace2 is mock_trace

        # end_trace with all parameters
        end_trace(trace1, "Success")

        # end_trace with defaults
        end_trace(trace2)

        # Verify calls were made correctly
        mock_tracing_core.start_trace.assert_has_calls(
            [call(trace_name="test", tags=["tag"]), call(trace_name="test2", tags=None)]
        )
        mock_tracing_core.end_trace.assert_has_calls(
            [call(trace_context=trace1, end_state="Success"), call(trace_context=trace2, end_state="Success")]
        )

    def test_return_type_compatibility(self):
        """Test that return types are compatible with existing code."""
        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        # Test that TraceContext has all expected attributes
        assert hasattr(trace_context, "span")
        assert hasattr(trace_context, "token")
        assert hasattr(trace_context, "is_init_trace")
        assert hasattr(trace_context, "_end_state")

        # Test that it can be used as a context manager
        assert hasattr(trace_context, "__enter__")
        assert hasattr(trace_context, "__exit__")

        # Test that __enter__ returns self (standard pattern)
        assert trace_context.__enter__() is trace_context

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_keyboard_interrupt(self, mock_get_instance):
        """Test context manager behavior with KeyboardInterrupt."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Test KeyboardInterrupt handling
        with pytest.raises(KeyboardInterrupt):
            with start_trace("keyboard_interrupt_trace"):
                raise KeyboardInterrupt("User interrupted")

        # Verify trace was ended with Error state
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Error")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_system_exit(self, mock_get_instance):
        """Test context manager behavior with SystemExit."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Test SystemExit handling
        with pytest.raises(SystemExit):
            with start_trace("system_exit_trace"):
                raise SystemExit(1)

        # Verify trace was ended with Error state
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Error")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_in_generator_function(self, mock_get_instance):
        """Test context manager usage within generator functions."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        def trace_generator():
            with start_trace("generator_trace") as trace:
                yield f"value_1_{trace.span}"
                yield f"value_2_{trace.span}"
                yield f"value_3_{trace.span}"

        # Consume the generator
        results = list(trace_generator())

        # Verify generator worked correctly
        assert len(results) == 3
        assert all("value_" in result for result in results)

        # Verify trace was properly managed
        mock_tracing_core.start_trace.assert_called_once()
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Success")

    def test_context_manager_exit_return_value(self):
        """Test that __exit__ always returns False (doesn't suppress exceptions)."""
        mock_span = Mock()
        trace_context = TraceContext(mock_span)

        # Test with no exception
        result = trace_context.__exit__(None, None, None)
        assert result is False

        # Test with exception
        result = trace_context.__exit__(ValueError, ValueError("test"), None)
        assert result is False

        # Test with different exception types
        for exc_type in [RuntimeError, TypeError, KeyboardInterrupt, SystemExit]:
            result = trace_context.__exit__(exc_type, exc_type("test"), None)
            assert result is False, f"__exit__ should return False for {exc_type.__name__}"

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_very_large_data(self, mock_get_instance):
        """Test context manager with very large trace names and tags."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Test with very large trace name
        large_trace_name = "x" * 10000  # 10KB trace name
        large_tags = {f"key_{i}": "x" * 1000 for i in range(100)}  # Large tags

        with start_trace(large_trace_name, tags=large_tags) as trace:
            assert trace is mock_trace

        # Verify the large data was passed correctly
        mock_tracing_core.start_trace.assert_called_once_with(trace_name=large_trace_name, tags=large_tags)
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Success")

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_with_asyncio_tasks(self, mock_get_instance):
        """Test context manager with actual asyncio tasks (not just async functions)."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        # Create different mock traces for each task
        mock_spans = [Mock() for _ in range(3)]
        mock_traces = [TraceContext(span) for span in mock_spans]
        mock_tracing_core.start_trace.side_effect = mock_traces

        async def task_with_trace(task_id):
            with start_trace(f"async_task_{task_id}"):
                await asyncio.sleep(0.001)  # Simulate async work
                return f"result_{task_id}"

        async def run_concurrent_tasks():
            # Create multiple asyncio tasks
            tasks = [
                asyncio.create_task(task_with_trace(1)),
                asyncio.create_task(task_with_trace(2)),
                asyncio.create_task(task_with_trace(3)),
            ]

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            return results

        # Run the concurrent tasks
        results = asyncio.run(run_concurrent_tasks())

        # Verify all tasks completed
        assert len(results) == 3
        assert results == ["result_1", "result_2", "result_3"]

        # Verify all traces were started and ended
        assert mock_tracing_core.start_trace.call_count == 3
        assert mock_tracing_core.end_trace.call_count == 3

    @patch("agentops.sdk.core.TracingCore.get_instance")
    def test_context_manager_resource_cleanup_on_exit_failure(self, mock_get_instance):
        """Test that resources are cleaned up even if __exit__ fails."""
        mock_tracing_core = Mock()
        mock_tracing_core.initialized = True
        mock_get_instance.return_value = mock_tracing_core

        mock_span = Mock()
        mock_trace = TraceContext(mock_span)
        mock_tracing_core.start_trace.return_value = mock_trace

        # Mock end_trace to fail
        mock_tracing_core.end_trace.side_effect = Exception("End trace failed")

        # The context manager should handle the failure gracefully
        with start_trace("cleanup_test") as trace:
            assert trace is mock_trace
            # Normal execution

        # Verify end_trace was attempted despite the failure
        mock_tracing_core.end_trace.assert_called_once_with(mock_trace, "Success")

        # Verify the trace state was still updated
        assert mock_trace._end_state == "Success"
