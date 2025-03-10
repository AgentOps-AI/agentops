import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from opentelemetry.trace import StatusCode

from agentops.sdk.traced import TracedObject


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


if __name__ == "__main__":
    unittest.main() 