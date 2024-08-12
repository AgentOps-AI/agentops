import functools
import sys
from importlib import import_module
from importlib.metadata import version

from packaging.version import Version, parse

from ..log_config import logger
from ..event import LLMEvent
from ..helpers import get_ISO_time
import inspect
from typing import Optional

from .cohere import override_cohere_chat, override_cohere_chat_stream
from .groq import override_groq_chat, override_groq_chat_stream
from .litellm import override_litellm_completion, override_litellm_async_completion
from .ollama import (
    override_ollama_chat,
    override_ollama_chat_client,
    override_ollama_chat_async_client,
    undo_override_ollama,
)
from .openai import (
    override_openai_v1_completion,
    override_openai_v1_async_completion,
    handle_response_v0_openai,
    undo_override_openai_v1_async_completion,
    undo_override_openai_v1_completion,
)

original_func = {}
original_create = None
original_create_async = None


class LlmTracker:
    SUPPORTED_APIS = {
        "litellm": {"1.3.1": ("openai_chat_completions.completion",)},
        "openai": {
            "1.0.0": ("chat.completions.create",),
            "0.0.0": (
                "ChatCompletion.create",
                "ChatCompletion.acreate",
            ),
        },
        "cohere": {
            "5.4.0": ("chat", "chat_stream"),
        },
        "ollama": {"0.0.1": ("chat", "Client.chat", "AsyncClient.chat")},
        "groq": {
            "0.9.0": ("Client.chat", "AsyncClient.chat"),
        },
    }

    def __init__(self, client):
        self.client = client
        self.completion = ""
        self.llm_event: Optional[LLMEvent] = None

    def _override_method(self, api, method_path, module):
        def handle_response(result, kwargs, init_timestamp):
            if api == "openai":
                return handle_response_v0_openai(self, result, kwargs, init_timestamp)
            return result

        def wrap_method(original_method):
            if inspect.iscoroutinefunction(original_method):

                @functools.wraps(original_method)
                async def async_method(*args, **kwargs):
                    init_timestamp = get_ISO_time()
                    response = await original_method(*args, **kwargs)
                    return handle_response(response, kwargs, init_timestamp)

                return async_method

            else:

                @functools.wraps(original_method)
                def sync_method(*args, **kwargs):
                    init_timestamp = get_ISO_time()
                    response = original_method(*args, **kwargs)
                    return handle_response(response, kwargs, init_timestamp)

                return sync_method

        method_parts = method_path.split(".")
        original_method = functools.reduce(getattr, method_parts, module)
        new_method = wrap_method(original_method)

        if len(method_parts) == 1:
            setattr(module, method_parts[0], new_method)
        else:
            parent = functools.reduce(getattr, method_parts[:-1], module)
            setattr(parent, method_parts[-1], new_method)

    def override_api(self):
        """
        Overrides key methods of the specified API to record events.
        """

        for api in self.SUPPORTED_APIS:
            if api in sys.modules:
                module = import_module(api)
                if api == "litellm":
                    module_version = version(api)
                    if module_version is None:
                        logger.warning(
                            f"Cannot determine LiteLLM version. Only LiteLLM>=1.3.1 supported."
                        )

                    if Version(module_version) >= parse("1.3.1"):
                        override_litellm_completion(self)
                        override_litellm_async_completion(self)
                    else:
                        logger.warning(
                            f"Only LiteLLM>=1.3.1 supported. v{module_version} found."
                        )
                    return  # If using an abstraction like litellm, do not patch the underlying LLM APIs

                if api == "openai":
                    # Patch openai v1.0.0+ methods
                    if hasattr(module, "__version__"):
                        module_version = parse(module.__version__)
                        if module_version >= parse("1.0.0"):
                            override_openai_v1_completion(self)
                            override_openai_v1_async_completion(self)
                        else:
                            # Patch openai <v1.0.0 methods
                            for method_path in self.SUPPORTED_APIS["openai"]["0.0.0"]:
                                self._override_method(api, method_path, module)

                if api == "cohere":
                    # Patch cohere v5.4.0+ methods
                    module_version = version(api)
                    if module_version is None:
                        logger.warning(
                            f"Cannot determine Cohere version. Only Cohere>=5.4.0 supported."
                        )

                    if Version(module_version) >= parse("5.4.0"):
                        override_cohere_chat(self)
                        override_cohere_chat_stream(self)
                    else:
                        logger.warning(
                            f"Only Cohere>=5.4.0 supported. v{module_version} found."
                        )

                if api == "ollama":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.0.1"):
                        override_ollama_chat(self)
                        override_ollama_chat_client(self)
                        override_ollama_chat_async_client(self)
                    else:
                        logger.warning(
                            f"Only Ollama>=0.0.1 supported. v{module_version} found."
                        )

                if api == "groq":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.9.0"):
                        override_groq_chat(self)
                        override_groq_chat_stream(self)
                    else:
                        logger.warning(
                            f"Only Groq>=0.9.0 supported. v{module_version} found."
                        )

    def stop_instrumenting(self):
        undo_override_openai_v1_async_completion()
        undo_override_openai_v1_completion()
        undo_override_ollama(self)
