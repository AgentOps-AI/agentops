import logging
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.resources import Resource

from agentops.instrumentation import get_log_handler, set_log_handler

if TYPE_CHECKING:
    from agentops.session import Session


@dataclass
class LogCapture:
    """Captures terminal output for a session using OpenTelemetry logging.

    Integrates with TelemetryManager to use consistent configuration and logging setup.
    If no telemetry manager is available, creates a standalone logging setup.

    Attributes:
        session_id
        stdout_line_count: Number of lines written to stdout
        stderr_line_count: Number of lines written to stderr
        log_level_counts: Count of log messages by level
        start_time: ISO timestamp when capture started
        end_time: ISO timestamp when capture stopped
        is_capturing: Whether capture is currently active
    """

    session_id: UUID
    stdout_line_count: int = field(default=0)
    stderr_line_count: int = field(default=0)
    log_level_counts: Dict[str, int] = field(
        default_factory=lambda: {"INFO": 0, "WARNING": 0, "ERROR": 0, "DEBUG": 0, "CRITICAL": 0}
    )
    start_time: Optional[str] = field(default=None)
    end_time: Optional[str] = field(default=None)
    is_capturing: bool = field(default=False)

    # Private implementation fields
    _stdout_logger: logging.Logger = field(init=False, repr=False)
    _stderr_logger: logging.Logger = field(init=False, repr=False)
    _stdout: Optional[object] = field(default=None, init=False, repr=False)
    _stderr: Optional[object] = field(default=None, init=False, repr=False)
    _handler: Optional[LoggingHandler] = field(default=None, init=False, repr=False)
    _logger_provider: Optional[LoggerProvider] = field(default=None, init=False, repr=False)
    _owns_handler: bool = field(default=False, init=False, repr=False)
    _session: Optional["Session"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Initialize loggers after dataclass initialization"""
        # Use unique logger names to avoid conflicts
        self._stdout_logger = logging.getLogger(f"agentops.stdout.{id(self)}")
        self._stderr_logger = logging.getLogger(f"agentops.stderr.{id(self)}")

        # Configure loggers to not propagate to parent loggers
        for logger in (self._stdout_logger, self._stderr_logger):
            logger.setLevel(logging.INFO)
            logger.propagate = False
            logger.handlers.clear()

    @property
    def session(self) -> Optional["Session"]:
        """Get the associated session instance"""
        if self._session is None:
            from agentops.session import get_active_sessions

            for session in get_active_sessions():
                if session.session_id == self.session_id:
                    self._session = session
                    break
        return self._session

    def start(self):
        """Start capturing output using OTEL logging handler"""
        if self._stdout is not None:
            return

        if not self.session:
            raise ValueError(f"No active session found with ID {self.session_id}")

        from agentops.helpers import get_ISO_time

        self.start_time = get_ISO_time()
        self.is_capturing = True

        # Try to get handler from telemetry manager
        get_log_handler()

        # Create our own handler if none exists
        if not self._handler:
            self._owns_handler = True

            # Use session's resource attributes if available
            resource_attrs = {"service.name": "agentops", "session.id": str(self.session_id)}

            # resource_attrs.update(config.resource_attributes)

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
            set_log_handler(self._handler)

        # Add handler to both loggers
        self._stdout_logger.addHandler(self._handler)
        self._stderr_logger.addHandler(self._handler)

        # Save original stdout/stderr
        self._stdout = sys.stdout
        self._stderr = sys.stderr

        # Replace with logging proxies
        sys.stdout = self._StdoutProxy(self)
        sys.stderr = self._StderrProxy(self)

    def stop(self):
        """Stop capturing output and restore stdout/stderr"""
        if self._stdout is None:
            return

        from agentops.helpers import get_ISO_time

        self.end_time = get_ISO_time()
        self.is_capturing = False

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
                    set_log_handler(None)

            self._handler = None
            self._logger_provider = None

    def flush(self):
        """Flush any buffered logs"""
        if self._handler:
            self._handler.flush()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the log capture statistics.

        Returns:
            Dict containing log capture metrics and metadata
        """
        return {
            "stdout_lines": self.stdout_line_count,
            "stderr_lines": self.stderr_line_count,
            "log_levels": self.log_level_counts,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self._calculate_duration() if self.start_time and self.end_time else None,
            "is_capturing": self.is_capturing,
        }

    def _calculate_duration(self) -> float:
        """Calculate duration of log capture in seconds"""
        from datetime import datetime

        start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
        return (end - start).total_seconds()

    def to_span_data(self) -> Dict[str, Any]:
        """Convert log capture data into span attributes.

        Returns:
            Dict of attributes suitable for OpenTelemetry spans/events
        """
        data = {
            "session.id": str(self.session_id),
            "log.stdout_count": self.stdout_line_count,
            "log.stderr_count": self.stderr_line_count,
            "log.start_time": self.start_time,
            "log.end_time": self.end_time,
            "log.is_capturing": self.is_capturing,
        }

        # Add log level counts with proper prefix
        for level, count in self.log_level_counts.items():
            data[f"log.level.{level.lower()}"] = count

        # Add duration if available
        if self.start_time and self.end_time:
            data["log.duration_seconds"] = self._calculate_duration()

        return data

    class _StdoutProxy:
        """Proxies stdout to logger"""

        def __init__(self, capture):
            self._capture = capture
            self._logger = capture._stdout_logger
            self._original_stdout = capture._stdout

        def write(self, text):
            if text.strip():  # Only log non-empty strings
                self._capture.stdout_line_count += 1
                self._capture.log_level_counts["INFO"] += 1
                # Get raw console output with ANSI codes
                raw_text = text if isinstance(text, str) else str(text)
                # Write to original stdout for display
                self._original_stdout.write(raw_text)
                # Log the raw text with ANSI codes preserved
                self._logger.info(raw_text, extra={"raw": True, "preserve_color": True})

        def flush(self):
            self._original_stdout.flush()

    class _StderrProxy:
        """Proxies stderr to logger"""

        def __init__(self, capture):
            self._capture = capture
            self._logger = capture._stderr_logger
            self._original_stderr = capture._stderr

        def write(self, text):
            if text.strip():  # Only log non-empty strings
                self._capture.stderr_line_count += 1
                self._capture.log_level_counts["ERROR"] += 1
                # Write to original stderr for display
                self._original_stderr.write(text)
                # Log the raw text with ANSI codes preserved
                self._logger.error(text, extra={"raw": True, "preserve_color": True})

        def flush(self):
            self._original_stderr.flush()


class SessionLogHandler(LoggingHandler):
    """A logging handler that captures logs for a specific session without altering output.
    
    This handler captures logs and associates them with a specific session, while allowing
    normal logging behavior to continue unaffected.
    """
    
    def __init__(self, session_id: UUID, logger_provider=None):
        super().__init__(level=logging.INFO, logger_provider=logger_provider)
        self.session_id = session_id
        self.log_counts: Dict[str, int] = {
            "INFO": 0,
            "WARNING": 0,
            "ERROR": 0,
            "DEBUG": 0,
            "CRITICAL": 0
        }
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record, capturing it for the session without altering normal output."""
        try:
            # Count the log by level
            self.log_counts[record.levelname] += 1
            
            # Create the log event with ANSI codes preserved
            msg = self.format(record)
            
            # Let the parent class handle sending to OTEL
            super().emit(record)
            
        except Exception:
            self.handleError(record)


def install_session_handler(session: "Session") -> Optional[SessionLogHandler]:
    """Install a logging handler for a specific session.
    
    Args:
        session: The session to install the handler for
        
    Returns:
        The installed handler, or None if installation failed
    """
    try:
        # Create handler with session's logger provider
        handler = SessionLogHandler(
            session_id=session.session_id,
            logger_provider=session._logger_provider
        )
        
        # Add handler to root logger to capture all logs
        logging.getLogger().addHandler(handler)
        
        return handler
        
    except Exception as e:
        logging.error(f"Failed to install session log handler: {e}")
        return None


def remove_session_handler(handler: SessionLogHandler) -> None:
    """Remove a session's logging handler.
    
    Args:
        handler: The handler to remove
    """
    try:
        logging.getLogger().removeHandler(handler)
    except Exception as e:
        logging.error(f"Failed to remove session log handler: {e}")


if __name__ == "__main__":
    import os
    import sys
    import time
    from dataclasses import dataclass
    from uuid import uuid4

    # Add parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from agentops.session import add_session  # Changed from relative import

    # Create a mock session with telemetry
    @dataclass
    class MockSession:
        session_id: UUID

    # Setup telemetry

    # Create session and add to registry
    session = MockSession(session_id=uuid4())
    add_session(session)  # Add session to registry so it can be found

    # Create and start capture
    capture = LogCapture(session_id=session.session_id)
    capture.start()
    try:
        # Test Rich formatting
        from rich.console import Console
        console = Console(force_terminal=True)
        rprint = console.print
        rprint("[red]This is red text[/red]")
        rprint("[blue]Blue[/blue] and [green]green[/green] mixed")
        rprint("[bold red]Bold red[/bold red] and [italic blue]italic blue[/italic blue]")
        
        # Test raw ANSI codes
        print("\033[31mDirect red ANSI\033[0m\n")
        print("\033[34mBlue\033[0m and \033[32mgreen\033[0m mixed ANSI\n")
        print("\033[1;31mBold red ANSI\033[0m\n")
        
        # Test stderr with colors
        sys.stderr.write("\033[35mMagenta error\033[0m\n")
        sys.stderr.write("\033[33mYellow warning\033[0m\n")

    finally:
        # Stop capture and show normal output is restored
        capture.stop()
        # print("\nCapture stopped - this prints normally to stdout")
        # sys.stderr.write("This error goes normally to stderr\n")
