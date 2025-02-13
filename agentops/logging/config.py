import logging
import os
from .formatters import AgentOpsLogFormatter, AgentOpsLogFileFormatter

def configure_logging():
    """Configure the AgentOps logger with console and optional file handlers."""
    logger = logging.getLogger("agentops")
    logger.propagate = False
    logger.setLevel(logging.CRITICAL)

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