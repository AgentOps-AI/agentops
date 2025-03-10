import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from opentelemetry.trace import StatusCode

from agentops.sdk.spanned import SpannedBase


# Create a concrete implementation of SpannedBase for testing
class TestSpan(SpannedBase):
    """Concrete implementation of SpannedBase for testing."""
    pass


class TestSpannedBase(unittest.TestCase):
    """Test the SpannedBase abstract class."""

    def test_init(self):
        """Test initialization."""
        # Test basic initialization
        span = TestSpan(name="test", kind="test")
        self.assertEqual(span.name, "test")
        self.assertEqual(span.kind, "test")
        self.assertIsNone(span._parent)
        self.assertFalse(span.immediate_export)
        self.assertFalse(span.is_started)
        self.assertFalse(span.is_ended)
        
        # Test with immediate_export
        span = TestSpan(name="test", kind="test", immediate_export=True)
        self.assertTrue(span.immediate_export)
        self.assertEqual(span._attributes["export.immediate"], True)

    @patch("agentops.sdk.spanned.trace")
    def test_start(self, mock_trace):
        """Test starting a span."""
        # Set up mocks
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_context = MagicMock()
        mock_trace.set_span_in_context.return_value = mock_context
        
        # Test starting a span
        span = TestSpan(name="test", kind="test")
        result = span.start()
        
        # Verify
        self.assertEqual(result, span)
        self.assertTrue(span.is_started)
        self.assertFalse(span.is_ended)
        self.assertIsNotNone(span.start_time)
        self.assertIsNone(span.end_time)
        mock_trace.get_tracer.assert_called_once_with("agentops")
        mock_tracer.start_span.assert_called_once()
        mock_trace.set_span_in_context.assert_called_once_with(mock_span)
        
        # Test starting an already started span
        mock_trace.reset_mock()
        mock_tracer.reset_mock()
        result = span.start()
        self.assertEqual(result, span)
        mock_trace.get_tracer.assert_not_called()
        mock_tracer.start_span.assert_not_called()

    def test_end(self):
        """Test ending a span."""
        # Set up
        span = TestSpan(name="test", kind="test")
        mock_span = MagicMock()
        span._span = mock_span
        span._is_started = True
        
        # Test ending a span
        result = span.end()
        
        # Verify
        self.assertEqual(result, span)
        self.assertTrue(span.is_started)
        self.assertTrue(span.is_ended)
        self.assertIsNotNone(span.end_time)
        mock_span.end.assert_called_once()
        
        # Test ending an already ended span
        mock_span.reset_mock()
        result = span.end()
        self.assertEqual(result, span)
        mock_span.end.assert_not_called()

    def test_update(self):
        """Test updating a span."""
        # Set up
        span = TestSpan(name="test", kind="test", immediate_export=True)
        mock_span = MagicMock()
        span._span = mock_span
        span._is_started = True
        
        # Test updating a span
        result = span.update()
        
        # Verify
        self.assertEqual(result, span)
        mock_span.set_attribute.assert_called_once()
        self.assertIn("export.update", mock_span.set_attribute.call_args[0])
        
        # Test updating a span that's not configured for immediate export
        mock_span.reset_mock()
        span._immediate_export = False
        result = span.update()
        self.assertEqual(result, span)
        mock_span.set_attribute.assert_not_called()
        
        # Test updating a span that's not started
        mock_span.reset_mock()
        span._immediate_export = True
        span._is_started = False
        result = span.update()
        self.assertEqual(result, span)
        mock_span.set_attribute.assert_not_called()
        
        # Test updating a span that's ended
        mock_span.reset_mock()
        span._is_started = True
        span._is_ended = True
        result = span.update()
        self.assertEqual(result, span)
        mock_span.set_attribute.assert_not_called()

    def test_context_manager(self):
        """Test using a span as a context manager."""
        # Set up
        span = TestSpan(name="test", kind="test")
        span.start = MagicMock(return_value=span)
        span.end = MagicMock(return_value=span)
        
        # Test normal execution
        with span as s:
            self.assertEqual(s, span)
        span.start.assert_called_once()
        span.end.assert_called_once_with(StatusCode.OK)
        
        # Test with exception
        span.start.reset_mock()
        span.end.reset_mock()
        try:
            with span as s:
                raise ValueError("Test error")
        except ValueError:
            pass
        span.start.assert_called_once()
        span.end.assert_called_once()
        self.assertEqual(span.end.call_args[0][0], StatusCode.ERROR)

    def test_to_dict(self):
        """Test converting a span to a dictionary."""
        # Set up
        span = TestSpan(name="test", kind="test", immediate_export=True)
        span._is_started = True
        span._start_time = "2023-01-01T00:00:00Z"
        
        # Test
        result = span.to_dict()
        
        # Verify
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["kind"], "test")
        self.assertEqual(result["start_time"], "2023-01-01T00:00:00Z")
        self.assertIsNone(result["end_time"])
        self.assertTrue(result["is_started"])
        self.assertFalse(result["is_ended"])
        self.assertTrue(result["immediate_export"])


if __name__ == "__main__":
    unittest.main() 