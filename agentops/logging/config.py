import logging
import os
import sys
from typing import Dict, Optional, Union

from .formatters import AgentOpsLogFileFormatter, AgentOpsLogFormatter

# Create the logger at module level
logger = logging.getLogger("agentops")
logger.propagate = False
logger.setLevel(logging.CRITICAL)


def configure_logging(config=None):  # Remove type hint temporarily to avoid circular import
    """Configure the AgentOps logger with console and optional file handlers.

    Args:
        config: Optional Config instance. If not provided, a new Config instance will be created.
    """
    # Defer the Config import to avoid circular dependency
    if config is None:
        from agentops.config import Config

        config = Config()

    # Use env var as override if present, otherwise use config
    log_level_env = os.environ.get("AGENTOPS_LOG_LEVEL", "").upper()
    if log_level_env and hasattr(logging, log_level_env):
        log_level = getattr(logging, log_level_env)
    else:
        log_level = config.log_level if isinstance(config.log_level, int) else logging.CRITICAL

    logger.setLevel(log_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Configure console logging
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(AgentOpsLogFormatter())
    logger.addHandler(stream_handler)

    # Configure file logging if enabled
    log_to_file = os.environ.get("AGENTOPS_LOGGING_TO_FILE", "True").lower() == "true"
    if log_to_file:
        file_handler = logging.FileHandler("agentops.log", mode="w")
        file_handler.setLevel(logging.DEBUG)
        formatter = AgentOpsLogFileFormatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def intercept_opentelemetry_logging():
    """
    Configure OpenTelemetry logging to redirect all messages to the AgentOps logger.
    All OpenTelemetry logs will be prefixed with [opentelemetry.X] and set to DEBUG level.
    """
    prefix = "opentelemetry"
    otel_root_logger = logging.getLogger(prefix)
    otel_root_logger.propagate = False
    otel_root_logger.setLevel(logging.DEBUG)  # capture all

    for handler in otel_root_logger.handlers[:]:
        otel_root_logger.removeHandler(handler)

    # Create a handler that forwards all messages to the AgentOps logger
    class OtelLogHandler(logging.Handler):
        def emit(self, record):
            if record.name.startswith(f"{prefix}."):
                module_name = record.name.replace(f"{prefix}.", "", 1)
            else:
                module_name = record.name
            message = f"[{prefix}.{module_name}] {record.getMessage()}"
            logger.debug(message)

    otel_root_logger.addHandler(OtelLogHandler())
