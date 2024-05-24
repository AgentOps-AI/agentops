import logging
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
logger.setLevel(logging.CRITICAL)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(AgentOpsFormatter())
logger.addHandler(handler)
