import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import StatusCode

from agentops.config import Config
from agentops.sdk.core import TracingCore, ImmediateExportProcessor
from agentops.sdk.spanned import SpannedBase


class TestImmediateExportProcessor(unittest.TestCase):
    """Test the ImmediateExportProcessor class."""

    def test_init(self):
        """Test initialization."""
        exporter = MagicMock()
        processor = ImmediateExportProcessor(exporter)
        self.assertEqual(processor._exporter, exporter)

    def test_on_start(self):
        """Test on_start method."""
        # Set up
        exporter = MagicMock()
        processor = ImmediateExportProcessor(exporter)
        span = MagicMock()
        
        # Test with export.immediate=False
        span.attributes = {}
        processor.on_start(span)
        exporter.export.assert_not_called()
        
        # Test with export.immediate=True
        span.attributes = {"export.immediate": True}
        processor.on_start(span)
        exporter.export.assert_called_once_with([span])
        
        # Test with exception
        exporter.reset_mock()
        exporter.export.side_effect = Exception("Test error")
        processor.on_start(span)  # Should not raise

    def test_on_end(self):
        """Test on_end method."""
        # Set up
        exporter = MagicMock()
        processor = ImmediateExportProcessor(exporter)
        span = MagicMock()
        
        # Test normal case
        processor.on_end(span)
        exporter.export.assert_called_once_with([span])
        
        # Test with exception
        exporter.reset_mock()
        exporter.export.side_effect = Exception("Test error")
        processor.on_end(span)  # Should not raise

    def test_force_flush(self):
        """Test force_flush method."""
        # Set up
        exporter = MagicMock()
        exporter.force_flush.return_value = True
        processor = ImmediateExportProcessor(exporter)
        
        # Test normal case
        result = processor.force_flush()
        self.assertTrue(result)
        exporter.force_flush.assert_called_once()
        
        # Test with exception
        exporter.reset_mock()
        exporter.force_flush.side_effect = Exception("Test error")
        result = processor.force_flush()
        self.assertFalse(result)

    def test_shutdown(self):
        """Test shutdown method."""
        # Set up
        exporter = MagicMock()
        processor = ImmediateExportProcessor(exporter)
        
        # Test
        processor.shutdown()
        exporter.shutdown.assert_called_once()


class TestTracingCore(unittest.TestCase):
    """Test the TracingCore class."""

    def setUp(self):
        """Set up the test."""
        # Reset the singleton instance
        TracingCore._instance = None

    def test_get_instance(self):
        """Test get_instance method."""
        # Test getting the instance
        instance1 = TracingCore.get_instance()
        self.assertIsInstance(instance1, TracingCore)
        
        # Test singleton pattern
        instance2 = TracingCore.get_instance()
        self.assertIs(instance2, instance1)

    @patch("agentops.sdk.core.TracerProvider")
    @patch("agentops.sdk.core.trace")
    def test_initialize(self, mock_trace, mock_tracer_provider):
        """Test initialize method."""
        # Set up
        core = TracingCore()
        config = Config(api_key="test_key")
        mock_provider = MagicMock()
        mock_tracer_provider.return_value = mock_provider
        
        # Test initialization
        core.initialize(config)
        self.assertTrue(core._initialized)
        self.assertEqual(core._config, config)
        mock_tracer_provider.assert_called_once()
        mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)
        
        # Test initializing an already initialized core
        mock_tracer_provider.reset_mock()
        mock_trace.reset_mock()
        core.initialize(config)
        mock_tracer_provider.assert_not_called()
        mock_trace.set_tracer_provider.assert_not_called()

    def test_shutdown(self):
        """Test shutdown method."""
        # Set up
        core = TracingCore()
        core._initialized = True
        processor1 = MagicMock()
        processor2 = MagicMock()
        core._processors = [processor1, processor2]
        core._provider = MagicMock()
        
        # Test shutdown
        core.shutdown()
        self.assertFalse(core._initialized)
        processor1.force_flush.assert_called_once()
        processor2.force_flush.assert_called_once()
        core._provider.shutdown.assert_called_once()
        
        # Test shutting down an already shut down core
        processor1.reset_mock()
        processor2.reset_mock()
        core._provider.reset_mock()
        core.shutdown()
        processor1.force_flush.assert_not_called()
        processor2.force_flush.assert_not_called()
        core._provider.shutdown.assert_not_called()

    def test_get_tracer(self):
        """Test get_tracer method."""
        # Set up
        core = TracingCore()
        mock_tracer = MagicMock()
        with patch("agentops.sdk.core.trace") as mock_trace:
            mock_trace.get_tracer.return_value = mock_tracer
            
            # Test getting a tracer when not initialized
            with self.assertRaises(RuntimeError):
                core.get_tracer()
            
            # Test getting a tracer when initialized
            core._initialized = True
            tracer = core.get_tracer("test_tracer")
            self.assertEqual(tracer, mock_tracer)
            mock_trace.get_tracer.assert_called_once_with("test_tracer")

    @patch("agentops.sdk.core.SpanFactory")
    def test_create_span(self, mock_factory):
        """Test create_span method."""
        # Set up
        core = TracingCore()
        mock_span = MagicMock()
        mock_factory.create_span.return_value = mock_span
        
        # Test creating a span when not initialized
        with self.assertRaises(RuntimeError):
            core.create_span(kind="test", name="test_span")
        
        # Test creating a span when initialized
        core._initialized = True
        span = core.create_span(
            kind="test",
            name="test_span",
            attributes={"key": "value"},
            immediate_export=True
        )
        self.assertEqual(span, mock_span)
        mock_factory.create_span.assert_called_once_with(
            kind="test",
            name="test_span",
            parent=None,
            attributes={"key": "value", "export.immediate": True},
            auto_start=True,
            immediate_export=True
        )

    @patch("agentops.sdk.core.SpanFactory")
    def test_register_span_type(self, mock_factory):
        """Test register_span_type method."""
        # Set up
        core = TracingCore()
        mock_span_class = MagicMock()
        
        # Test
        core.register_span_type("test", mock_span_class)
        mock_factory.register_span_type.assert_called_once_with("test", mock_span_class)


if __name__ == "__main__":
    unittest.main() 