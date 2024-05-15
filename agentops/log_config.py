import logging

logger = logging.getLogger("agentops")
logger.setLevel(logging.CRITICAL)

def set_logging_level(level):
    logger.setLevel(level)

def set_logging_level_critial():
    logger.setLevel(logging.CRITICAL)

def set_logging_level_info():
    logger.setLevel(logging.INFO)
    
def set_logging_level_debug():
    logger.setLevel(logging.DEBUG)
