import logging
import re
from .client import Client
from .event import Event


class AgentOpsLogger():
    """
    A utility class for creating loggers and handlers configured to work with the AgentOps service.

    This class provides two static methods for creating a logger or a handler that sends log 
    records to the AgentOps service. The logger and handler are configured with a specific 
    AgentOps client and name.

    Example Usage:

    >>> from agentops import Client
    >>> client = Client(...)
    >>> logger = AgentOpsLogger.get_agentops_logger(client, 'my_logger')
    >>> logger.info('This is an info log')

    This will send an 'info' log to the AgentOps service.
    """

    @staticmethod
    def get_agentops_logger(client: Client, name: str, level=logging.DEBUG):
        """
        Create and return a logger with an AgentOpsHandler.

        Args:
            client (Client): The AgentOps client to which the logs will be sent.
            name (str): The name for the logger and handler.
            level (int, optional): The minimum severity level to log. Defaults to logging.DEBUG.

        Returns:
            logging.Logger: A logger configured with an AgentOpsHandler.
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        handler = AgentOpsHandler(client, name)
        handler.setLevel(level)
        logger.addHandler(handler)
        return logger

    @staticmethod
    def get_agentops_handler(client: Client, name: str):
        """
        Create and return an AgentOpsHandler.

        Args:
            client (Client): The AgentOps client to which the logs will be sent.
            name (str): The name for the handler.

        Returns:
            AgentOpsHandler: A new AgentOpsHandler with the given client and name.
        """
        return AgentOpsHandler(client, name)


class AgentOpsHandler(logging.Handler):
    """
    Custom logging handler for sending logs to the AgentOps service.

    This handler extends the built-in logging.Handler class to send log records to AgentOps.
    It also removes ANSI color codes from log messages before sending them.
    """

    def __init__(self, client: Client, name: str):
        """
        Initialize the handler with a specific AgentOps client and name.

        Args:
            client (Client): The AgentOps client to which the logs will be sent.
            name (str): The name for this handler.
        """
        super().__init__()
        self.name = name
        self.client = client

    @staticmethod
    def remove_color_codes(s: str) -> str:
        """
        Remove ANSI color codes from a string.

        Args:
            s (str): The string from which color codes will be removed.

        Returns:
            The same string, but without any color codes.
        """
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", s)

    def emit(self, record):
        """
        Process a log record and send it to the AgentOps client.

        This method is called whenever a log record needs to be processed.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        log_entry = self.format(record)
        log_entry = self.remove_color_codes(log_entry)

        if record.levelno == logging.ERROR:
            result = "Fail"
        else:
            result = 'Indeterminate'

        self.client.record(
            Event(f'{self.name}:{record.levelname}', returns=log_entry, result=result))
