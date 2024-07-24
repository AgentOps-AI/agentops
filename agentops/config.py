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
        env_data_opt_out: Optional[bool] = None
    ):
        self.api_key: Optional[str] = None
        self.parent_key: Optional[str] = None
        self.endpoint: str = endpoint or os.environ.get("AGENTOPS_API_ENDPOINT") or "https://api.agentops.ai"
        self.max_wait_time: int = max_wait_time or 5000
        self.max_queue_size: int = max_queue_size or 100
        self.default_tags: List[str] = default_tags or []
        self.instrument_llm_calls: bool = instrument_llm_calls or True
        self.auto_start_session: bool = auto_start_session or True
        self.skip_auto_end_session: bool = skip_auto_end_session or False
        self.env_data_opt_out: bool = env_data_opt_out or os.environ.get("AGENTOPS_ENV_DATA_OPT_OUT", "False").lower() == "true"

        p_api_key = api_key or os.environ.get("AGENTOPS_API_KEY")
        if p_api_key is not None:
            try:
                UUID(p_api_key)
                self.api_key = p_api_key
            except ValueError:
                logger.warning(f"API Key is invalid: {p_api_key}")

        p_parent_key = parent_key or os.environ.get("AGENTOPS_PARENT_KEY")
        if p_parent_key is not None:
            try:
                UUID(p_parent_key)
                self.parent_key = p_parent_key
            except ValueError:
                logger.warning(f"Parent Key is invalid: {p_parent_key}")
