import logging

logger = logging.getLogger("agentops")
logger.setLevel(logging.CRITICAL)

def set_logging_level_critial():
    logger.setLevel(logging.CRITICAL)

def set_logging_level_info():
    logger.setLevel(logging.INFO)