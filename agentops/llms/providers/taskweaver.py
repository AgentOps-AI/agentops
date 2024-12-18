import pprint
from typing import Optional, Generator
import inspect
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
        logger.info(f"TaskWeaver provider initialized with client: {client}")

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle responses for TaskWeaver"""
        logger.info(f"[HANDLE_RESPONSE] Start handling response type: {type(response)}")
        logger.info(f"[HANDLE_RESPONSE] Session: {session}")
        logger.info(f"[HANDLE_RESPONSE] Processing response: {response}")

        try:
            messages = kwargs.get("messages", [])
            conversations = []
            current_conversation = []
            
            # Group messages by conversation and role
            for msg in messages:
                if msg['role'] == 'user' and "Let's start the new conversation!" in msg.get('content', ''):
                    if current_conversation:
                        conversations.append(current_conversation)
                    current_conversation = []
                current_conversation.append(msg)
                
                # Record system messages immediately
                if msg['role'] == 'system':
                    system_event = LLMEvent(
                        init_timestamp=init_timestamp,
                        params=kwargs,
                        prompt=[msg],
                        completion=None,
                        model=kwargs.get("model", "unknown"),
                    )
                    if session is not None:
                        system_event.session_id = session.session_id
                    system_event.agent_id = check_call_stack_for_agent_id()
                    system_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, system_event)
                    logger.info("[HANDLE_RESPONSE] System message event recorded")
            
            if current_conversation:
                conversations.append(current_conversation)

            # Process the current response
            if isinstance(response, dict):
                content = response.get("content", "")
                try:
                    if content and isinstance(content, str) and content.startswith('{"response":'):
                        parsed = json.loads(content)
                        taskweaver_response = parsed.get("response", {})
                        role = taskweaver_response.get("send_to")
                        
                        # Record LLM event for the current role
                        llm_event = LLMEvent(
                            init_timestamp=init_timestamp,
                            params=kwargs,
                            prompt=current_conversation,
                            completion={
                                "role": "assistant",
                                "content": taskweaver_response.get("message", ""),
                                "metadata": {
                                    "plan": taskweaver_response.get("plan"),
                                    "current_plan_step": taskweaver_response.get("current_plan_step"),
                                    "send_to": role,
                                    "init_plan": taskweaver_response.get("init_plan")
                                },
                            },
                            model=kwargs.get("model", "unknown"),
                        )
                        if session is not None:
                            llm_event.session_id = session.session_id
                        llm_event.end_timestamp = get_ISO_time()
                        self._safe_record(session, llm_event)
                        logger.info(f"[HANDLE_RESPONSE] LLM event recorded for role: {role}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"[HANDLE_RESPONSE] JSON decode error: {str(e)}")
                    raise
                    
            logger.info(f"[HANDLE_RESPONSE] Completion: {llm_event.completion}")
            
        except Exception as e:
            logger.error(f"[HANDLE_RESPONSE] Error processing response: {str(e)}", exc_info=True)
            error_event = ErrorEvent(
                trigger_event=llm_event if 'llm_event' in locals() else None,
                exception=e,
                details={"response": str(response), "kwargs": str(kwargs)}
            )
            self._safe_record(session, error_event)
            kwargs_str = pprint.pformat(kwargs)
            response_str = pprint.pformat(response)
            logger.warning(
                f"[HANDLE_RESPONSE] Failed to process response:\n"
                f"response:\n {response_str}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def override(self):
        # Import all potential LLM service implementations
        from taskweaver.llm.openai import OpenAIService
        from taskweaver.llm.anthropic import AnthropicService
        from taskweaver.llm.azure_ml import AzureMLService
        from taskweaver.llm.groq import GroqService
        from taskweaver.llm.ollama import OllamaService
        from taskweaver.llm.qwen import QWenService
        from taskweaver.llm.zhipuai import ZhipuAIService
        
        logger.info("[OVERRIDE] Starting to patch LLM services")
        
        services = [
            OpenAIService,
            AnthropicService,
            AzureMLService,
            GroqService,
            OllamaService,
            QWenService,
            ZhipuAIService
        ]
        
        for service_class in services:
            try:
                logger.info(f"[OVERRIDE] Attempting to patch {service_class.__name__}")
                
                if hasattr(service_class, 'chat_completion'):
                    original = service_class.chat_completion
                    
                    def patched_chat_completion(service_self, messages, stream=True, temperature=None, max_tokens=None, top_p=None, stop=None, **kwargs) -> Generator:
                        logger.info(f"[PATCHED] Starting patched chat completion for {service_self.__class__.__name__}")
                        logger.info(f"[PATCHED] Stream mode: {stream}")
                        
                        init_timestamp = get_ISO_time()
                        session = kwargs.pop("session", None)
                        logger.info(f"[PATCHED] Session: {session}")
                        
                        logger.info(f"[PATCHED] Calling original with messages: {messages}")
                        result = original(
                            service_self, 
                            messages=messages,
                            stream=stream,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            top_p=top_p,
                            stop=stop,
                            **kwargs
                        )
                        logger.info(f"[PATCHED] Got result type: {type(result)}")
                        
                        if stream:
                            logger.info("[PATCHED] Handling streaming response")
                            accumulated_response = {"role": "assistant", "content": ""}
                            for response in result:
                                logger.info(f"[PATCHED] Stream chunk: {response}")
                                if isinstance(response, dict) and "content" in response:
                                    accumulated_response["content"] += response["content"]
                                else:
                                    accumulated_response["content"] += str(response)
                                yield response
                            
                            logger.info(f"[PATCHED] Recording accumulated response: {accumulated_response}")
                            self.handle_response(accumulated_response, kwargs, init_timestamp, session=session)
                        else:
                            logger.info("[PATCHED] Handling non-streaming response")
                            response = next(result) if hasattr(result, '__next__') else result
                            logger.info(f"[PATCHED] Non-stream response: {response}")
                            self.handle_response(response, kwargs, init_timestamp, session=session)
                            return response
                    
                    service_class.chat_completion = patched_chat_completion
                    logger.info(f"[OVERRIDE] Successfully patched {service_class.__name__}")
                
            except Exception as e:
                logger.error(f"[OVERRIDE] Failed to patch {service_class.__name__}: {str(e)}", exc_info=True)

    def undo_override(self):
        # Similar imports as override method
        from taskweaver.llm.openai import OpenAIService
        from taskweaver.llm.anthropic import AnthropicService
        from taskweaver.llm.azure_ml import AzureMLService
        from taskweaver.llm.groq import GroqService
        from taskweaver.llm.ollama import OllamaService
        from taskweaver.llm.qwen import QWenService
        from taskweaver.llm.zhipuai import ZhipuAIService
        
        services = [
            OpenAIService,
            AnthropicService,
            AzureMLService,
            GroqService,
            OllamaService,
            QWenService,
            ZhipuAIService
        ]
        
        for service_class in services:
            if hasattr(service_class, '_original_chat_completion'):
                service_class.chat_completion = service_class._original_chat_completion
                delattr(service_class, '_original_chat_completion')
                logger.info(f"[UNDO] Restored original methods for {service_class.__name__}")