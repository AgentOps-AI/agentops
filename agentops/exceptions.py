from agentops.logging import logger


class MultiTraceException(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoTraceException(Exception):
    def __init__(self, message="No trace found"):
        super().__init__(message)


class MultiSessionException(Exception):
    """@deprecated Use MultiTraceException instead."""

    def __init__(self, message):
        super().__init__(message)


class NoSessionException(Exception):
    """@deprecated Use NoTraceException instead."""

    def __init__(self, message="No session found"):
        super().__init__(message)


class NoApiKeyException(Exception):
    def __init__(
        self,
        message="Could not initialize AgentOps client - API Key is missing."
        + "\n\t    Find your API key at https://app.agentops.ai/settings/projects",
    ):
        super().__init__(message)


class InvalidApiKeyException(Exception):
    def __init__(self, api_key, endpoint):
        message = f"API Key is invalid: {{{api_key}}}.\n\t    Find your API key at {endpoint}/settings/projects"
        super().__init__(message)


class ApiServerException(Exception):
    def __init__(self, message):
        super().__init__(message)


class AgentOpsClientNotInitializedException(RuntimeError):
    def __init__(self, message="AgentOps client must be initialized before using this feature"):
        super().__init__(message)


class AgentOpsApiJwtExpiredException(Exception):
    def __init__(self, message="JWT token has expired"):
        super().__init__(message)
