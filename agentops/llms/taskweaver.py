from typing import Optional
import pprint
from agentops.llms.base import InstrumentedProvider
from agentops.events import LLMEvent, ErrorEvent
from agentops.session import Session
from agentops.utils import get_ISO_time, check_call_stack_for_agent_id
from agentops.decorators import singleton


@singleton
class TaskWeaverProvider(InstrumentedProvider):
    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "TaskWeaver"
        self.original_completion = {}
        self.original_completion_async = {}

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None):
        llm_event = LLMEvent(
            provider=self._provider_name,
            init_timestamp=init_timestamp,
            returns=response
        )

        try:
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs.get("model", "unknown")
            llm_event.prompt = kwargs.get("messages", [])
            
            if hasattr(response, "choices") and len(response.choices) > 0:
                choice = response.choices[0]
                llm_event.completion = {
                    "role": choice.message.role if hasattr(choice.message, "role") else "assistant",
                    "content": choice.message.content,
                    "function_call": getattr(choice.message, "function_call", None),
                    "tool_calls": getattr(choice.message, "tool_calls", None),
                }
                
            if hasattr(response, "usage"):
                llm_event.prompt_tokens = response.usage.prompt_tokens
                llm_event.completion_tokens = response.usage.completion_tokens

            llm_event.end_timestamp = get_ISO_time()
            self._safe_record(session, llm_event)

        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            kwargs_str = pprint.pformat(kwargs)
            response_str = pprint.pformat(response)
            print(f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
                  f"response:\n {response_str}\n"
                  f"kwargs:\n {kwargs_str}\n")

        return response

    def override(self):
        from taskweaver.llm import CompletionService
        from taskweaver.llm.openai import OpenAIService
        from taskweaver.llm.anthropic import AnthropicService
        from taskweaver.llm.azure_ml import AzureMLService
        from taskweaver.llm.google_genai import GoogleGenAIService
        from taskweaver.llm.groq import GroqService
        from taskweaver.llm.ollama import OllamaService
        from taskweaver.llm.qwen import QwenService
        from taskweaver.llm.zhipuai import ZhipuAIService

        services = [
            OpenAIService, AnthropicService, AzureMLService, 
            GoogleGenAIService, GroqService, OllamaService,
            QwenService, ZhipuAIService
        ]

        for service in services:
            self._override_service(service)

    def _override_service(self, service_class):
        service_name = service_class.__name__

        def patched_chat_completion(self, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = self.original_completion[service_name](*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        async def patched_chat_completion_async(self, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = await self.original_completion_async[service_name](*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        self.original_completion[service_name] = service_class.chat_completion
        self.original_completion_async[service_name] = service_class.chat_completion_async
        
        service_class.chat_completion = patched_chat_completion
        service_class.chat_completion_async = patched_chat_completion_async

    def undo_override(self):
        from taskweaver.llm import CompletionService
        from taskweaver.llm.openai import OpenAIService
        from taskweaver.llm.anthropic import AnthropicService
        from taskweaver.llm.azure_ml import AzureMLService
        from taskweaver.llm.google_genai import GoogleGenAIService
        from taskweaver.llm.groq import GroqService
        from taskweaver.llm.ollama import OllamaService
        from taskweaver.llm.qwen import QwenService
        from taskweaver.llm.zhipuai import ZhipuAIService

        services = [
            OpenAIService, AnthropicService, AzureMLService, 
            GoogleGenAIService, GroqService, OllamaService,
            QwenService, ZhipuAIService
        ]

        for service in services:
            service_name = service.__name__
            if service_name in self.original_completion:
                service.chat_completion = self.original_completion[service_name]
                service.chat_completion_async = self.original_completion_async[service_name]