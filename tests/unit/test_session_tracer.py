import gc
import uuid
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider

from agentops.session.processors import LiveProcessor
from agentops.session.tracer import SessionTracer, _session_tracers


def test_session_tracer_global_lifecycle():
    """Test the global lifecycle of SessionTracer."""
    # Create a mock session
    mock_session = MagicMock()

    mock_session.session_id = session_id = str(uuid.uuid4())
    mock_session.dict.return_value = {"session_id": session_id}

    # Verify _session_tracers is empty initially
    assert len(_session_tracers) == 0
    # Create a session tracer
    tracer = SessionTracer(mock_session)

    # Need to call start() to add the tracer to _session_tracers
    tracer.start()

    # Verify the tracer was added to _session_tracers
    assert len(_session_tracers) == 1
    assert mock_session.session_id in _session_tracers
    assert _session_tracers[mock_session.session_id] is tracer

    # Delete the tracer reference and force garbage collection
    del tracer
    gc.collect()  # Force garbage collection to trigger __del__
    # Verify _session_tracers is empty again
    assert len(_session_tracers) == 0
    assert session_id not in _session_tracers


class TestSessionTracer:
    """Tests for the SessionTracer class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.session_id = "test-session-id"
        self.mock_session.config.processor = None
        self.mock_session.config.exporter = None
        self.mock_session.config.exporter_endpoint = None
        self.mock_session.config.max_queue_size = 100
        self.mock_session.config.max_wait_time = 1000

    def test_init_with_custom_processor(self):
        """Test initialization with a custom processor."""
        mock_processor = MagicMock()
        self.mock_session.config.processor = mock_processor

        with patch("agentops.session.tracer.get_tracer_provider") as mock_get_provider:
            mock_provider = MagicMock(spec=TracerProvider)
            mock_get_provider.return_value = mock_provider

            tracer = SessionTracer(self.mock_session)

            # Verify the custom processor was added to the provider
            mock_provider.add_span_processor.assert_called_once_with(mock_processor)
            assert tracer._span_processor == mock_processor

    def test_init_with_custom_exporter(self):
        """Test initialization with a custom exporter."""
        mock_exporter = MagicMock()
        self.mock_session.config.exporter = mock_exporter

        with patch("agentops.session.tracer.get_tracer_provider") as mock_get_provider:
            mock_provider = MagicMock(spec=TracerProvider)
            mock_get_provider.return_value = mock_provider

            with patch("agentops.session.tracer.LiveProcessor") as mock_processor_cls:
                mock_processor = MagicMock()
                mock_processor_cls.return_value = mock_processor

                tracer = SessionTracer(self.mock_session)

                # Verify the processor was created with our exporter and added to the provider
                mock_processor_cls.assert_called_once_with(
                    mock_exporter,
                    max_export_batch_size=self.mock_session.config.max_queue_size,
                    schedule_delay_millis=self.mock_session.config.max_wait_time,
                )
                mock_provider.add_span_processor.assert_called_once_with(mock_processor)
                assert tracer._span_processor == mock_processor

    def test_init_with_default_exporter(self):
        """Test initialization with the default exporter."""
        with patch("agentops.session.tracer.get_tracer_provider") as mock_get_provider:
            mock_provider = MagicMock(spec=TracerProvider)
            mock_get_provider.return_value = mock_provider

            with patch("agentops.session.tracer.OTLPSpanExporter") as mock_exporter_cls:
                mock_exporter = MagicMock()
                mock_exporter_cls.return_value = mock_exporter

                with patch("agentops.session.tracer.LiveProcessor") as mock_processor_cls:
                    mock_processor = MagicMock()
                    mock_processor_cls.return_value = mock_processor

                    tracer = SessionTracer(self.mock_session)

                    # Verify the exporter was created with the default endpoint
                    mock_exporter_cls.assert_called_once_with(endpoint="https://otlp.agentops.cloud/v1/traces")

                    # Verify the processor was created with our exporter and added to the provider
                    mock_processor_cls.assert_called_once_with(
                        mock_exporter,
                        max_export_batch_size=self.mock_session.config.max_queue_size,
                        schedule_delay_millis=self.mock_session.config.max_wait_time,
                    )
                    mock_provider.add_span_processor.assert_called_once_with(mock_processor)
                    assert tracer._span_processor == mock_processor

    def test_shutdown_flushes_provider(self):
        """Test that shutdown flushes the tracer provider."""
        with patch("agentops.session.tracer.get_tracer_provider") as mock_get_provider:
            mock_provider = MagicMock(spec=TracerProvider)
            mock_get_provider.return_value = mock_provider

            tracer = SessionTracer(self.mock_session)
            tracer._token = None

            # Mock the tracer provider to avoid actual flushing
            with patch("agentops.session.tracer.trace.get_tracer_provider") as mock_get_trace_provider:
                mock_trace_provider = MagicMock(spec=TracerProvider)
                mock_get_trace_provider.return_value = mock_trace_provider

                tracer.shutdown()

                # Verify force_flush was called on the provider
                mock_trace_provider.force_flush.assert_called_once()

    def test_shutdown_no_processor(self):
        """Test shutdown when no processor is available."""
        with patch("agentops.session.tracer.get_tracer_provider"):
            tracer = SessionTracer(self.mock_session)
            tracer._span_processor = None
            tracer._token = None

            # This should not raise an exception
            tracer.shutdown()

    def test_shutdown_ends_session_span(self):
        """Test that shutdown ends the session span."""
        with patch("agentops.session.tracer.get_tracer_provider"):
            tracer = SessionTracer(self.mock_session)
            mock_span = MagicMock()

            # Set end_time to None to simulate a span that hasn't been ended
            mock_span.end_time = None

            tracer.session._span = mock_span
            tracer._token = None  # Avoid context detachment

            # Mock the tracer provider to avoid actual flushing
            with patch("agentops.session.tracer.trace.get_tracer_provider") as mock_get_provider:
                mock_provider = MagicMock()
                mock_get_provider.return_value = mock_provider

                tracer.shutdown()

                # Verify end was called on the span
                mock_span.end.assert_called_once()

    def test_del_calls_shutdown(self):
        """Test that __del__ calls shutdown."""
        with patch("agentops.session.tracer.get_tracer_provider"):
            tracer = SessionTracer(self.mock_session)

            with patch.object(tracer, "shutdown") as mock_shutdown:
                tracer.__del__()

                # Verify shutdown was called
                mock_shutdown.assert_called_once()
