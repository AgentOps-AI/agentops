import logging
from uuid import uuid4
from unittest.mock import Mock

import pytest
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

from agentops.instrumentation import setup_session_telemetry, cleanup_session_telemetry
from agentops.log_config import logger
from agentops.session import SessionLogExporter
from agentops.log_capture import LogCapture
from agentops.session import add_session


class TestSessionTelemetry:
    @pytest.fixture
    def session_id(self):
        return str(uuid4())

    @pytest.fixture
    def initial_handler_count(self):
        """Get initial number of handlers on the logger"""
        return len(logger.handlers)

    def test_setup_telemetry_components(self, session_id, mock_req, agentops_session):
        """Test that telemetry setup creates and returns the expected components"""
        # Set up telemetry with real exporter
        log_exporter = SessionLogExporter(session=agentops_session)
        log_handler, log_processor = setup_session_telemetry(session_id, log_exporter)

        # Verify components are created with correct types
        assert isinstance(log_handler, LoggingHandler)
        assert isinstance(log_processor, BatchLogRecordProcessor)

        # Verify handler has correct configuration
        assert log_handler.level == logging.INFO
        assert isinstance(log_handler._logger_provider, LoggerProvider)

        # Clean up
        cleanup_session_telemetry(log_handler, log_processor)

    def test_handler_installation_and_cleanup(self, session_id, mock_req, agentops_session, initial_handler_count):
        """Test that handler is properly installed and removed"""
        # Set up telemetry
        log_exporter = SessionLogExporter(session=agentops_session)
        log_handler, log_processor = setup_session_telemetry(session_id, log_exporter)
        logger.addHandler(log_handler)

        # Verify handler was added
        assert len(logger.handlers) == initial_handler_count + 1
        assert log_handler in logger.handlers

        # Clean up
        cleanup_session_telemetry(log_handler, log_processor)

        # Verify handler was removed
        assert len(logger.handlers) == initial_handler_count
        assert log_handler not in logger.handlers

    def test_logging_with_telemetry(self, mock_req, agentops_session):
        """Test that logs are captured and exported"""
        # Create and start log capture
        capture = LogCapture(session_id=agentops_session.session_id)
        capture.start()

        try:
            session_id = str(agentops_session.session_id)
            print(f"\nSession ID: {session_id}")
            
            log_exporter = SessionLogExporter(session=agentops_session)
            log_handler, log_processor = setup_session_telemetry(session_id, log_exporter)
            logger.addHandler(log_handler)

            # Log some messages
            test_message = "Test log message"
            print(f"Sending message: {test_message}")
            logger.info(test_message)

            # Force flush logs
            print("Forcing flush...")
            log_processor.force_flush()
            print("Flush complete")

            # Debug: Print all request URLs and mock setup
            print("\nMock setup:")
            print(f"Base URL: {agentops_session.config.endpoint}")
            print(f"Expected endpoint: {agentops_session.config.endpoint}/v3/logs/{session_id}")
            print("\nRequest history:")
            for req in mock_req.request_history:
                print(f"Method: {req.method}, URL: {req.url}")
                if hasattr(req, 'text'):
                    print(f"Body: {req.text}")

            # Verify the request was made to the logs endpoint
            assert any(req.url.endswith(f"/v3/logs/{session_id}") for req in mock_req.request_history), \
                f"No request found for /v3/logs/{session_id} in {[req.url for req in mock_req.request_history]}"

        finally:
            # Clean up
            capture.stop()
            cleanup_session_telemetry(log_handler, log_processor)

    def test_cleanup_prevents_further_logging(self, session_id, mock_req, agentops_session):
        """Test that cleanup prevents further log exports"""
        # Set up telemetry
        log_exporter = SessionLogExporter(session=agentops_session)
        log_handler, log_processor = setup_session_telemetry(session_id, log_exporter)
        logger.addHandler(log_handler)

        # Log before cleanup
        logger.info("Before cleanup")
        initial_request_count = len([r for r in mock_req.request_history if r.url.endswith(f"/v3/logs/{session_id}")])

        # Clean up
        cleanup_session_telemetry(log_handler, log_processor)

        # Try logging after cleanup
        logger.info("After cleanup")
        log_processor.force_flush()

        # Verify no new requests were made
        final_request_count = len([r for r in mock_req.request_history if r.url.endswith(f"/v3/logs/{session_id}")])
        assert final_request_count == initial_request_count

    def test_multiple_sessions_isolation(self, mock_req, agentops_session):
        """Test that multiple sessions maintain logging isolation"""
        # Set up two sessions
        session_id_1 = str(uuid4())
        session_id_2 = str(uuid4())
        
        log_exporter = SessionLogExporter(session=agentops_session)
        handler1, processor1 = setup_session_telemetry(session_id_1, log_exporter)
        handler2, processor2 = setup_session_telemetry(session_id_2, log_exporter)
        
        logger.addHandler(handler1)
        logger.addHandler(handler2)

        # Verify both handlers are present
        assert handler1 in logger.handlers
        assert handler2 in logger.handlers

        # Clean up one session
        cleanup_session_telemetry(handler1, processor1)

        # Verify only the correct handler was removed
        assert handler1 not in logger.handlers
        assert handler2 in logger.handlers

        # Clean up the other session
        cleanup_session_telemetry(handler2, processor2) 
