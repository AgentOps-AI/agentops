from .log_config import logger


class MultiSessionException(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoSessionException(Exception):
    def __init__(self, message):
        super().__init__(message)


class ConfigurationError(Exception):
    """Exception raised for errors related to Configuration"""

    def __init__(self, message: str):
        super().__init__(message)
        logger.warning(message)
