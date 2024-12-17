import pprint
import json
from typing import Optional, Generator
import inspect
import time

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

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id
            logger.info(f"[HANDLE_RESPONSE] Set session_id: {session.session_id}")

        try:
            logger.info(f"[HANDLE_RESPONSE] Processing response: {response}")
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.prompt = kwargs.get("messages", [])
            
            # Parse the response content if it's a dict with content field
            if isinstance(response, dict) and "content" in response:
                try:
                    parsed_content = json.loads(response["content"])
                    llm_event.completion = {
                        "role": response.get("role", "assistant"),
                        "content": parsed_content.get("response", {}).get("message", ""),
                        "metadata": {
                            "plan": parsed_content.get("response", {}).get("plan", ""),
                            "current_plan_step": parsed_content.get("response", {}).get("current_plan_step", ""),
                            "send_to": parsed_content.get("response", {}).get("send_to", "")
                        }
                    }
                except json.JSONDecodeError:
                    llm_event.completion = {
                        "role": response.get("role", "assistant"),
                        "content": response.get("content", "")
                    }
            else:
                llm_event.completion = {
                    "role": "assistant",
                    "content": str(response)
                }
            
            logger.info(f"[HANDLE_RESPONSE] Completion: {llm_event.completion}")
            
            llm_event.end_timestamp = get_ISO_time()
            self._safe_record(session, llm_event)
            logger.info("[HANDLE_RESPONSE] Event recorded successfully")
            
        except Exception as e:
            logger.error(f"[HANDLE_RESPONSE] Error processing response: {str(e)}", exc_info=True)
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            kwargs_str = pprint.pformat(kwargs)
            response_str = pprint.pformat(response)
            logger.warning(
                f"[HANDLE_RESPONSE] Failed to process response:\n"
                f"response:\n {response_str}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def _create_patched_completion(self, service_class):
        """Creates a patched version of the chat completion method"""
        original_chat_completion = service_class._original_chat_completion
        provider = self
        
        def patched_chat_completion(self, messages, stream=True, temperature=None, max_tokens=None, top_p=None, stop=None, **kwargs):
            try:
                logger.info(f"[PATCHED] Starting patched chat completion for {service_class.__name__}")
                logger.info(f"[PATCHED] Stream mode: {stream}")
                
                # Use ISO format timestamp
                init_timestamp = get_ISO_time()
                
                # Call the original method
                result = original_chat_completion(self, messages, stream, temperature, max_tokens, top_p, stop, **kwargs)
                
                logger.info(f"[PATCHED] Got result type: {type(result)}")
                
                # Handle streaming responses
                if stream:
                    logger.info("[PATCHED] Handling streaming response")
                    accumulated_response = {'role': 'assistant', 'content': ''}
                    
                    def process_stream():
                        for chunk in result:
                            logger.info(f"[PATCHED] Stream chunk: {chunk}")
                            if chunk.get('content'):
                                accumulated_response['content'] += chunk['content']
                            yield chunk
                        
                        # Record the complete response after streaming
                        logger.info(f"[PATCHED] Recording accumulated response: {accumulated_response}")
                        # Remove TaskWeaver specific kwargs
                        response_kwargs = {k: v for k, v in kwargs.items() 
                                        if k not in ['json_schema']}
                        # Add required parameters
                        provider.handle_response(
                            response=accumulated_response,
                            kwargs=response_kwargs,
                            init_timestamp=init_timestamp
                        )
                    
                    return process_stream()
                
                # Handle non-streaming responses
                else:
                    logger.info("[PATCHED] Handling non-streaming response")
                    # Remove TaskWeaver specific kwargs
                    response_kwargs = {k: v for k, v in kwargs.items() 
                                    if k not in ['json_schema']}
                    # Add required parameters
                    provider.handle_response(
                        response=result,
                        kwargs=response_kwargs,
                        init_timestamp=init_timestamp
                    )
                    return result
                    
            except Exception as e:
                logger.error(f"[PATCHED] Error in patched completion: {str(e)}", exc_info=True)
                # Return original result in case of error
                return original_chat_completion(self, messages, stream, temperature, max_tokens, top_p, stop, **kwargs)
        
        return patched_chat_completion

    def override(self):
        try:
            # Get the current API type from config
            from taskweaver.config.config_mgt import AppConfigSource
            from taskweaver.llm.base import LLMModuleConfig
            
            config_source = AppConfigSource()
            llm_config = LLMModuleConfig(config_source)
            self.api_type = llm_config.api_type
            
            logger.info("[OVERRIDE] Starting to patch LLM services")
            
            # Patch all available services
            services = [
                ("openai", "taskweaver.llm.openai", "OpenAIService"),
                ("anthropic", "taskweaver.llm.anthropic", "AnthropicService"),
                ("azure", "taskweaver.llm.azure", "AzureService"),
                ("groq", "taskweaver.llm.groq", "GroqService"),
                ("ollama", "taskweaver.llm.ollama", "OllamaService"),
                ("qwen", "taskweaver.llm.qwen", "QWenService"),
                ("zhipuai", "taskweaver.llm.zhipuai", "ZhipuAIService")
            ]
            
            for service_type, module_path, class_name in services:
                try:
                    logger.info(f"[OVERRIDE] Attempting to patch {class_name}")
                    module = __import__(module_path, fromlist=[class_name])
                    service_class = getattr(module, class_name)
                    
                    if not hasattr(service_class, '_original_chat_completion'):
                        service_class._original_chat_completion = service_class.chat_completion
                        service_class.chat_completion = self._create_patched_completion(service_class)
                        logger.info(f"[OVERRIDE] Successfully patched {class_name}")
                except ImportError:
                    logger.debug(f"[OVERRIDE] Service {service_type} not available")
                except Exception as e:
                    logger.error(f"[OVERRIDE] Failed to patch {class_name}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"[OVERRIDE] Failed to patch services: {str(e)}", exc_info=True)

    def undo_override(self):
        try:
            # Restore all services that were patched
            services = [
                ("openai", "taskweaver.llm.openai", "OpenAIService"),
                ("anthropic", "taskweaver.llm.anthropic", "AnthropicService"),
                ("azure", "taskweaver.llm.azure", "AzureService"),
                ("groq", "taskweaver.llm.groq", "GroqService"),
                ("ollama", "taskweaver.llm.ollama", "OllamaService"),
                ("qwen", "taskweaver.llm.qwen", "QWenService"),
                ("zhipuai", "taskweaver.llm.zhipuai", "ZhipuAIService")
            ]
            
            for service_type, module_path, class_name in services:
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    service_class = getattr(module, class_name)
                    
                    if hasattr(service_class, '_original_chat_completion'):
                        service_class.chat_completion = service_class._original_chat_completion
                        delattr(service_class, '_original_chat_completion')
                        logger.info(f"[UNDO] Restored original methods for {class_name}")
                except ImportError:
                    continue
                except Exception as e:
                    logger.error(f"[UNDO] Failed to restore {class_name}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"[UNDO] Failed to restore services: {str(e)}", exc_info=True)