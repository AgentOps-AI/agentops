from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass


@dataclass
class InstrumentorConfig:
    """Common configuration for all instrumentors."""

    enrich_assistant: bool = False
    enrich_token_usage: bool = False
    exception_logger: Optional[Callable] = None
    get_common_metrics_attributes: Optional[Callable[[], Dict[str, Any]]] = None
    upload_base64_image: Optional[Callable] = None
    enable_trace_context_propagation: bool = True

    def __post_init__(self):
        if self.get_common_metrics_attributes is None:
            self.get_common_metrics_attributes = lambda: {}


# Global config instance that can be shared
_global_config = InstrumentorConfig()


def get_config() -> InstrumentorConfig:
    """Get the global instrumentor configuration."""
    return _global_config


def set_config(config: InstrumentorConfig):
    """Set the global instrumentor configuration."""
    global _global_config
    _global_config = config
