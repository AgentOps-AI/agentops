import logging
import os
import sys
from typing import Dict, Optional, Union

from .formatters import AgentOpsLogFileFormatter, AgentOpsLogFormatter

# Create the logger at module level
logger = logging.getLogger("agentops")
logger.propagate = False
logger.setLevel(logging.CRITICAL)

class IgnoreTracerProviderFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage() != 'Overriding of current TracerProvider is not allowed'

# Apply filter to suppress specific OpenTelemetry log messages
logging.getLogger('opentelemetry.trace').addFilter(IgnoreTracerProviderFilter())

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
