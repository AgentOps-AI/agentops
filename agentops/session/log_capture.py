import logging
import sys
from typing import Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.resources import Resource


class LogCapture:
    """Captures terminal output for a session using OpenTelemetry logging.

    Integrates with TelemetryManager to use consistent configuration and logging setup.
    If no telemetry manager is available, creates a standalone logging setup.
    """

    def __init__(self, session):
        self.session = session
        # Use unique logger names to avoid conflicts
        self._stdout_logger = logging.getLogger(f"agentops.stdout.{id(self)}")
        self._stderr_logger = logging.getLogger(f"agentops.stderr.{id(self)}")
        self._stdout = None
        self._stderr = None
        self._handler = None
        self._logger_provider = None
        self._owns_handler = False  # Track if we created our own handler

        # Configure loggers to not propagate to parent loggers
        for logger in (self._stdout_logger, self._stderr_logger):
            logger.setLevel(logging.INFO)
            logger.propagate = False
            logger.handlers.clear()

    def start(self):
        """Start capturing output using OTEL logging handler"""
        if self._stdout is not None:
            return

        # Try to get handler from telemetry manager
        if hasattr(self.session, "_telemetry") and self.session._telemetry:
            self._handler = self.session._telemetry.get_log_handler()

        # Create our own handler if none exists
        if not self._handler:
            self._owns_handler = True

            # Use session's resource attributes if available
            resource_attrs = {"service.name": "agentops", "session.id": str(getattr(self.session, "id", "unknown"))}

            if (
                hasattr(self.session, "_telemetry")
                and self.session._telemetry
                and self.session._telemetry.config
                and self.session._telemetry.config.resource_attributes
            ):
                resource_attrs.update(self.session._telemetry.config.resource_attributes)

            # Setup logger provider with console exporter
            resource = Resource.create(resource_attrs)
            self._logger_provider = LoggerProvider(resource=resource)
            exporter = ConsoleLogExporter()
            self._logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

            self._handler = LoggingHandler(
                level=logging.INFO,
                logger_provider=self._logger_provider,
            )

            # Register with telemetry manager if available
            if hasattr(self.session, "_telemetry") and self.session._telemetry:
                self.session._telemetry.set_log_handler(self._handler)

        # Add handler to both loggers
        self._stdout_logger.addHandler(self._handler)
        self._stderr_logger.addHandler(self._handler)

        # Save original stdout/stderr
        self._stdout = sys.stdout
        self._stderr = sys.stderr

        # Replace with logging proxies
        sys.stdout = self._StdoutProxy(self._stdout_logger)
        sys.stderr = self._StderrProxy(self._stderr_logger)

    def stop(self):
        """Stop capturing output and restore stdout/stderr"""
        if self._stdout is None:
            return

        # Restore original stdout/stderr
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        self._stdout = None
        self._stderr = None

        # Clean up handlers
        if self._handler:
            self._stdout_logger.removeHandler(self._handler)
            self._stderr_logger.removeHandler(self._handler)

            # Only close/shutdown if we own the handler
            if self._owns_handler:
                self._handler.close()
                if self._logger_provider:
                    self._logger_provider.shutdown()

                # Clear from telemetry manager if we created it
                if hasattr(self.session, "_telemetry") and self.session._telemetry:
                    self.session._telemetry.set_log_handler(None)

            self._handler = None
            self._logger_provider = None

    def flush(self):
        """Flush any buffered logs"""
        if self._handler:
            self._handler.flush()

    class _StdoutProxy:
        """Proxies stdout to logger"""

        def __init__(self, logger):
            self._logger = logger

        def write(self, text):
            if text.strip():  # Only log non-empty strings
                self._logger.info(text.rstrip())

        def flush(self):
            pass

    class _StderrProxy:
        """Proxies stderr to logger"""

        def __init__(self, logger):
            self._logger = logger

        def write(self, text):
            if text.strip():  # Only log non-empty strings
                self._logger.error(text.rstrip())

        def flush(self):
            pass


if __name__ == "__main__":
    import time
    from dataclasses import dataclass
    from uuid import uuid4

    from agentops.telemetry.config import OTELConfig
    from agentops.telemetry.manager import TelemetryManager

    # Create a mock session with telemetry
    @dataclass
    class MockSession:
        id: UUID
        _telemetry: Optional[TelemetryManager] = None

    # Setup telemetry
    telemetry = TelemetryManager()
    config = OTELConfig(resource_attributes={"test.attribute": "demo"}, endpoint="http://localhost:4317")
    telemetry.initialize(config)

    # Create session
    session = MockSession(id=uuid4(), _telemetry=telemetry)

    # Create and start capture
    capture = LogCapture(session)
    capture.start()

    try:
        print("Regular stdout message")
        print("Multi-line stdout message\nwith a second line")
        sys.stderr.write("Error message to stderr\n")

        # Show that empty lines are ignored
        print("")
        print("\n\n")

        # Demonstrate concurrent output
        def background_prints():
            for i in range(3):
                time.sleep(0.5)
                print(f"Background message {i}")
                sys.stderr.write(f"Background error {i}\n")

        import threading

        thread = threading.Thread(target=background_prints)
        thread.start()

        # Main thread output
        for i in range(3):
            time.sleep(0.7)
            print(f"Main thread message {i}")

        thread.join()

    finally:
        # Stop capture and show normal output is restored
        capture.stop()
        telemetry.shutdown()
        print("\nCapture stopped - this prints normally to stdout")
        sys.stderr.write("This error goes normally to stderr\n")
