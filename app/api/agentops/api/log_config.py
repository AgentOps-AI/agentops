import logging
import os

# Simple logging configuration
log_levels = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def setup_logger(name: str = "AgentOpsAPI") -> logging.Logger:
    """Set up and configure a logger with the specified name."""
    logging_level: str = os.environ.get("LOGGING_LEVEL", "INFO")
    level = log_levels.get(logging_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Clear existing handlers to avoid duplicates when reloading in dev
    if logger.handlers:
        logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


# Create the main application logger
logger = setup_logger()
