import logging
import os
import re
from sys import prefix


class AgentOpsFormatter(logging.Formatter):
    blue = "\x1b[34m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    prefix = "🖇 AgentOps: %(message)s"

    FORMATS = {
        logging.DEBUG: f"(DEBUG) {prefix}",
        logging.INFO: f"{prefix}",
        logging.WARNING: f"{prefix}",
        logging.ERROR: f"{bold_red}{prefix}{reset}",
        logging.CRITICAL: f"{bold_red}{prefix}{reset}",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger("agentops")
logger.propagate = False
logger.setLevel(logging.CRITICAL)

# Streaming Handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(AgentOpsFormatter())
logger.addHandler(stream_handler)


# File Handler
class ScrubColorFormatter(logging.Formatter):
    def format(self, record):
        # Remove ANSI escape codes from the message
        record.msg = ANSI_ESCAPE_PATTERN.sub("", record.msg)
        return super().format(record)


ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
log_to_file = os.environ.get("AGENTOPS_LOGGING_TO_FILE", "True").lower() == "true"
if log_to_file:
    file_handler = logging.FileHandler("agentops.log", mode="w")
    file_handler.setLevel(logging.DEBUG)
    formatter = ScrubColorFormatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# for handler in logger.handlers:
#     print(f"Handler: {handler}")
#     print(f"  - Level: {handler.level}")
#     print(f"  - Formatter: {handler.formatter}")
#     print(f"  - Handler Type: {type(handler).__name__}")
