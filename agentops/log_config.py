import logging
import os
import re
import sys
import inspect

# Import loguru conditionally
try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False

# Get logging level from environment variable
logging_level = os.environ.get("AGENTOPS_LOGGING_LEVEL", "INFO")
LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
LOG_LEVEL = LEVEL_MAP.get(logging_level.upper(), logging.INFO)

class AgentOpsLogFormatter(logging.Formatter):
    blue = "\x1b[34m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    prefix = "🖇 AgentOps: "

    FORMATS = {
        logging.DEBUG: f"(DEBUG) {prefix}%(message)s",
        logging.INFO: f"{prefix}%(message)s",
        logging.WARNING: f"{prefix}%(message)s",
        logging.ERROR: f"{bold_red}{prefix}%(message)s{reset}",
        logging.CRITICAL: f"{bold_red}{prefix}%(message)s{reset}",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Setup loguru if available
if LOGURU_AVAILABLE:
    # Remove default handler
    loguru_logger.remove()
    
    # Configure loguru with our format including colors for different levels
    format_string = (
        "<green>🖇 AgentOps:</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    level_colors = {
        "TRACE": "<cyan>",
        "DEBUG": "<blue>",
        "INFO": "<green>",
        "SUCCESS": "<green>",
        "WARNING": "<yellow>",
        "ERROR": "<red>",
        "CRITICAL": "<red><bold>",
    }

    # Add custom colors to loguru levels
    for level_name, color in level_colors.items():
        loguru_logger.level(level_name, color=color)
    
    # Configure loguru with enhanced format
    loguru_logger.add(
        sys.stderr,
        format=format_string,
        level=logging_level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Create intercepting handler for AgentOps logging only
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Only handle AgentOps logs
            if not record.name.startswith('agentops'):
                return

            # Get corresponding Loguru level if it exists
            try:
                level = loguru_logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = inspect.currentframe(), 0
            while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
                frame = frame.f_back
                depth += 1

            loguru_logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Create our specific logger
    logger = logging.getLogger("agentops")
    logger.propagate = False
    logger.setLevel(LOG_LEVEL)  # Use environment variable level
    
    # Only handle AgentOps logs
    logger.addHandler(InterceptHandler())

else:
    # Fallback to standard logging setup
    logger = logging.getLogger("agentops")
    logger.propagate = False
    logger.setLevel(LOG_LEVEL)  # Use environment variable level

    # Streaming Handler  
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(LOG_LEVEL)  # Use environment variable level
    stream_handler.setFormatter(AgentOpsLogFormatter())
    logger.addHandler(stream_handler)

    # File Handler
    ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
    log_to_file = os.environ.get("AGENTOPS_LOGGING_TO_FILE", "True").lower() == "true"
    
    if log_to_file:
        class AgentOpsLogFileFormatter(logging.Formatter):
            def format(self, record):
                # Remove ANSI escape codes from the message
                record.msg = ANSI_ESCAPE_PATTERN.sub("", str(record.msg))
                return super().format(record)

        file_handler = logging.FileHandler("agentops.log", mode="w")
        file_handler.setLevel(LOG_LEVEL)  # Use environment variable level
        formatter = AgentOpsLogFileFormatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
