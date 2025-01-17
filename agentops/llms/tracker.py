import sys
from importlib import import_module
from importlib.metadata import version

from packaging.version import Version, parse

from ..log_config import logger

from .providers.cohere import CohereProvider
from .providers.groq import GroqProvider
from .providers.litellm import LiteLLMProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAiProvider
from .providers.anthropic import AnthropicProvider
from .providers.mistral import MistralProvider
from .providers.ai21 import AI21Provider
from .providers.llama_stack_client import LlamaStackClientProvider
from .providers.taskweaver import TaskWeaverProvider
from .providers.gemini import GeminiProvider

original_func = {}
original_create = None
original_create_async = None


class LlmTracker:
    SUPPORTED_APIS = {
        "google.generativeai": {
            "0.1.0": ("GenerativeModel.generate_content", "GenerativeModel.generate_content_stream"),
        },
        "litellm": {"1.3.1": ("openai_chat_completions.completion",)},
        "openai": {
            "1.0.0": (
                "chat.completions.create",
                # Assistants
                "beta.assistants.create",
                "beta.assistants.retrieve",
                "beta.assistants.update",
                "beta.assistants.delete",
                "beta.assistants.list",
                "beta.assistants.files.create",
                "beta.assistants.files.retrieve",
                "beta.assistants.files.delete",
                "beta.assistants.files.list",
                # Threads
                "beta.threads.create",
                "beta.threads.retrieve",
                "beta.threads.update",
                "beta.threads.delete",
                # Messages
                "beta.threads.messages.create",
                "beta.threads.messages.retrieve",
                "beta.threads.messages.update",
                "beta.threads.messages.list",
                "beta.threads.messages.files.retrieve",
                "beta.threads.messages.files.list",
                # Runs
                "beta.threads.runs.create",
                "beta.threads.runs.retrieve",
                "beta.threads.runs.update",
                "beta.threads.runs.list",
                "beta.threads.runs.cancel",
                "beta.threads.runs.submit_tool_outputs",
                # Run Steps
                "beta.threads.runs.steps.Steps.retrieve",
                "beta.threads.runs.steps.Steps.list",
            ),
            "0.0.0": (
                "ChatCompletion.create",
                "ChatCompletion.acreate",
            ),
        },
        "cohere": {
            "5.4.0": ("chat", "chat_stream"),
        },
        "ollama": {"0.0.1": ("chat", "Client.chat", "AsyncClient.chat")},
        "llama_stack_client": {
            "0.0.53": ("resources.InferenceResource.chat_completion", "lib.agents.agent.Agent.create_turn"),
        },
        "groq": {
            "0.9.0": ("Client.chat", "AsyncClient.chat"),
        },
        "anthropic": {
            "0.32.0": ("completions.create",),
        },
        "mistralai": {
            "1.0.1": ("chat.complete", "chat.stream"),
        },
        "ai21": {
            "2.0.0": (
                "chat.completions.create",
                "client.answer.create",
            ),
        },
        "taskweaver": {
            "0.0.1": ("chat_completion", "chat_completion_stream"),
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
                        logger.warning("Cannot determine LiteLLM version. Only LiteLLM>=1.3.1 supported.")

                    if Version(module_version) >= parse("1.3.1"):
                        provider = LiteLLMProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only LiteLLM>=1.3.1 supported. v{module_version} found.")
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
                        logger.warning("Cannot determine Cohere version. Only Cohere>=5.4.0 supported.")

                    if Version(module_version) >= parse("5.4.0"):
                        provider = CohereProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only Cohere>=5.4.0 supported. v{module_version} found.")

                if api == "ollama":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.0.1"):
                        provider = OllamaProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only Ollama>=0.0.1 supported. v{module_version} found.")

                if api == "groq":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.9.0"):
                        provider = GroqProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only Groq>=0.9.0 supported. v{module_version} found.")

                if api == "anthropic":
                    module_version = version(api)

                    if module_version is None:
                        logger.warning("Cannot determine Anthropic version. Only Anthropic>=0.32.0 supported.")

                    if Version(module_version) >= parse("0.32.0"):
                        provider = AnthropicProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only Anthropic>=0.32.0 supported. v{module_version} found.")

                if api == "mistralai":
                    module_version = version(api)

                    if Version(module_version) >= parse("1.0.1"):
                        provider = MistralProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only MistralAI>=1.0.1 supported. v{module_version} found.")

                if api == "ai21":
                    module_version = version(api)

                    if module_version is None:
                        logger.warning("Cannot determine AI21 version. Only AI21>=2.0.0 supported.")

                    if Version(module_version) >= parse("2.0.0"):
                        provider = AI21Provider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only AI21>=2.0.0 supported. v{module_version} found.")

                if api == "llama_stack_client":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.0.53"):
                        provider = LlamaStackClientProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only LlamaStackClient>=0.0.53 supported. v{module_version} found.")

                if api == "taskweaver":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.0.1"):
                        provider = TaskWeaverProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only TaskWeaver>=0.0.1 supported. v{module_version} found.")

                if api == "google.generativeai":
                    module_version = version(api)

                    if Version(module_version) >= parse("0.1.0"):
                        provider = GeminiProvider(self.client)
                        provider.override()
                    else:
                        logger.warning(f"Only google.generativeai>=0.1.0 supported. v{module_version} found.")

    def stop_instrumenting(self):
        OpenAiProvider(self.client).undo_override()
        GroqProvider(self.client).undo_override()
        CohereProvider(self.client).undo_override()
        LiteLLMProvider(self.client).undo_override()
        OllamaProvider(self.client).undo_override()
        AnthropicProvider(self.client).undo_override()
        MistralProvider(self.client).undo_override()
        AI21Provider(self.client).undo_override()
        LlamaStackClientProvider(self.client).undo_override()
        TaskWeaverProvider(self.client).undo_override()
        GeminiProvider(self.client).undo_override()
