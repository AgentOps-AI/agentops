import logging

logger = logging.getLogger("agentops")
logger.setLevel(logging.CRITICAL)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('🖇 AgentOps: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)