import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Set, TypedDict, Union
from uuid import UUID

from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter

from agentops.helpers.env import get_env_bool, get_env_int, get_env_list
from agentops.helpers.serialization import AgentOpsJSONEncoder


class ConfigDict(TypedDict):
    api_key: Optional[str]
    endpoint: Optional[str]
    app_url: Optional[str]
    max_wait_time: Optional[int]
    export_flush_interval: Optional[int]
    max_queue_size: Optional[int]
    default_tags: Optional[List[str]]
    trace_name: Optional[str]
    instrument_llm_calls: Optional[bool]
    auto_start_session: Optional[bool]
    auto_init: Optional[bool]
    skip_auto_end_session: Optional[bool]
    env_data_opt_out: Optional[bool]
    log_level: Optional[Union[str, int]]
    fail_safe: Optional[bool]
    prefetch_jwt_token: Optional[bool]
    log_session_replay_url: Optional[bool]


@dataclass
class Config:
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("AGENTOPS_API_KEY"),
        metadata={"description": "API key for authentication with AgentOps services"},
    )

    endpoint: str = field(
        default_factory=lambda: os.getenv("AGENTOPS_API_ENDPOINT", "https://api.agentops.ai"),
        metadata={"description": "Base URL for the AgentOps API"},
    )

    app_url: str = field(
        default_factory=lambda: os.getenv("AGENTOPS_APP_URL", "https://app.agentops.ai"),
        metadata={"description": "Dashboard URL for the AgentOps application"},
    )

    max_wait_time: int = field(
        default_factory=lambda: get_env_int("AGENTOPS_MAX_WAIT_TIME", 5000),
        metadata={"description": "Maximum time in milliseconds to wait for API responses"},
    )

    export_flush_interval: int = field(
        default_factory=lambda: get_env_int("AGENTOPS_EXPORT_FLUSH_INTERVAL", 1000),
        metadata={"description": "Time interval in milliseconds between automatic exports of telemetry data"},
    )

    max_queue_size: int = field(
        default_factory=lambda: get_env_int("AGENTOPS_MAX_QUEUE_SIZE", 512),
        metadata={"description": "Maximum number of events to queue before forcing a flush"},
    )

    default_tags: Set[str] = field(
        default_factory=lambda: get_env_list("AGENTOPS_DEFAULT_TAGS"),
        metadata={"description": "Default tags to apply to all sessions"},
    )

    trace_name: Optional[str] = field(
        default_factory=lambda: os.getenv("AGENTOPS_TRACE_NAME"),
        metadata={"description": "Default name for the trace/session"},
    )

    instrument_llm_calls: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_INSTRUMENT_LLM_CALLS", True),
        metadata={"description": "Whether to automatically instrument and track LLM API calls"},
    )

    auto_start_session: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_AUTO_START_SESSION", True),
        metadata={"description": "Whether to automatically start a session when initializing"},
    )

    auto_init: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_AUTO_INIT", True),
        metadata={"description": "Whether to automatically initialize the client on import"},
    )

    skip_auto_end_session: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_SKIP_AUTO_END_SESSION", False),
        metadata={"description": "Whether to skip automatically ending sessions on program exit"},
    )

    env_data_opt_out: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_ENV_DATA_OPT_OUT", False),
        metadata={"description": "Whether to opt out of collecting environment data"},
    )

    log_level: Union[str, int] = field(
        default_factory=lambda: os.getenv("AGENTOPS_LOG_LEVEL", "INFO"),
        metadata={"description": "Logging level for AgentOps logs"},
    )

    fail_safe: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_FAIL_SAFE", False),
        metadata={"description": "Whether to suppress errors and continue execution when possible"},
    )

    prefetch_jwt_token: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_PREFETCH_JWT_TOKEN", True),
        metadata={"description": "Whether to prefetch JWT token during initialization"},
    )

    log_session_replay_url: bool = field(
        default_factory=lambda: get_env_bool("AGENTOPS_LOG_SESSION_REPLAY_URL", True),
        metadata={"description": "Whether to log session replay URLs to the console"},
    )

    exporter_endpoint: Optional[str] = field(
        default_factory=lambda: os.getenv("AGENTOPS_EXPORTER_ENDPOINT", "https://otlp.agentops.ai/v1/traces"),
        metadata={
            "description": "Endpoint for the span exporter. When not provided, the default AgentOps endpoint will be used."
        },
    )

    exporter: Optional[SpanExporter] = field(
        default_factory=lambda: None, metadata={"description": "Custom span exporter for OpenTelemetry trace data"}
    )

    processor: Optional[SpanProcessor] = field(
        default_factory=lambda: None, metadata={"description": "Custom span processor for OpenTelemetry trace data"}
    )

    def configure(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        app_url: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        export_flush_interval: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: Optional[List[str]] = None,
        trace_name: Optional[str] = None,
        instrument_llm_calls: Optional[bool] = None,
        auto_start_session: Optional[bool] = None,
        auto_init: Optional[bool] = None,
        skip_auto_end_session: Optional[bool] = None,
        env_data_opt_out: Optional[bool] = None,
        log_level: Optional[Union[str, int]] = None,
        fail_safe: Optional[bool] = None,
        prefetch_jwt_token: Optional[bool] = None,
        log_session_replay_url: Optional[bool] = None,
        exporter: Optional[SpanExporter] = None,
        processor: Optional[SpanProcessor] = None,
        exporter_endpoint: Optional[str] = None,
    ):
        """Configure settings from kwargs, validating where necessary"""
        if api_key is not None:
            self.api_key = api_key
            if not TESTING:  # Allow setting dummy keys in tests
                try:
                    UUID(api_key)
                except ValueError:
                    # Log warning but don't throw exception - let async auth handle it
                    from agentops.logging import logger

                    logger.warning(
                        f"API key format appears invalid: {api_key[:8]}... "
                        f"Authentication may fail. Find your API key at {self.endpoint}/settings/projects"
                    )
                    # Continue with the invalid key - async auth will handle the failure gracefully

        if endpoint is not None:
            self.endpoint = endpoint

        if app_url is not None:
            self.app_url = app_url

        if max_wait_time is not None:
            self.max_wait_time = max_wait_time

        if export_flush_interval is not None:
            self.export_flush_interval = export_flush_interval

        if max_queue_size is not None:
            self.max_queue_size = max_queue_size

        if default_tags is not None:
            self.default_tags = set(default_tags)

        if trace_name is not None:
            self.trace_name = trace_name

        if instrument_llm_calls is not None:
            self.instrument_llm_calls = instrument_llm_calls

        if auto_start_session is not None:
            self.auto_start_session = auto_start_session

        if auto_init is not None:
            self.auto_init = auto_init

        if skip_auto_end_session is not None:
            self.skip_auto_end_session = skip_auto_end_session

        if env_data_opt_out is not None:
            self.env_data_opt_out = env_data_opt_out

        if log_level is not None:
            if isinstance(log_level, str):
                log_level_str = log_level.upper()
                if hasattr(logging, log_level_str):
                    self.log_level = getattr(logging, log_level_str)
                else:
                    self.log_level = logging.INFO
            else:
                self.log_level = log_level

        if fail_safe is not None:
            self.fail_safe = fail_safe

        if prefetch_jwt_token is not None:
            self.prefetch_jwt_token = prefetch_jwt_token

        if log_session_replay_url is not None:
            self.log_session_replay_url = log_session_replay_url

        if exporter is not None:
            self.exporter = exporter

        if processor is not None:
            self.processor = processor

        if exporter_endpoint is not None:
            self.exporter_endpoint = exporter_endpoint
        # else:
        #     self.exporter_endpoint = self.endpoint

    def dict(self):
        """Return a dictionary representation of the config"""
        return {
            "api_key": self.api_key,
            "endpoint": self.endpoint,
            "app_url": self.app_url,
            "max_wait_time": self.max_wait_time,
            "export_flush_interval": self.export_flush_interval,
            "max_queue_size": self.max_queue_size,
            "default_tags": self.default_tags,
            "trace_name": self.trace_name,
            "instrument_llm_calls": self.instrument_llm_calls,
            "auto_start_session": self.auto_start_session,
            "auto_init": self.auto_init,
            "skip_auto_end_session": self.skip_auto_end_session,
            "env_data_opt_out": self.env_data_opt_out,
            "log_level": self.log_level,
            "fail_safe": self.fail_safe,
            "prefetch_jwt_token": self.prefetch_jwt_token,
            "log_session_replay_url": self.log_session_replay_url,
            "exporter": self.exporter,
            "processor": self.processor,
            "exporter_endpoint": self.exporter_endpoint,
        }

    def json(self):
        """Return a JSON representation of the config"""
        return json.dumps(self.dict(), cls=AgentOpsJSONEncoder)


# checks if pytest is imported
TESTING = "pytest" in sys.modules
