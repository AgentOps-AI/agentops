import logging


class AgentOpsFormatter(logging.Formatter):
    blue = "\x1b[34m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "🖇 AgentOps: %(message)s"

    FORMATS = {
        logging.DEBUG: "(DEBUG) " + format,
        logging.INFO: format,
        logging.WARNING: format,
        logging.ERROR: format,
        logging.CRITICAL: bold_red + format + reset,
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
