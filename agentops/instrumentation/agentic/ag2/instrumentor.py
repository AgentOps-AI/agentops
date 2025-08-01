"""AG2 (AutoGen) Instrumentation Module

This module provides the main instrumentor class and wrapping functions for AG2 (AutoGen).
It focuses on collecting summary-level telemetry rather than individual message events.
"""

import json
from typing import Dict, Any
from wrapt import wrap_function_wrapper

from opentelemetry.trace import SpanKind
from opentelemetry.metrics import Meter
from opentelemetry.instrumentation.utils import unwrap as otel_unwrap
import contextvars
import threading
from opentelemetry import context as otel_context
from agentops.logging import logger
from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    StandardMetrics,
    create_span,
    SpanAttributeManager,
)
from agentops.instrumentation.agentic.ag2 import LIBRARY_NAME, LIBRARY_VERSION
from agentops.semconv.message import MessageAttributes
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.workflow import WorkflowAttributes
from agentops.semconv.tool import ToolAttributes


class AG2Instrumentor(CommonInstrumentor):
    """Instrumentor for AG2 (AutoGen)

    This instrumentor captures high-level events from AG2's agent interactions,
    focusing on summaries rather than individual messages, and providing detailed
    tool usage information.
    """

    def __init__(self):
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=[],  # We'll use custom wrapping
            metrics_enabled=True,
            dependencies=["ag2 >= 0.3.2"],
        )
        super().__init__(config)
        self._attribute_manager = None

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for AG2 instrumentation."""
        return StandardMetrics.create_standard_metrics(meter)

    def _initialize(self, **kwargs):
        """Initialize attribute manager and AG2-specific concurrent.futures instrumentation."""
        self._attribute_manager = SpanAttributeManager(service_name="agentops", deployment_environment="production")

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for AG2 methods."""

        methods_to_wrap = [
            ("autogen.agentchat.conversable_agent", "ConversableAgent.__init__", self._agent_init_wrapper),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.run", self._agent_run_wrapper_with_context),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.initiate_chat", self._initiate_chat_wrapper),
            (
                "autogen.agentchat.conversable_agent",
                "ConversableAgent.a_initiate_chat",
                self._async_initiate_chat_wrapper,
            ),
            (
                "autogen.agentchat.conversable_agent",
                "ConversableAgent._generate_oai_reply_from_client",
                self._generate_oai_reply_from_client_wrapper,
            ),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.receive", self._receive_wrapper),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.a_receive", self._async_receive_wrapper),
            ("autogen.agentchat.groupchat", "GroupChatManager.run_chat", self._group_chat_run_wrapper),
            ("autogen.agentchat.groupchat", "GroupChatManager.a_run_chat", self._async_group_chat_run_wrapper),
            (
                "autogen.agentchat.conversable_agent",
                "ConversableAgent.execute_function",
                lambda tracer: self._tool_execution_wrapper(tracer, "function"),
            ),
            (
                "autogen.agentchat.conversable_agent",
                "ConversableAgent.run_code",
                lambda tracer: self._tool_execution_wrapper(tracer, "code"),
            ),
            ("autogen.agentchat.groupchat", "GroupChat.select_speaker", self._group_chat_select_speaker_wrapper),
        ]

        for module, method, wrapper_factory in methods_to_wrap:
            try:
                wrap_function_wrapper(module, method, wrapper_factory(self._tracer))
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to wrap {method}: {e}")

    def _custom_unwrap(self, **kwargs):
        """Remove instrumentation from AG2."""
        # Unwrap all instrumented methods
        methods_to_unwrap = [
            ("autogen.agentchat.conversable_agent", "ConversableAgent.__init__"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.run"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.initiate_chat"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.a_initiate_chat"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent._generate_oai_reply_from_client"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.receive"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.a_receive"),
            ("autogen.agentchat.groupchat", "GroupChatManager.run_chat"),
            ("autogen.agentchat.groupchat", "GroupChatManager.a_run_chat"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.execute_function"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.run_code"),
            ("autogen.agentchat.groupchat", "GroupChat.select_speaker"),
        ]

        try:
            for module, method in methods_to_unwrap:
                otel_unwrap(module, method)
            logger.debug("Successfully uninstrumented AG2")
        except Exception as e:
            logger.debug(f"Failed to unwrap AG2 methods: {e}")

    def _set_llm_config_attributes(self, span, llm_config):
        if not isinstance(llm_config, dict):
            return

        if "model" in llm_config:
            span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, llm_config["model"])

        for param, attr in [
            ("temperature", SpanAttributes.LLM_REQUEST_TEMPERATURE),
            ("top_p", SpanAttributes.LLM_REQUEST_TOP_P),
            ("frequency_penalty", SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY),
            ("presence_penalty", SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY),
        ]:
            if param in llm_config and llm_config[param] is not None:
                span.set_attribute(attr, llm_config[param])

    def _agent_init_wrapper(self, tracer):
        """Wrapper for capturing agent initialization."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                name = kwargs.get("name", "unnamed_agent")
                llm_config = kwargs.get("llm_config", {})

                result = wrapped(*args, **kwargs)

                model = "unknown"
                if isinstance(llm_config, dict) and llm_config:
                    model = llm_config.get("model", "unknown")

                instance._agentops_metadata = {"name": name, "type": "ConversableAgent", "model": model}

                return result
            except Exception:
                return wrapped(*args, **kwargs)

        return wrapper

    def _generate_oai_reply_from_client_wrapper(self, tracer):
        """Wrapper for capturing _generate_oai_reply_from_client method calls with token metrics."""

        def wrapper(wrapped, instance, args, kwargs):
            agent_name = getattr(instance, "name", "unnamed_agent")

            # Get model name from llm_client for span naming
            llm_client = args[0] if args else kwargs.get("llm_client")

            # Extract model from _config_list
            model_name = "unknown"
            if hasattr(llm_client, "_config_list") and llm_client._config_list:
                if isinstance(llm_client._config_list, list) and len(llm_client._config_list) > 0:
                    config = llm_client._config_list[0]
                    if isinstance(config, dict) and "model" in config:
                        model_name = config["model"]

            span_name = f"{model_name}.llm"

            with create_span(
                tracer, span_name, kind=SpanKind.CLIENT, attribute_manager=self._attribute_manager
            ) as span:
                # Set span kind for actual LLM client call
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.LLM.value)
                span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "llm")
                span.set_attribute("llm.client_call", "true")

                # Get messages from args
                messages = args[1] if len(args) > 1 else kwargs.get("messages", [])

                # Extract input from messages and set gen_ai.prompt
                if messages and isinstance(messages, list) and len(messages) > 0:
                    # Set gen_ai.prompt array with full conversation history
                    prompt_index = 0
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get("role") in ["user", "assistant", "system"]:
                            role = msg.get("role")
                            content = msg.get("content", "")
                            if content and role:
                                span.set_attribute(
                                    f"{SpanAttributes.LLM_PROMPTS}.{prompt_index}.content", self._safe_str(content)
                                )
                                span.set_attribute(f"{SpanAttributes.LLM_PROMPTS}.{prompt_index}.role", role)
                                prompt_index += 1

                    # Set entity input to the latest user message (what triggered this LLM call)
                    latest_user_message = None
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get("role") == "user":
                            content = msg.get("content", "")
                            if content:
                                latest_user_message = content

                    if latest_user_message:
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, self._safe_str(latest_user_message))

                # Call the wrapped method - this is where the actual LLM call happens
                result = wrapped(*args, **kwargs)

                # Set the output and gen_ai.completion
                if result:
                    if isinstance(result, dict):
                        content = result.get("content", "")
                        if content:
                            content_str = self._safe_str(content)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, content_str)
                            span.set_attribute(f"{SpanAttributes.LLM_COMPLETIONS}.0.content", content_str)
                            span.set_attribute(f"{SpanAttributes.LLM_COMPLETIONS}.0.role", "assistant")

                        # If model information is in the result
                        if "model" in result:
                            span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, result["model"])
                    elif isinstance(result, str):
                        # Handle string result (which is what AG2 returns)
                        result_str = self._safe_str(result)

                        # Set entity output
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, result_str)

                        # Set gen_ai.completion with full content
                        span.set_attribute(f"{SpanAttributes.LLM_COMPLETIONS}.0.content", result_str)
                        span.set_attribute(f"{SpanAttributes.LLM_COMPLETIONS}.0.role", "assistant")

                # Try to get token metrics from the client's usage tracking
                try:
                    # The OpenAIWrapper tracks usage in actual_usage_summary and total_usage_summary
                    if hasattr(llm_client, "actual_usage_summary") and llm_client.actual_usage_summary:
                        # Get the latest usage
                        for model, usage in llm_client.actual_usage_summary.items():
                            if model != "total_cost" and isinstance(usage, dict):
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", 0)
                                total_tokens = usage.get("total_tokens", 0)
                                cost = usage.get("cost", 0.0)

                                # Set token usage metrics
                                if prompt_tokens > 0:
                                    span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, str(prompt_tokens))
                                if completion_tokens > 0:
                                    span.set_attribute(
                                        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, str(completion_tokens)
                                    )
                                if total_tokens > 0:
                                    span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, str(total_tokens))
                                if cost > 0:
                                    span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, str(cost))

                                # Set request/response model
                                span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model)
                                span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, model)
                                span.set_attribute(SpanAttributes.LLM_SYSTEM, "ag2")

                                break  # Use the first model's metrics
                except Exception as e:
                    logger.debug(f"[AG2 DEBUG] Could not extract token metrics: {e}")

                return result

        return wrapper

    def _initiate_chat_wrapper(self, tracer):
        """Wrapper for capturing individual chat initiation as a parent span."""

        def wrapper(wrapped, instance, args, kwargs):
            recipient_agent = args[0] if args else None
            if not recipient_agent:
                return wrapped(*args, **kwargs)

            # Get agent names for span identification
            initiator_name = getattr(instance, "name", "unnamed_initiator")
            recipient_name = getattr(recipient_agent, "name", "unnamed_agent")

            span_name = f"ag2.chat.{initiator_name}_to_{recipient_name}.workflow"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                # Set span kind as agent for proper categorization
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                span.set_attribute(AgentAttributes.FROM_AGENT, initiator_name)
                span.set_attribute(AgentAttributes.TO_AGENT, recipient_name)
                span.set_attribute("agent.type", "individual")
                span.set_attribute("agent.initiator", initiator_name)
                span.set_attribute("agent.recipient", recipient_name)

                # Set agentops entity attributes
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                # Extract initial message
                initial_message = kwargs.get("message", "")
                if initial_message:
                    initial_message = self._safe_str(initial_message)
                    span.set_attribute("agent.initial_message", initial_message)
                    # Set entity input
                    span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, initial_message)

                # Extract system messages and put them in agent attributes
                initiator_system_msg = getattr(instance, "system_message", "")
                if initiator_system_msg:
                    initiator_system_msg = self._safe_str(initiator_system_msg)
                    span.set_attribute("agent.initiator_system_message", initiator_system_msg)

                recipient_system_msg = getattr(recipient_agent, "system_message", "")
                if recipient_system_msg:
                    recipient_system_msg = self._safe_str(recipient_system_msg)
                    span.set_attribute("agent.system_instruction", recipient_system_msg)
                    # Also set in gen_ai for compatibility
                    span.set_attribute(SpanAttributes.LLM_REQUEST_SYSTEM_INSTRUCTION, recipient_system_msg)

                # Extract LLM config and set gen_ai attributes
                recipient_llm_config = getattr(recipient_agent, "llm_config", {})

                if isinstance(recipient_llm_config, dict) and recipient_llm_config:
                    model = recipient_llm_config.get("model", "unknown")
                    span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model)
                    span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, model)
                    span.set_attribute(SpanAttributes.LLM_SYSTEM, "ag2")

                    # Also set LLM config attributes
                    self._set_llm_config_attributes(span, recipient_llm_config)

                result = wrapped(*args, **kwargs)

                # Extract chat history after completion
                self._extract_chat_history(span, instance, recipient_agent)

                return result

        return wrapper

    def _async_initiate_chat_wrapper(self, tracer):
        """Wrapper for capturing async individual chat initiation as a parent span."""

        async def wrapper(wrapped, instance, args, kwargs):
            recipient_agent = args[0] if args else None
            if not recipient_agent:
                return await wrapped(*args, **kwargs)

            # Get agent names for span identification
            initiator_name = getattr(instance, "name", "unnamed_initiator")
            recipient_name = getattr(recipient_agent, "name", "unnamed_agent")

            span_name = f"ag2.chat.{initiator_name}_to_{recipient_name}.workflow"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                # Set span kind as agent for proper categorization
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                span.set_attribute(AgentAttributes.FROM_AGENT, initiator_name)
                span.set_attribute(AgentAttributes.TO_AGENT, recipient_name)
                span.set_attribute("agent.type", "individual_async")
                span.set_attribute("agent.initiator", initiator_name)
                span.set_attribute("agent.recipient", recipient_name)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                # Extract initial message
                initial_message = kwargs.get("message", "")
                if initial_message:
                    initial_message = self._safe_str(initial_message)
                    span.set_attribute("agent.initial_message", initial_message)
                    span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, initial_message)

                # Extract system messages
                recipient_system_msg = getattr(recipient_agent, "system_message", "")
                if recipient_system_msg:
                    recipient_system_msg = self._safe_str(recipient_system_msg)
                    span.set_attribute("agent.system_instruction", recipient_system_msg)
                    span.set_attribute(SpanAttributes.LLM_REQUEST_SYSTEM_INSTRUCTION, recipient_system_msg)

                # Extract LLM config
                recipient_llm_config = getattr(recipient_agent, "llm_config", {})
                if isinstance(recipient_llm_config, dict) and recipient_llm_config:
                    self._set_llm_config_attributes(span, recipient_llm_config)

                result = await wrapped(*args, **kwargs)

                # Extract chat history after completion
                self._extract_chat_history(span, instance, recipient_agent)

                return result

        return wrapper

    def _receive_wrapper(self, tracer):
        """Wrapper for capturing message receive events."""

        def wrapper(wrapped, instance, args, kwargs):
            agent_name = getattr(instance, "name", "unnamed_agent")
            span_name = f"ag2.agent.{agent_name}.receive"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                # Get message and sender
                message = args[0] if args else kwargs.get("message", "")
                sender = args[1] if len(args) > 1 else kwargs.get("sender")

                if sender:
                    sender_name = getattr(sender, "name", "unknown")
                    span.set_attribute("agent.sender", sender_name)

                if message:
                    if isinstance(message, dict):
                        content = message.get("content", "")
                        if content:
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, self._safe_str(content))
                    elif isinstance(message, str):
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, self._safe_str(message))

                result = wrapped(*args, **kwargs)
                return result

        return wrapper

    def _async_receive_wrapper(self, tracer):
        """Wrapper for async capturing message reception."""

        async def wrapper(wrapped, instance, args, kwargs):
            agent_name = getattr(instance, "name", "unnamed_agent")
            span_name = f"ag2.agent.{agent_name}.async_receive"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                # Get message from the first argument
                message = args[0] if args else None

                # Enhanced message processing
                if message:
                    if isinstance(message, dict):
                        # Dict message format
                        sender_name = message.get("name", "unknown")
                        content = self._extract_message_content(message)
                        role = message.get("role", "user")

                        # Set sender and message attributes
                        span.set_attribute("agent.sender", sender_name)
                        span.set_attribute("message.role", role)

                        if content:
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, content)
                            span.set_attribute("message.content", content)

                    elif isinstance(message, str):
                        # String message format
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, message)
                        span.set_attribute("message.content", message)

                # Get sender from the second argument if available
                sender = args[1] if len(args) > 1 else None
                if sender and hasattr(sender, "name"):
                    span.set_attribute("agent.sender_name", sender.name)

                return await wrapped(*args, **kwargs)

        return wrapper

    def _async_group_chat_run_wrapper(self, tracer):
        """Wrapper for capturing async group chat execution."""

        async def wrapper(wrapped, instance, args, kwargs):
            with create_span(
                tracer,
                "ag2.groupchat.run.task.async",
                kind=SpanKind.INTERNAL,
                attribute_manager=self._attribute_manager,
            ) as span:
                group_chat = getattr(instance, "groupchat", None)
                agents = getattr(group_chat, "agents", []) if group_chat else []
                agent_names = [getattr(agent, "name", f"agent_{i}") for i, agent in enumerate(agents)]

                span.set_attribute(AgentAttributes.AGENT_ROLE, "GroupChatManager")
                span.set_attribute(AgentAttributes.AGENT_NAME, getattr(instance, "name", "unnamed_manager"))
                span.set_attribute("groupchat.agents", ", ".join(agent_names))
                span.set_attribute("groupchat.agent_count", len(agents))

                # Capture input message if available
                message = kwargs.get("message", "")
                if message:
                    content_to_set = self._extract_message_content(message)
                    span.set_attribute("groupchat.input_message", content_to_set)

                result = await wrapped(*args, **kwargs)
                self._capture_group_chat_summary(span, instance, result)
                return result

        return wrapper

    def _agent_run_wrapper_with_context(self, tracer):
        """Wrapper for capturing agent run with context propagation and proper span lifecycle."""

        def wrapper(wrapped, instance, args, kwargs):
            agent_name = getattr(instance, "name", "unnamed_agent")
            agent_type = getattr(instance, "_agentops_metadata", {}).get("type", "ConversableAgent")
            span_name = f"ag2.agent.{agent_name}.run.workflow"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                model = getattr(instance, "_agentops_metadata", {}).get("model", "unknown")

                span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)
                span.set_attribute(AgentAttributes.AGENT_ROLE, agent_type)
                span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, model)

                llm_config = getattr(instance, "llm_config", None)
                self._set_llm_config_attributes(span, llm_config)

                # Capture input message if available
                message = kwargs.get("message", "")
                if message:
                    content_to_set = self._extract_message_content(message)
                    span.set_attribute("agent.run.input_message", content_to_set)

                # Capture BOTH contextvars and OpenTelemetry context
                ctx = contextvars.copy_context()
                current_otel_context = otel_context.get_current()

                # Thread tracking for proper span lifecycle
                active_threads = []

                # Store the original Thread.__init__ and start methods
                original_thread_init = threading.Thread.__init__
                original_thread_start = threading.Thread.start

                def context_aware_init(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
                    """Modified Thread.__init__ that wraps the target to run in both captured contexts."""
                    if kwargs is None:
                        kwargs = {}
                    if target and callable(target):
                        original_target = target

                        def wrapped_target(*target_args, **target_kwargs):
                            # Run in both contextvars AND OpenTelemetry context
                            def run_with_otel_context():
                                # Attach the OpenTelemetry context in the thread
                                token = otel_context.attach(current_otel_context)
                                try:
                                    return original_target(*target_args, **target_kwargs)
                                finally:
                                    otel_context.detach(token)

                            # Run with contextvars context
                            return ctx.run(run_with_otel_context)

                        target = wrapped_target

                    # Keep original daemon setting but ensure conversations don't run indefinitely
                    # If daemon was not explicitly set, default to False (AG2's normal behavior)
                    if daemon is None:
                        daemon = False

                    original_thread_init(
                        self, group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon
                    )

                def context_aware_start(self):
                    """Modified Thread.start that tracks the thread."""
                    active_threads.append(self)
                    return original_thread_start(self)

                # Temporarily patch Thread.__init__ and start just for this run() call
                threading.Thread.__init__ = context_aware_init
                threading.Thread.start = context_aware_start
                try:
                    response = wrapped(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[AG2 DEBUG] Error in agent.run execution: {e}")
                    raise
                finally:
                    # Always restore the original Thread methods
                    try:
                        threading.Thread.__init__ = original_thread_init
                        threading.Thread.start = original_thread_start
                    except Exception as e:
                        logger.error(f"[AG2 DEBUG] Error restoring Thread methods: {e}")
                        # Force restore
                        threading.Thread.__init__ = (
                            threading.Thread.__init__.__wrapped__
                            if hasattr(threading.Thread.__init__, "__wrapped__")
                            else original_thread_init
                        )
                        threading.Thread.start = (
                            threading.Thread.start.__wrapped__
                            if hasattr(threading.Thread.start, "__wrapped__")
                            else original_thread_start
                        )

                # Try to get final results from response if available
                try:
                    if hasattr(response, "get_chat_results"):
                        chat_results = response.get_chat_results()
                        if chat_results:
                            self._capture_conversation_summary(span, instance, chat_results)
                    elif hasattr(response, "chat_history"):
                        self._capture_conversation_summary(span, instance, response)
                    elif hasattr(response, "get") and callable(response.get):
                        model_info = response.get("model", "")
                        if model_info:
                            span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, str(model_info))
                except Exception as e:
                    logger.debug(f"[AG2 DEBUG] Could not extract final results: {e}")

                span.set_attribute(WorkflowAttributes.WORKFLOW_STEP_STATUS, "completed")
                return response

        return wrapper

    def _group_chat_run_wrapper(self, tracer):
        """Wrapper for capturing group chat execution."""

        def wrapper(wrapped, instance, args, kwargs):
            with create_span(
                tracer, "ag2.groupchat.run.task", kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                group_chat = getattr(instance, "groupchat", None)
                agents = getattr(group_chat, "agents", []) if group_chat else []
                agent_names = [getattr(agent, "name", f"agent_{i}") for i, agent in enumerate(agents)]

                span.set_attribute(AgentAttributes.AGENT_ROLE, "GroupChatManager")
                span.set_attribute(AgentAttributes.AGENT_NAME, getattr(instance, "name", "unnamed_manager"))
                span.set_attribute("groupchat.agents", ", ".join(agent_names))
                span.set_attribute("groupchat.agent_count", len(agents))

                # Capture input message if available
                message = kwargs.get("message", "")
                if message:
                    content_to_set = self._extract_message_content(message)
                    span.set_attribute("groupchat.input_message", content_to_set)

                result = wrapped(*args, **kwargs)
                self._capture_group_chat_summary(span, instance, result)
                return result

        return wrapper

    def _tool_execution_wrapper(self, tracer, tool_type):
        """Wrapper for capturing tool execution."""

        def wrapper(wrapped, instance, args, kwargs):
            span_name = f"ag2.tool.{tool_type}.tool_usage"

            with create_span(
                tracer, span_name, kind=SpanKind.CLIENT, attribute_manager=self._attribute_manager
            ) as span:
                # Set span kind and type as tool for proper categorization
                span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.TOOL.value)
                agent_name = getattr(instance, "name", "unnamed_agent")
                span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)
                span.set_attribute(ToolAttributes.TOOL_NAME, tool_type)
                span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "tool")

                if tool_type == "function" and args:
                    func_call = args[0]
                    if isinstance(func_call, dict):
                        span.set_attribute(
                            MessageAttributes.TOOL_CALL_NAME.format(i=0), func_call.get("name", "unknown")
                        )
                        if "arguments" in func_call:
                            try:
                                span.set_attribute(
                                    MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=0),
                                    json.dumps(func_call["arguments"]),
                                )
                            except:
                                pass

                elif tool_type == "code" and args:
                    code = args[0]
                    if isinstance(code, str):
                        span.set_attribute("tool.code.size", len(code))
                        span.set_attribute("tool.code.language", kwargs.get("lang", "unknown"))

                result = wrapped(*args, **kwargs)

                self._process_tool_result(span, result, tool_type)

                return result

        return wrapper

    def _group_chat_select_speaker_wrapper(self, tracer):
        """Wrapper for capturing which agent is selected to speak in a group chat."""

        def wrapper(wrapped, instance, args, kwargs):
            previous_speaker_name = "unknown"
            messages = getattr(instance, "messages", [])
            if messages and len(messages) > 0:
                previous_speaker_name = messages[-1].get("name", "unknown")

            selected_speaker = wrapped(*args, **kwargs)

            if not selected_speaker:
                return selected_speaker

            current_speaker_name = getattr(selected_speaker, "name", "unnamed")

            with create_span(
                tracer, "ag2.handoff", kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                span.set_attribute(AgentAttributes.FROM_AGENT, previous_speaker_name)
                span.set_attribute(AgentAttributes.TO_AGENT, current_speaker_name)
                span.set_attribute(AgentAttributes.AGENT_NAME, current_speaker_name)
                span.set_attribute(AgentAttributes.AGENT_ROLE, selected_speaker.__class__.__name__)

                system_message = getattr(selected_speaker, "system_message", "")
                if system_message:
                    system_message = self._safe_str(system_message)
                    span.set_attribute(SpanAttributes.LLM_REQUEST_SYSTEM_INSTRUCTION, system_message)

                self._set_llm_config_attributes(span, getattr(selected_speaker, "llm_config", None))

                if messages:
                    for msg in reversed(messages):
                        if msg.get("name") == current_speaker_name:
                            if "metadata" in msg and isinstance(msg["metadata"], dict):
                                meta = msg["metadata"]
                                if "model" in meta:
                                    span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, meta["model"])
                            break

                span.set_attribute("groupchat.role", "participant")

            return selected_speaker

        return wrapper

    # Helper methods
    def _safe_str(self, value):
        """Safely convert value to string."""
        if value is None:
            return ""
        return str(value) if not isinstance(value, str) else value

    def _extract_message_content(self, message):
        """Extract content from various message formats."""
        if isinstance(message, dict):
            content = message.get("content", "")
            return self._safe_str(content)
        elif isinstance(message, str):
            return message
        else:
            return str(message)

    def _extract_chat_history(self, span, initiator, recipient):
        """Extract chat history information."""
        try:
            # Get recipient chat history
            recipient_chat_history = getattr(recipient, "chat_history", [])

            if recipient_chat_history:
                message_count = len(recipient_chat_history)
                span.set_attribute("conversation.message_count", message_count)

                # Record sample of conversation messages
                if message_count > 0:
                    first_msg = recipient_chat_history[0]
                    last_msg = recipient_chat_history[-1]

                    self._set_message_attributes(span, first_msg, 0, "prompt")
                    self._set_message_attributes(span, last_msg, 0, "completion")

                    # Check for tool usage
                    span.set_attribute("chat.used_tools", "tool_calls" in last_msg)

                    # Capture metadata
                    if "metadata" in last_msg and isinstance(last_msg["metadata"], dict):
                        meta = last_msg["metadata"]
                        if "model" in meta:
                            span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, meta["model"])

        except Exception as e:
            logger.debug(f"Could not extract chat history: {e}")

    def _set_message_attributes(self, span, message, index, prefix):
        """Set message attributes on span."""
        if isinstance(message, dict):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            name = message.get("name", "unknown")

            span.set_attribute(f"messaging.{prefix}.role.{index}", role)
            content = self._safe_str(content)
            span.set_attribute(f"messaging.{prefix}.content.{index}", content)
            span.set_attribute(f"messaging.{prefix}.speaker.{index}", name)

    def _process_tool_result(self, span, result, tool_type):
        """Process and set tool execution result attributes."""
        if tool_type == "function" and isinstance(result, tuple) and len(result) > 0:
            success = result[0] if isinstance(result[0], bool) else False
            span.set_attribute(ToolAttributes.TOOL_STATUS, "success" if success else "error")

            if len(result) > 1 and isinstance(result[1], dict):
                try:
                    span.set_attribute(ToolAttributes.TOOL_RESULT, json.dumps(result[1]))
                except:
                    pass

        if tool_type == "code" and isinstance(result, tuple) and len(result) >= 3:
            exit_code = result[0]
            span.set_attribute("exit_code", exit_code)
            span.set_attribute(ToolAttributes.TOOL_STATUS, "success" if exit_code == 0 else "error")

            if len(result) > 1 and result[1]:
                stdout = self._safe_str(result[1])
                span.set_attribute("tool.code.stdout", stdout)

            if len(result) > 2 and result[2]:
                stderr = self._safe_str(result[2])
                span.set_attribute("tool.code.stderr", stderr)

    def _capture_conversation_summary(self, span, agent, response):
        """Extract and record conversation summary data."""
        if not hasattr(response, "chat_history"):
            return

        try:
            chat_history = getattr(response, "chat_history", [])
            message_count = len(chat_history)
            user_messages = sum(1 for msg in chat_history if msg.get("role") == "user")
            assistant_messages = sum(1 for msg in chat_history if msg.get("role") == "assistant")

            span.set_attribute("conversation.message_count", message_count)
            span.set_attribute("conversation.user_messages", user_messages)
            span.set_attribute("conversation.assistant_messages", assistant_messages)

            # Set prompts and completions
            span.set_attribute(SpanAttributes.LLM_PROMPTS, user_messages)
            span.set_attribute(SpanAttributes.LLM_COMPLETIONS, assistant_messages)
            if message_count > 0:
                for i, msg in enumerate(chat_history[: min(2, message_count)]):
                    self._set_message_attributes(span, msg, i, "prompt")

                if message_count > 2:
                    self._set_message_attributes(span, chat_history[-1], 0, "completion")
        except Exception as e:
            logger.error(f"[AG2 DEBUG] Error capturing conversation summary: {e}")

    def _capture_group_chat_summary(self, span, manager, result):
        """Extract and record group chat summary data."""
        try:
            messages = getattr(manager.groupchat, "messages", [])
            message_count = len(messages)

            agent_message_counts = {}
            for message in messages:
                agent_name = message.get("name", "unknown")
                if agent_name not in agent_message_counts:
                    agent_message_counts[agent_name] = 0
                agent_message_counts[agent_name] += 1

            span.set_attribute("conversation.message_count", message_count)

            for agent_name, count in agent_message_counts.items():
                span.set_attribute(f"conversation.agent_messages.{agent_name}", count)

            if hasattr(manager.groupchat, "speaker_selection_method"):
                span.set_attribute(
                    "groupchat.speaker_selection_method", str(manager.groupchat.speaker_selection_method)
                )

            if message_count > 0:
                for i, msg in enumerate(messages[: min(2, message_count)]):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    name = msg.get("name", "unknown")

                    span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=i), role)
                    content = self._safe_str(content)
                    span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=i), content)
                    span.set_attribute(MessageAttributes.PROMPT_SPEAKER.format(i=i), name)

                if message_count > 2:
                    last_msg = messages[-1]
                    role = last_msg.get("role", "unknown")
                    content = last_msg.get("content", "")
                    name = last_msg.get("name", "unknown")

                    span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), role)
                    content = self._safe_str(content)
                    span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), content)
                    span.set_attribute(MessageAttributes.COMPLETION_SPEAKER.format(i=0), name)

                    if "metadata" in last_msg and isinstance(last_msg["metadata"], dict):
                        meta = last_msg["metadata"]
                        if "model" in meta:
                            span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, meta["model"])
        except Exception as e:
            logger.error(f"Error capturing group chat summary: {e}")
