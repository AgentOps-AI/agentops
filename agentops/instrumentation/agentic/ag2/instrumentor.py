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
        """Initialize attribute manager."""
        self._attribute_manager = SpanAttributeManager(service_name="agentops", deployment_environment="production")

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for AG2 methods."""
        methods_to_wrap = [
            ("autogen.agentchat.conversable_agent", "ConversableAgent.__init__", self._agent_init_wrapper),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.run", self._agent_run_wrapper),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.initiate_chat", self._initiate_chat_wrapper),
            ("autogen.agentchat.groupchat", "GroupChatManager.run_chat", self._group_chat_run_wrapper),
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
                logger.debug(f"Successfully wrapped {method}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to wrap {method}: {e}")

    def _custom_unwrap(self, **kwargs):
        """Remove instrumentation from AG2."""
        # Unwrap all instrumented methods
        methods_to_unwrap = [
            ("autogen.agentchat.conversable_agent", "ConversableAgent.__init__"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.run"),
            ("autogen.agentchat.conversable_agent", "ConversableAgent.initiate_chat"),
            ("autogen.agentchat.groupchat", "GroupChatManager.run_chat"),
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
            except Exception as e:
                logger.error(f"Error in agent init instrumentation: {e}")
                return wrapped(*args, **kwargs)

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

            span_name = f"ag2.chat.{initiator_name}_to_{recipient_name}"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                span.set_attribute(AgentAttributes.FROM_AGENT, initiator_name)
                span.set_attribute(AgentAttributes.TO_AGENT, recipient_name)
                span.set_attribute("ag2.chat.type", "individual")
                span.set_attribute("ag2.chat.initiator", initiator_name)
                span.set_attribute("ag2.chat.recipient", recipient_name)

                # Extract system messages and LLM configs
                self._extract_agent_attributes(span, instance, recipient_agent)

                # Extract initial message
                initial_message = kwargs.get("message", "")
                if initial_message:
                    initial_message = self._safe_str(initial_message)
                    span.set_attribute("ag2.chat.initial_message", initial_message)

                result = wrapped(*args, **kwargs)

                # Extract chat history after completion
                self._extract_chat_history(span, instance, recipient_agent)

                return result

        return wrapper

    def _agent_run_wrapper(self, tracer):
        """Wrapper for capturing agent run as a summary."""

        def wrapper(wrapped, instance, args, kwargs):
            agent_name = getattr(instance, "name", "unnamed_agent")
            agent_type = getattr(instance, "_agentops_metadata", {}).get("type", "ConversableAgent")
            span_name = f"ag2.agent.{agent_name}.run"

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
                    span.set_attribute("ag2.run.input_message", content_to_set)

                # Initialize completions and prompts count
                span.set_attribute(SpanAttributes.LLM_COMPLETIONS, 0)
                span.set_attribute(SpanAttributes.LLM_PROMPTS, 0)

                response = wrapped(*args, **kwargs)

                if hasattr(response, "chat_history"):
                    self._capture_conversation_summary(span, instance, response)
                elif hasattr(response, "get") and callable(response.get):
                    model_info = response.get("model", "")
                    if model_info:
                        span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, model_info)

                span.set_attribute(WorkflowAttributes.WORKFLOW_STEP_STATUS, "completed")
                return response

        return wrapper

    def _group_chat_run_wrapper(self, tracer):
        """Wrapper for capturing group chat execution."""

        def wrapper(wrapped, instance, args, kwargs):
            with create_span(
                tracer, "ag2.groupchat.run", kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                group_chat = getattr(instance, "groupchat", None)
                agents = getattr(group_chat, "agents", []) if group_chat else []
                agent_names = [getattr(agent, "name", f"agent_{i}") for i, agent in enumerate(agents)]

                span.set_attribute(AgentAttributes.AGENT_ROLE, "GroupChatManager")
                span.set_attribute(AgentAttributes.AGENT_NAME, getattr(instance, "name", "unnamed_manager"))
                span.set_attribute("ag2.groupchat.agents", ", ".join(agent_names))
                span.set_attribute("ag2.groupchat.agent_count", len(agents))

                # Capture input message if available
                message = kwargs.get("message", "")
                if message:
                    content_to_set = self._extract_message_content(message)
                    span.set_attribute("ag2.groupchat.input_message", content_to_set)

                result = wrapped(*args, **kwargs)
                self._capture_group_chat_summary(span, instance, result)

                return result

        return wrapper

    def _tool_execution_wrapper(self, tracer, tool_type):
        """Wrapper for capturing tool execution."""

        def wrapper(wrapped, instance, args, kwargs):
            span_name = f"ag2.tool.{tool_type}"

            with create_span(
                tracer, span_name, kind=SpanKind.INTERNAL, attribute_manager=self._attribute_manager
            ) as span:
                agent_name = getattr(instance, "name", "unnamed_agent")
                span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)
                span.set_attribute(ToolAttributes.TOOL_NAME, tool_type)

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
                        span.set_attribute("ag2.tool.code.size", len(code))
                        span.set_attribute("ag2.tool.code.language", kwargs.get("lang", "unknown"))

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

                span.set_attribute("ag2.groupchat.role", "participant")

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

    def _extract_agent_attributes(self, span, initiator, recipient):
        """Extract and set agent attributes on span."""
        # Extract system message from both agents
        initiator_system_msg = getattr(initiator, "system_message", "")
        if initiator_system_msg:
            initiator_system_msg = self._safe_str(initiator_system_msg)
            span.set_attribute("ag2.initiator.system_message", initiator_system_msg)

        recipient_system_msg = getattr(recipient, "system_message", "")
        if recipient_system_msg:
            recipient_system_msg = self._safe_str(recipient_system_msg)
            span.set_attribute(SpanAttributes.LLM_REQUEST_SYSTEM_INSTRUCTION, recipient_system_msg)

        # Extract LLM config from both agents
        initiator_llm_config = getattr(initiator, "llm_config", {})
        if isinstance(initiator_llm_config, dict) and initiator_llm_config:
            model = initiator_llm_config.get("model", "unknown")
            span.set_attribute("ag2.initiator.model", model)

        recipient_llm_config = getattr(recipient, "llm_config", {})
        self._set_llm_config_attributes(span, recipient_llm_config)

    def _extract_chat_history(self, span, initiator, recipient):
        """Extract chat history information."""
        try:
            # Get initiator chat history
            initiator_chat_history = getattr(initiator, "chat_history", [])
            if initiator_chat_history:
                span.set_attribute("ag2.initiator.message_count", len(initiator_chat_history))

            # Get recipient chat history
            recipient_chat_history = getattr(recipient, "chat_history", [])
            if recipient_chat_history:
                message_count = len(recipient_chat_history)
                span.set_attribute("ag2.conversation.message_count", message_count)

                # Record sample of conversation messages
                if message_count > 0:
                    self._set_message_attributes(span, recipient_chat_history[0], 0, "prompt")
                    self._set_message_attributes(span, recipient_chat_history[-1], 0, "completion")

                    # Check for tool usage
                    last_msg = recipient_chat_history[-1]
                    span.set_attribute("ag2.chat.used_tools", "tool_calls" in last_msg)

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
                span.set_attribute("ag2.tool.code.stdout", stdout)

            if len(result) > 2 and result[2]:
                stderr = self._safe_str(result[2])
                span.set_attribute("ag2.tool.code.stderr", stderr)

    def _capture_conversation_summary(self, span, agent, response):
        """Extract and record conversation summary data."""
        if not hasattr(response, "chat_history"):
            return

        try:
            chat_history = getattr(response, "chat_history", [])
            message_count = len(chat_history)

            user_messages = sum(1 for msg in chat_history if msg.get("role") == "user")
            assistant_messages = sum(1 for msg in chat_history if msg.get("role") == "assistant")

            span.set_attribute("ag2.conversation.message_count", message_count)
            span.set_attribute("ag2.conversation.user_messages", user_messages)
            span.set_attribute("ag2.conversation.assistant_messages", assistant_messages)

            # Set prompts and completions
            span.set_attribute(SpanAttributes.LLM_PROMPTS, user_messages)
            span.set_attribute(SpanAttributes.LLM_COMPLETIONS, assistant_messages)

            if message_count > 0:
                for i, msg in enumerate(chat_history[: min(2, message_count)]):
                    self._set_message_attributes(span, msg, i, "prompt")

                if message_count > 2:
                    self._set_message_attributes(span, chat_history[-1], 0, "completion")
        except Exception as e:
            logger.error(f"Error capturing conversation summary: {e}")

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

            span.set_attribute("ag2.conversation.message_count", message_count)

            for agent_name, count in agent_message_counts.items():
                span.set_attribute(f"ag2.conversation.agent_messages.{agent_name}", count)

            if hasattr(manager.groupchat, "speaker_selection_method"):
                span.set_attribute(
                    "ag2.groupchat.speaker_selection_method", str(manager.groupchat.speaker_selection_method)
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
