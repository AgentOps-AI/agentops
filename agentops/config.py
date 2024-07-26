import os
from typing import List, Optional
from uuid import UUID

from .log_config import logger


class Configuration:
    def __init__(
        self,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: Optional[List[str]] = None,
        instrument_llm_calls: Optional[bool] = None,
        auto_start_session: Optional[bool] = None,
        skip_auto_end_session: Optional[bool] = None,
        env_data_opt_out: Optional[bool] = None,
    ):

        api_key = api_key or os.environ.get("AGENTOPS_API_KEY")
        if api_key is not None:
            try:
                UUID(api_key)
                self.api_key = api_key
            except ValueError:
                logger.warning(f"API Key is invalid: {api_key}")

        parent_key = parent_key or os.environ.get("AGENTOPS_PARENT_KEY")
        if parent_key is not None:
            try:
                UUID(parent_key)
                self.parent_key = parent_key
            except ValueError:
                logger.warning(f"Parent Key is invalid: {parent_key}")

        if isinstance(default_tags, str):
            default_tags = [default_tags]
        if not isinstance(default_tags, list):
            logger.warning(
                "default_tags is not a list - default tags will be not set. Please pass a List to default_tags"
            )

        if default_tags is None:
            default_tags = []

        self.api_key: Optional[str] = api_key
        self.parent_key: Optional[str] = parent_key
        self.endpoint: str = (
            endpoint
            or os.environ.get("AGENTOPS_API_ENDPOINT")
            or "https://api.agentops.ai"
        )
        self.max_wait_time: int = max_wait_time or 5000
        self.max_queue_size: int = max_queue_size or 100
        self.default_tags: set[str] = set(default_tags)
        self.instrument_llm_calls: bool = instrument_llm_calls or True
        self.auto_start_session: bool = auto_start_session or True
        self.skip_auto_end_session: bool = skip_auto_end_session or False
        self.env_data_opt_out: bool = (
            env_data_opt_out
            or os.environ.get("AGENTOPS_ENV_DATA_OPT_OUT", "False").lower() == "true"
        )
