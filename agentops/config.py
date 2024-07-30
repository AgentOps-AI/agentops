from typing import List, Optional
from uuid import UUID

from .log_config import logger


class Configuration:
    def __init__(self):
        self.api_key: Optional[str] = None
        self.parent_key: Optional[str] = None
        self.endpoint: str = "https://api.agentops.ai"
        self.max_wait_time: int = 5000
        self.max_queue_size: int = 100
        self.default_tags: set[str] = set()
        self.instrument_llm_calls: bool = True
        self.auto_start_session: bool = True
        self.skip_auto_end_session: bool = False
        self.env_data_opt_out: bool = False

    def configure(
        self,
        client,
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
        if api_key is not None:
            try:
                UUID(api_key)
                self.api_key = api_key
            except ValueError:
                message = f"API Key is invalid: {{{api_key}}}.\n\t    Find your API key at https://app.agentops.ai/settings/projects"
                client.add_pre_init_warning(message)
                logger.error(message)

        if parent_key is not None:
            try:
                UUID(parent_key)
                self.parent_key = parent_key
            except ValueError:
                message = f"Parent Key is invalid: {parent_key}"
                client.add_pre_init_warning(message)
                logger.warning(message)

        if endpoint is not None:
            self.endpoint = endpoint

        if max_wait_time is not None:
            self.max_wait_time = max_wait_time

        if max_queue_size is not None:
            self.max_queue_size = max_queue_size

        if default_tags is not None:
            self.default_tags.update(default_tags)

        if instrument_llm_calls is not None:
            self.instrument_llm_calls = instrument_llm_calls

        if auto_start_session is not None:
            self.auto_start_session = auto_start_session

        if skip_auto_end_session is not None:
            self.skip_auto_end_session = skip_auto_end_session

        if env_data_opt_out is not None:
            self.env_data_opt_out = env_data_opt_out
