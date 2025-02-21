from .config import logger, configure_logging

# Create and configure the logger
logger = configure_logging()

__all__ = ['logger', 'configure_logging'] 