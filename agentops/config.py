from dataclasses import dataclass, field
from typing import Optional, Set
from uuid import UUID

from .log_config import logger

# TODO: Use annotations to clarify the purpose of each attribute.
# Details are defined in a docstrings found in __init__.py, but
# it's good to have those right on the fields at class definition


@dataclass
class Configuration:
    api_key: Optional[str] = None
    parent_key: Optional[str] = None
    endpoint: str = "https://api.agentops.ai"
    max_wait_time: int = 5000
    max_queue_size: int = 512
    default_tags: Set[str] = field(default_factory=set)
    instrument_llm_calls: bool = True
    auto_start_session: bool = True
    skip_auto_end_session: bool = False
    env_data_opt_out: bool = False

    def configure(self, client, **kwargs):
        # Special handling for keys that need UUID validation
        for key_name in ["api_key", "parent_key"]:
            if key_name in kwargs and kwargs[key_name] is not None:
                try:
                    UUID(kwargs[key_name])
                    setattr(self, key_name, kwargs[key_name])
                except ValueError:
                    message = (
                        f"API Key is invalid: {{{kwargs[key_name]}}}.\n\t    Find your API key at https://app.agentops.ai/settings/projects"
                        if key_name == "api_key"
                        else f"Parent Key is invalid: {kwargs[key_name]}"
                    )
                    client.add_pre_init_warning(message)
                    logger.error(message) if key_name == "api_key" else logger.warning(message)
                kwargs.pop(key_name)

        # Special handling for default_tags which needs update() instead of assignment
        if "default_tags" in kwargs and kwargs["default_tags"] is not None:
            self.default_tags.update(kwargs.pop("default_tags"))

        # Handle all other attributes
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)
