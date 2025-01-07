import logging
from typing import Optional

from opentelemetry._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs import LoggerProvider as SDKLoggerProvider
from opentelemetry.sdk._logs import LoggingHandler as _LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.trace import get_current_span
from opentelemetry.util.types import Attributes


class LoggingHandler(_LoggingHandler):
    """
    Custom log handler that integrates with OpenTelemetry
    """

    def __init__(
        self,
        level: int = logging.NOTSET,
        logger_provider: Optional[LoggerProvider] = None,
    ):
        super().__init__(level, logger_provider)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record with trace context"""
        try:
            # Get current span context
            span = get_current_span()
            trace_id = span.get_span_context().trace_id if span else None
            span_id = span.get_span_context().span_id if span else None

            # Create OTEL log record
            log_data = {
                "timestamp": int(record.created * 1e9),  # Convert to nanoseconds
                "severity_text": record.levelname,
                "severity_number": record.levelno,
                "body": record.getMessage(),
                "attributes": {
                    "logger.name": record.name,
                    "logger.thread_name": record.threadName,
                    "logger.file.name": record.filename,
                    "logger.file.line": record.lineno,
                    "logger.file.path": record.pathname,
                },
            }

            # Add trace context if available
            if trace_id:
                log_data["attributes"]["trace_id"] = format(trace_id, "032x")
            if span_id:
                log_data["attributes"]["span_id"] = format(span_id, "016x")

            # Create and emit OTEL log record
            otel_record = LogRecord(**log_data)
            self._logger.emit(otel_record)

        except Exception as e:
            # Fallback to standard logging if OTEL emission fails
            super().emit(record)

    @staticmethod
    def setup(service_name: str) -> SDKLoggerProvider:
        """Setup logging with OTEL integration"""
        # Create logger provider
        logger_provider = SDKLoggerProvider()

        # Add console exporter for development
        console_exporter = ConsoleLogExporter()
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(console_exporter))

        # Create and configure handler
        handler = LoggingHandler(
            level=logging.INFO,
            logger_provider=logger_provider,
        )

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        return logger_provider

def set_log_handler(handler: logging.Handler, logger_name: str = "agentops") -> None:
    """
    Configure an AgentOps-specific logger with the provided handler.
    
    Args:
        handler: The logging handler to set
        logger_name: The name of the logger to configure (defaults to "agentops")
    """
    # Get AgentOps-specific logger instead of root logger
    logger = logging.getLogger(logger_name)
    logger.propagate = False  # Prevent duplicate logging
    
    # Remove existing handlers of the same type to avoid duplicates
    for existing_handler in logger.handlers[:]:
        if isinstance(existing_handler, type(handler)):
            logger.removeHandler(existing_handler)
        
    # Add the new handler
    logger.addHandler(handler)
    
    # Only set level if not already set
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)
