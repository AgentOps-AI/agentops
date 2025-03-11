import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from opentelemetry.trace import StatusCode

from agentops.sdk.traced import TracedObject
from agentops.semconv.core import CoreAttributes


# Create a concrete implementation of TracedObject for testing
class ConcreteTracedObject(TracedObject):
    """Concrete implementation of TracedObject for testing."""
    pass


class TestTracedObject(unittest.TestCase):
    """Test the TracedObject base class."""

    def test_init(self):
        """Test initialization."""
        # Test with default trace_id
        obj = TracedObject()
        self.assertIsInstance(obj.trace_id, UUID)
        self.assertIsNone(obj.span_id)
        self.assertIsNone(obj.span)

        # Test with custom trace_id
        trace_id = "12345678-1234-5678-1234-567812345678"
        obj = TracedObject(trace_id=trace_id)
        self.assertEqual(str(obj.trace_id), trace_id)

        # Test with attributes
        attributes = {"key": "value"}
        obj = TracedObject(attributes=attributes)
        self.assertEqual(obj._attributes, attributes)
        
        # Test with name and kind
        obj = ConcreteTracedObject(name="test", kind="test")
        self.assertEqual(obj.name, "test")
        self.assertEqual(obj.kind, "test")
        self.assertIsNone(obj._parent)
        self.assertFalse(obj.immediate_export)
        self.assertFalse(obj.is_started)
        self.assertFalse(obj.is_ended)
        
        # Test with immediate_export
        obj = ConcreteTracedObject(name="test", kind="test", immediate_export=True)
        self.assertTrue(obj.immediate_export)
        self.assertEqual(obj._attributes[CoreAttributes.EXPORT_IMMEDIATELY], True)

    def test_set_attribute(self):
        """Test setting attributes."""
        obj = TracedObject()
        
        # Test without span
        obj.set_attribute("key", "value")
        self.assertEqual(obj._attributes["key"], "value")
        
        # Test with span
        mock_span = MagicMock()
        obj._span = mock_span
        obj.set_attribute("key2", "value2")
        self.assertEqual(obj._attributes["key2"], "value2")
        mock_span.set_attribute.assert_called_once_with("key2", "value2")

    def test_set_attributes(self):
        """Test setting multiple attributes."""
        obj = TracedObject()
        
        # Test without span
        attributes = {"key1": "value1", "key2": "value2"}
        obj.set_attributes(attributes)
        self.assertEqual(obj._attributes["key1"], "value1")
        self.assertEqual(obj._attributes["key2"], "value2")
        
        # Test with span
        mock_span = MagicMock()
        obj._span = mock_span
        attributes = {"key3": "value3", "key4": "value4"}
        obj.set_attributes(attributes)
        self.assertEqual(obj._attributes["key3"], "value3")
        self.assertEqual(obj._attributes["key4"], "value4")
        mock_span.set_attribute.assert_any_call("key3", "value3")
        mock_span.set_attribute.assert_any_call("key4", "value4")

    def test_set_status(self):
        """Test setting status."""
        obj = TracedObject()
        
        # Test without span (should not raise error)
        obj.set_status(StatusCode.OK)
        
        # Test with span
        mock_span = MagicMock()
        obj._span = mock_span
        
        # Test with StatusCode
        obj.set_status(StatusCode.OK)
        mock_span.set_status.assert_called_once()
        
        # Test with string
        mock_span.reset_mock()
        obj.set_status("OK")
        mock_span.set_status.assert_called_once()
        
        # Test with string and description
        mock_span.reset_mock()
        obj.set_status("ERROR", "Something went wrong")
        mock_span.set_status.assert_called_once()

    def test_str_repr(self):
        """Test string representation."""
        obj = TracedObject()
        self.assertIn("TracedObject", str(obj))
        self.assertIn("trace_id", str(obj))
        
        self.assertIn("TracedObject", repr(obj))
        self.assertIn("trace_id", repr(obj))
        self.assertIn("span_id", repr(obj))
    
    @patch("agentops.sdk.traced.trace")
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
        span = ConcreteTracedObject(name="test", kind="test")
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
        span = ConcreteTracedObject(name="test", kind="test")
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
        span = ConcreteTracedObject(name="test", kind="test", immediate_export=True)
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
        span = ConcreteTracedObject(name="test", kind="test")
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
        span = ConcreteTracedObject(name="test", kind="test", immediate_export=True)
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