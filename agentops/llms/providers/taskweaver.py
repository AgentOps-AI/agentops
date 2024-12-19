import pprint
from typing import Optional
import json

from agentops.event import ErrorEvent, LLMEvent
from agentops.session import Session
from agentops.log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.llms.providers.instrumented_provider import InstrumentedProvider
from agentops.singleton import singleton


@singleton
class TaskWeaverProvider(InstrumentedProvider):
    original_chat_completion = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "TaskWeaver"

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle responses for TaskWeaver"""
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)

        try:
            response_dict = response.get("response", {})
            llm_event.init_timestamp = init_timestamp
            llm_event.params = kwargs
            llm_event.returns = response_dict
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs.get("model", "unknown")
            llm_event.prompt = kwargs.get("messages")
            llm_event.completion = response_dict.get("message", "")
            llm_event.end_timestamp = get_ISO_time()
            self._safe_record(session, llm_event)
            
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=llm_event,
                exception=e,
                details={"response": str(response), "kwargs": str(kwargs)}
            )
            self._safe_record(session, error_event)
            kwargs_str = pprint.pformat(kwargs)
            response_str = pprint.pformat(response)
            logger.error(
                f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
                f"response:\n {response_str}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def override(self):
        """Override TaskWeaver's chat completion methods"""
        global original_chat_completion

        try:
            from taskweaver.llm.openai import OpenAIService
            from taskweaver.llm.anthropic import AnthropicService
            from taskweaver.llm.azure_ml import AzureMLService
            from taskweaver.llm.groq import GroqService
            from taskweaver.llm.ollama import OllamaService
            from taskweaver.llm.qwen import QWenService
            from taskweaver.llm.zhipuai import ZhipuAIService

            # Create our own mapping of services
            service_mapping = {
                "openai": OpenAIService,
                "azure": OpenAIService,
                "azure_ad": OpenAIService,
                "anthropic": AnthropicService,
                "azure_ml": AzureMLService,
                "groq": GroqService,
                "ollama": OllamaService,
                "qwen": QWenService,
                "zhipuai": ZhipuAIService
            }

            def patched_chat_completion(service, *args, **kwargs):
                init_timestamp = get_ISO_time()
                session = kwargs.get("session", None)
                if "session" in kwargs.keys():
                    del kwargs["session"]
                
                result = original_chat_completion(service, *args, **kwargs)
                kwargs.update(
                    {
                        "model": self._get_model_name(service),
                        "messages": args[0],
                        "stream": args[1],
                        "temperature": args[2],
                        "max_tokens": args[3],
                        "top_p": args[4],
                        "stop": args[5],
                    }
                )

                if kwargs["stream"]:
                    accumulated_content = ""
                    for chunk in result:
                        if isinstance(chunk, dict) and "content" in chunk:
                            accumulated_content += chunk["content"]
                        else:
                            accumulated_content += chunk
                        yield chunk
                    accumulated_content = json.loads(accumulated_content)
                    return self.handle_response(accumulated_content, kwargs, init_timestamp, session=session)
                else:
                    return self.handle_response(result, kwargs, init_timestamp, session=session)

            for service_name, service_class in service_mapping.items():
                original_chat_completion = service_class.chat_completion
                service_class.chat_completion = patched_chat_completion
                    
        except Exception as e:
            logger.error(f"Failed to patch method: {str(e)}", exc_info=True)

    def undo_override(self):
        """Restore original TaskWeaver chat completion methods"""
        try:
            from taskweaver.llm.openai import OpenAIService
            from taskweaver.llm.anthropic import AnthropicService
            from taskweaver.llm.azure_ml import AzureMLService
            from taskweaver.llm.groq import GroqService
            from taskweaver.llm.ollama import OllamaService
            from taskweaver.llm.qwen import QWenService
            from taskweaver.llm.zhipuai import ZhipuAIService

            # Create our own mapping of services
            service_mapping = {
                "openai": OpenAIService,
                "azure": OpenAIService,
                "azure_ad": OpenAIService,
                "anthropic": AnthropicService,
                "azure_ml": AzureMLService,
                "groq": GroqService,
                "ollama": OllamaService,
                "qwen": QWenService,
                "zhipuai": ZhipuAIService
            }

            if original_chat_completion is not None:
                for service_name, service_class in service_mapping.items():
                    service_class.chat_completion = original_chat_completion

        except Exception as e:
            logger.error(f"Failed to restore original method: {str(e)}", exc_info=True)

    def _get_model_name(self, service) -> str:
        """Extract model name from service instance"""
        model_name = "unknown"
        if hasattr(service, "config"):
            config = service.config
            if hasattr(config, "model"):
                model_name = config.model or "unknown"
            elif hasattr(config, "llm_module_config") and hasattr(config.llm_module_config, "model"):
                model_name = config.llm_module_config.model or "unknown"
        return model_name