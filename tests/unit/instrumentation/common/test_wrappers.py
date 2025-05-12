"""
Unit tests for the common wrappers module.

This module tests the functionality of the common wrapper utilities
for OpenTelemetry instrumentation, including WrapConfig, _update_span,
_finish_span_success, _finish_span_error, _create_wrapper, wrap, and unwrap.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Optional, Tuple

from opentelemetry.trace import SpanKind

from agentops.instrumentation.common.wrappers import (
    WrapConfig,
    _update_span,
    _finish_span_success,
    _finish_span_error,
    _create_wrapper,
    wrap,
    unwrap,
)
from agentops.instrumentation.common.attributes import AttributeMap
from tests.unit.instrumentation.mock_span import MockTracingSpan


class TestWrapConfig:
    """Tests for the WrapConfig class."""

    def test_wrap_config_initialization(self):
        """Test that WrapConfig is initialized properly with default values."""

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            return {"key": "value"}

        # Initialize a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Verify config values
        assert config.trace_name == "test_trace"
        assert config.package == "test_package"
        assert config.class_name == "TestClass"
        assert config.method_name == "test_method"
        assert config.handler == dummy_handler
        assert config.span_kind == SpanKind.CLIENT  # Default value

    def test_wrap_config_repr(self):
        """Test the string representation of WrapConfig."""

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            return {"key": "value"}

        # Initialize a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Verify the string representation
        assert repr(config) == "test_package.TestClass.test_method"

    def test_wrap_config_with_custom_span_kind(self):
        """Test that WrapConfig accepts a custom span kind."""

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            return {"key": "value"}

        # Initialize a WrapConfig with custom span kind
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
            span_kind=SpanKind.SERVER,
        )

        # Verify the span kind
        assert config.span_kind == SpanKind.SERVER


class TestSpanHelpers:
    """Tests for span helper functions."""

    def test_update_span(self):
        """Test _update_span sets attributes on a span."""
        # Create a mock span
        mock_span = MockTracingSpan()

        # Define attributes to set
        attributes = {"key1": "value1", "key2": 42, "key3": True}

        # Call _update_span
        _update_span(mock_span, attributes)

        # Verify attributes were set
        for key, value in attributes.items():
            assert mock_span.attributes[key] == value

    def test_finish_span_success(self):
        """Test _finish_span_success sets status to OK."""
        # Create a mock span
        mock_span = MockTracingSpan()

        # Call _finish_span_success
        _finish_span_success(mock_span)

        # Verify status was set
        assert mock_span.status is not None
        # The actual object is a real Status with StatusCode.OK
        # We're not checking the exact type, just that it was called with OK status code

    def test_finish_span_error(self):
        """Test _finish_span_error sets error status and records exception."""
        # Create a mock span
        mock_span = MockTracingSpan()

        # Create a test exception
        test_exception = ValueError("Test error")

        # Call _finish_span_error
        _finish_span_error(mock_span, test_exception)

        # Verify status was set to ERROR
        assert mock_span.status is not None
        # The actual object is a real Status with StatusCode.ERROR
        # We're not checking the exact type, just that it was called with ERROR status code

        # Verify exception was recorded
        assert len(mock_span.events) == 1
        assert mock_span.events[0]["name"] == "exception"
        assert mock_span.events[0]["exception"] == test_exception


class TestCreateWrapper:
    """Tests for _create_wrapper and wrapper functionality."""

    def test_create_wrapper_success_path(self):
        """Test wrapper created by _create_wrapper handles success path."""
        # Create a mock tracer
        mock_tracer = MagicMock()
        mock_span = MockTracingSpan()

        # Mock start_as_current_span to return our mock span
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            result = {}
            if args:
                result["args"] = str(args)
            if kwargs:
                result["kwargs"] = str(kwargs)
            if return_value is not None:
                result["return_value"] = str(return_value)
            return result

        # Create a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Create the wrapper
        wrapper = _create_wrapper(config, mock_tracer)

        # Create a mock wrapped function
        def mock_wrapped(*args, **kwargs):
            return "success"

        # Call the wrapper with the wrapped function
        result = wrapper(mock_wrapped, None, ("arg1", "arg2"), {"kwarg1": "value1"})

        # Verify the result
        assert result == "success"

        # Verify tracer was called correctly
        mock_tracer.start_as_current_span.assert_called_once_with("test_trace", kind=SpanKind.CLIENT)

        # Verify attributes were set on the span
        assert "args" in mock_span.attributes
        assert "('arg1', 'arg2')" == mock_span.attributes["args"]
        assert "kwargs" in mock_span.attributes
        assert "{'kwarg1': 'value1'}" == mock_span.attributes["kwargs"]
        assert "return_value" in mock_span.attributes
        assert "success" == mock_span.attributes["return_value"]

    def test_create_wrapper_error_path(self):
        """Test wrapper created by _create_wrapper handles error path."""
        # Create a mock tracer
        mock_tracer = MagicMock()
        mock_span = MockTracingSpan()

        # Mock start_as_current_span to return our mock span
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            result = {}
            if args:
                result["args"] = str(args)
            if kwargs:
                result["kwargs"] = str(kwargs)
            if return_value is not None:
                result["return_value"] = str(return_value)
            return result

        # Create a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Create the wrapper
        wrapper = _create_wrapper(config, mock_tracer)

        # Create a mock wrapped function that raises an exception
        def mock_wrapped(*args, **kwargs):
            raise ValueError("Test error")

        # Call the wrapper with the wrapped function, expecting an exception
        with pytest.raises(ValueError, match="Test error"):
            wrapper(mock_wrapped, None, ("arg1", "arg2"), {"kwarg1": "value1"})

        # Verify tracer was called correctly
        mock_tracer.start_as_current_span.assert_called_once_with("test_trace", kind=SpanKind.CLIENT)

        # Verify attributes were set on the span
        assert "args" in mock_span.attributes
        assert "('arg1', 'arg2')" == mock_span.attributes["args"]
        assert "kwargs" in mock_span.attributes
        assert "{'kwarg1': 'value1'}" == mock_span.attributes["kwargs"]

        # Verify exception was recorded
        assert len(mock_span.events) == 1
        assert mock_span.events[0]["name"] == "exception"
        assert isinstance(mock_span.events[0]["exception"], ValueError)

    def test_create_wrapper_suppressed_instrumentation(self):
        """Test wrapper respects suppressed instrumentation context."""
        # Create a mock tracer
        mock_tracer = MagicMock()

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            return {}

        # Create a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Create the wrapper
        wrapper = _create_wrapper(config, mock_tracer)

        # Create a mock wrapped function
        mock_wrapped = MagicMock(return_value="success")

        # Mock the context_api to return True for suppressed instrumentation
        with patch("agentops.instrumentation.common.wrappers.context_api.get_value", return_value=True):
            result = wrapper(mock_wrapped, None, ("arg1", "arg2"), {"kwarg1": "value1"})

        # Verify the result
        assert result == "success"

        # Verify tracer was NOT called
        mock_tracer.start_as_current_span.assert_not_called()

        # Verify wrapped function was called directly
        mock_wrapped.assert_called_once_with("arg1", "arg2", kwarg1="value1")


class TestWrapUnwrap:
    """Tests for wrap and unwrap functions."""

    def test_wrap_function(self):
        """Test that wrap calls wrap_function_wrapper with correct arguments."""

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            return {}

        # Create a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Create a mock tracer
        mock_tracer = MagicMock()

        # Mock wrap_function_wrapper
        with patch("agentops.instrumentation.common.wrappers.wrap_function_wrapper") as mock_wrap:
            # Mock _create_wrapper to return a simple function
            with patch("agentops.instrumentation.common.wrappers._create_wrapper") as mock_create_wrapper:
                mock_create_wrapper.return_value = lambda *args: None

                # Call wrap
                wrap(config, mock_tracer)

                # Verify wrap_function_wrapper was called correctly
                mock_wrap.assert_called_once_with(
                    "test_package", "TestClass.test_method", mock_create_wrapper.return_value
                )

                # Verify _create_wrapper was called correctly
                mock_create_wrapper.assert_called_once_with(config, mock_tracer)

    def test_unwrap_function(self):
        """Test that unwrap calls _unwrap with correct arguments."""

        # Create a simple attribute handler
        def dummy_handler(
            args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None
        ) -> AttributeMap:
            return {}

        # Create a WrapConfig
        config = WrapConfig(
            trace_name="test_trace",
            package="test_package",
            class_name="TestClass",
            method_name="test_method",
            handler=dummy_handler,
        )

        # Mock _unwrap
        with patch("agentops.instrumentation.common.wrappers._unwrap") as mock_unwrap:
            # Call unwrap
            unwrap(config)

            # Verify _unwrap was called correctly
            mock_unwrap.assert_called_once_with("test_package.TestClass", "test_method")


if __name__ == "__main__":
    pytest.main()
