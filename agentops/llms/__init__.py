import functools
import sys
from importlib import import_module
from importlib.metadata import version

from packaging.version import Version, parse

from ..log_config import logger

from .cohere import CohereProvider
from .groq import GroqProvider
from .litellm import LiteLLMProvider
from .ollama import OllamaProvider
from .openai import OpenAiProvider
from .anthropic import AnthropicProvider

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
        "anthropic": {
            "0.32.0": ("completions.create",),
        },
    }

    def __init__(self, client):
        self.client = client

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
                        provider = LiteLLMProvider(self.client)
                        provider.override()
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
                            provider = OpenAiProvider(self.client)
                            provider.override()
                        else:
                            raise DeprecationWarning(
                                "OpenAI versions < 0.1 are no longer supported by AgentOps. Please upgrade OpenAI or "
                                "downgrade AgentOps to <=0.3.8."
                            )

                if api == "cohere":
                    # Patch cohere v5.4.0+ methods
                    module_version = version(api)
                    if module_version is None:
                        logger.warning(
                            f"Cannot determine Cohere version. Only Cohere>=5.4.0 supported."
                        )

                    if Version(module_version) >= parse("5.4.0"):
                        provider = CohereProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(
                            f"Only Cohere>=5.4.0 supported. v{module_version} found."
                        )

                if api == "ollama":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.0.1"):
                        provider = OllamaProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(
                            f"Only Ollama>=0.0.1 supported. v{module_version} found."
                        )

                if api == "groq":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.9.0"):
                        provider = GroqProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(
                            f"Only Groq>=0.9.0 supported. v{module_version} found."
                        )

                if api == "anthropic":
                    module_version = version(api)

                    if module_version is None:
                        logger.warning(
                            f"Cannot determine Anthropic version. Only Anthropic>=0.32.0 supported."
                        )

                    if Version(module_version) >= parse("0.32.0"):
                        provider = AnthropicProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(
                            f"Only Anthropic>=0.32.0 supported. v{module_version} found."
                        )

    def stop_instrumenting(self):
        OpenAiProvider(self.client).undo_override()
        GroqProvider(self.client).undo_override()
        CohereProvider(self.client).undo_override()
        LiteLLMProvider(self.client).undo_override()
        OllamaProvider(self.client).undo_override()
        AnthropicProvider(self.client).undo_override()
