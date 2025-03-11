import logging
import os
import sys
import inspect
import threading
from typing import Dict, Optional, Union, Any, Callable

from .formatters import AgentOpsLogFileFormatter, AgentOpsLogFormatter

# Create the logger at module level
logger = logging.getLogger("agentops")
logger.propagate = False
logger.setLevel(logging.CRITICAL)

# Thread-local storage for context information
_context = threading.local()

class IgnoreTracerProviderFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage() != 'Overriding of current TracerProvider is not allowed'

# Apply filter to suppress specific OpenTelemetry log messages
logging.getLogger('opentelemetry.trace').addFilter(IgnoreTracerProviderFilter())

def set_context(**kwargs):
    """Set context information for logging.
    
    Args:
        **kwargs: Key-value pairs to add to the logging context.
    """
    for key, value in kwargs.items():
        setattr(_context, key, value)

def get_context():
    """Get the current logging context.
    
    Returns:
        dict: The current logging context.
    """
    return {key: getattr(_context, key) for key in dir(_context) 
            if not key.startswith('_') and not callable(getattr(_context, key))}

def clear_context():
    """Clear the current logging context."""
    for key in list(dir(_context)):
        if not key.startswith('_') and not callable(getattr(_context, key)):
            delattr(_context, key)

def log_with_context(level: int, msg: str, *args, **kwargs):
    """Log a message with the current context.
    
    Args:
        level: Logging level.
        msg: Message to log.
        *args: Additional positional arguments for the logger.
        **kwargs: Additional keyword arguments for the logger.
    """
    # Get caller information
    frame = inspect.currentframe().f_back
    module = inspect.getmodule(frame)
    module_name = module.__name__ if module else "unknown"
    func_name = frame.f_code.co_name
    lineno = frame.f_lineno
    
    # Add context information
    context_info = get_context()
    if context_info:
        context_str = " ".join(f"{k}={v}" for k, v in context_info.items())
        msg = f"{msg} [{context_str}]"
    
    # Add source information
    source_info = f"[{module_name}.{func_name}:{lineno}]"
    msg = f"{msg} {source_info}"
    
    logger.log(level, msg, *args, **kwargs)

def debug(msg: str, *args, **kwargs):
    """Log a debug message with context."""
    log_with_context(logging.DEBUG, msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    """Log an info message with context."""
    log_with_context(logging.INFO, msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    """Log a warning message with context."""
    log_with_context(logging.WARNING, msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    """Log an error message with context."""
    log_with_context(logging.ERROR, msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    """Log a critical message with context."""
    log_with_context(logging.CRITICAL, msg, *args, **kwargs)

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
