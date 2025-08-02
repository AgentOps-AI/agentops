"""Common wrapper methods for AutoGen agent instrumentors.

This module provides base wrapper methods that are shared across all AutoGen agent types
to avoid code duplication while allowing specific agents to add their unique methods.
"""

import logging
from opentelemetry.trace import SpanKind, Status, StatusCode
import inspect
from agentops.instrumentation.common import SpanAttributeManager, create_span
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import AgentOpsSpanKindValues
from ..utils.common import (
    AutoGenSpanManager,
    extract_agent_attributes,
    safe_str,
    instrument_coroutine,
    instrument_async_generator,
)

logger = logging.getLogger(__name__)


class CommonAgentWrappers:
    """Base class with common wrapper methods for all AutoGen agents."""

    def __init__(self, tracer, attribute_manager: SpanAttributeManager):
        self.tracer = tracer
        self.attribute_manager = attribute_manager
        self.span_manager = AutoGenSpanManager(tracer, attribute_manager)

    def _create_agent_wrapper(self):
        """Common wrapper for capturing agent creation."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                # Extract agent attributes
                attributes = extract_agent_attributes(instance, args, kwargs)
                agent_name = attributes["name"]
                agent_type = attributes["type"]

                # Create the create_agent span
                span_name = f"create_agent {agent_name}.workflow"

                if not self.tracer:
                    return wrapped(*args, **kwargs)

                # Create the span using a context-manager so lifecycle is automatic
                with create_span(
                    self.tracer,
                    span_name,
                    kind=SpanKind.CLIENT,
                    attribute_manager=self.attribute_manager,
                ) as span:
                    try:
                        # Set base attributes
                        self.span_manager.set_base_attributes(span, agent_name, "create_agent")
                        span.set_attribute("gen_ai.agent.type", agent_type)

                        # Set description if available
                        if "description" in attributes:
                            span.set_attribute("gen_ai.agent.description", attributes["description"])

                        # Call the original __init__ method
                        result = wrapped(*args, **kwargs)

                        # Store metadata on the instance for future use
                        if hasattr(instance, "__dict__"):
                            instance._agentops_metadata = {
                                "name": agent_name,
                                "type": agent_type,
                                "system": "autogen",
                            }

                        return result

                    except Exception as e:
                        # Span status/error handling will be managed by create_span, but we log for visibility
                        logger.debug(f"[AutoGen DEBUG] Error during create_agent instrumentation: {e}")
                        raise

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in _create_agent_wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper

    def _run_wrapper(self):
        """Common wrapper for capturing agent run method calls."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                agent_name = getattr(instance, "name", "unnamed_agent")
                span_name = f"agent.run.{agent_name}.agent"

                # Call the original method first to get the result
                result = wrapped(*args, **kwargs)

                # Check if result is async and wrap it

                if inspect.iscoroutine(result):
                    # Wrap coroutine to keep span active during execution
                    async def instrumented_coroutine():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set span attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "agent.run")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                            # Get task information
                            task = kwargs.get("task") or (args[0] if args else None)
                            if task and isinstance(task, str):
                                span.set_attribute("agent.task", safe_str(task))

                            # Instrument the coroutine
                            return await instrument_coroutine(result, span, "run")

                    return instrumented_coroutine()
                else:
                    # Synchronous result
                    with self.tracer.start_as_current_span(span_name) as span:
                        span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                        span.set_attribute("gen_ai.agent.name", str(agent_name))
                        span.set_attribute("gen_ai.operation.name", "agent.run")
                        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                        # Get task information
                        task = kwargs.get("task") or (args[0] if args else None)
                        if task and isinstance(task, str):
                            span.set_attribute("agent.task", safe_str(task))

                        return result

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in agent run wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper

    def _run_stream_wrapper(self):
        """Common wrapper for capturing agent run_stream method calls."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                agent_name = getattr(instance, "name", "unnamed_agent")
                span_name = f"agent.run_stream.{agent_name}.agent"

                # Call the original method first to get the result
                result = wrapped(*args, **kwargs)

                # Check if result is async and wrap it
                if inspect.isasyncgen(result):
                    # Wrap async generator to keep span active during execution
                    async def instrumented_async_generator():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set span attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "agent.run_stream")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                            # Get task information
                            task = kwargs.get("task") or (args[0] if args else None)
                            if task and isinstance(task, str):
                                span.set_attribute("agent.task", safe_str(task))

                            # Instrument the async generator
                            async for item in instrument_async_generator(result, span, "run_stream"):
                                yield item

                    return instrumented_async_generator()

                elif inspect.iscoroutine(result):
                    # Wrap coroutine to keep span active during execution
                    async def instrumented_coroutine():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set span attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "agent.run_stream")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                            # Get task information
                            task = kwargs.get("task") or (args[0] if args else None)
                            if task and isinstance(task, str):
                                span.set_attribute("agent.task", safe_str(task))

                            # Instrument the coroutine
                            return await instrument_coroutine(result, span, "run_stream")

                    return instrumented_coroutine()
                else:
                    # Synchronous result
                    with self.tracer.start_as_current_span(span_name) as span:
                        span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                        span.set_attribute("gen_ai.agent.name", str(agent_name))
                        span.set_attribute("gen_ai.operation.name", "agent.run_stream")
                        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")

                        # Get task information
                        task = kwargs.get("task") or (args[0] if args else None)
                        if task and isinstance(task, str):
                            span.set_attribute("agent.task", safe_str(task))

                        return result

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in agent run_stream wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper

    def _on_messages_wrapper(self):
        """Common wrapper for capturing agent on_messages method calls."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                agent_name = getattr(instance, "name", "unnamed_agent")
                span_name = f"agent.on_messages.{agent_name}.agent"

                # Call the original method first to get the result
                result = wrapped(*args, **kwargs)

                # Check if result is async and wrap it
                if inspect.iscoroutine(result):
                    # Wrap coroutine to keep span active during execution
                    async def instrumented_coroutine():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set span attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "agent.on_messages")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")
                            span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)

                            # Get messages information
                            messages = kwargs.get("messages") or (args[0] if args else None)
                            if messages and hasattr(messages, "__len__"):
                                span.set_attribute("agent.input_message_count", len(messages))

                            # Instrument the coroutine
                            return await instrument_coroutine(result, span, "on_messages")

                    return instrumented_coroutine()
                else:
                    # Synchronous result
                    with self.tracer.start_as_current_span(span_name) as span:
                        span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                        span.set_attribute("gen_ai.agent.name", str(agent_name))
                        span.set_attribute("gen_ai.operation.name", "agent.on_messages")
                        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")
                        span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)

                        # Get messages information
                        messages = kwargs.get("messages") or (args[0] if args else None)
                        if messages and hasattr(messages, "__len__"):
                            span.set_attribute("agent.input_message_count", len(messages))

                        return result

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in agent on_messages wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper

    def _on_messages_stream_wrapper(self):
        """Common wrapper for capturing agent on_messages_stream method calls."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                agent_name = getattr(instance, "name", "unnamed_agent")
                span_name = f"agent.on_messages_stream.{agent_name}.agent"

                # Call the original method first to get the result
                result = wrapped(*args, **kwargs)

                # Check if result is async and wrap it
                if inspect.isasyncgen(result):
                    # Wrap async generator to keep span active during execution
                    async def instrumented_async_generator():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set span attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "agent.on_messages_stream")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")
                            span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)

                            # Get messages information
                            messages = kwargs.get("messages") or (args[0] if args else None)
                            if messages and hasattr(messages, "__len__"):
                                span.set_attribute("agent.input_message_count", len(messages))

                            # Track streaming progress
                            item_count = 0
                            event_types = set()

                            # Instrument the async generator
                            async for item in instrument_async_generator(result, span, "on_messages_stream"):
                                item_count += 1
                                item_type = type(item).__name__
                                event_types.add(item_type)

                                # Update streaming metrics
                                span.set_attribute("agent.stream.item_count", item_count)
                                span.set_attribute("agent.stream.event_types", ",".join(sorted(event_types)))

                                yield item

                    return instrumented_async_generator()

                elif inspect.iscoroutine(result):
                    # Wrap coroutine to keep span active during execution
                    async def instrumented_coroutine():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set span attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "agent.on_messages_stream")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")
                            span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)

                            # Get messages information
                            messages = kwargs.get("messages") or (args[0] if args else None)
                            if messages and hasattr(messages, "__len__"):
                                span.set_attribute("agent.input_message_count", len(messages))

                            # Instrument the coroutine
                            return await instrument_coroutine(result, span, "on_messages_stream")

                    return instrumented_coroutine()
                else:
                    # Synchronous result
                    with self.tracer.start_as_current_span(span_name) as span:
                        span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                        span.set_attribute("gen_ai.agent.name", str(agent_name))
                        span.set_attribute("gen_ai.operation.name", "agent.on_messages_stream")
                        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENT.value)
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "agent")
                        span.set_attribute(AgentAttributes.AGENT_NAME, agent_name)

                        # Get messages information
                        messages = kwargs.get("messages") or (args[0] if args else None)
                        if messages and hasattr(messages, "__len__"):
                            span.set_attribute("agent.input_message_count", len(messages))

                        return result

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in agent on_messages_stream wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper

    def _call_llm_wrapper(self):
        """Generic wrapper for capturing LLM interactions."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                agent_name = kwargs.get("agent_name")

                if not agent_name or isinstance(agent_name, property):
                    possible_name = getattr(instance, "name", None)
                    agent_name = possible_name if isinstance(possible_name, str) else "unnamed_agent"

                span_name = f"_call_llm {agent_name}.llm"

                # Call the original method first to get the result
                result = wrapped(*args, **kwargs)

                # Check if result is async and wrap it
                if inspect.isasyncgen(result):
                    # Wrap async generator to keep span active during execution
                    async def instrumented_async_generator():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set common attributes for all LLM calls
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "_call_llm")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.LLM.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "llm")

                            # Extract *all* prompt messages
                            messages_list = None
                            if "messages" in kwargs and kwargs["messages"]:
                                messages_list = kwargs["messages"]
                            else:
                                # Try positional args (rare for _call_llm)
                                if args:
                                    first_arg = args[0]
                                    if hasattr(first_arg, "messages"):
                                        messages_list = first_arg.messages
                                    elif hasattr(first_arg, "get"):
                                        try:
                                            messages_list = first_arg.get("messages")
                                        except Exception:
                                            messages_list = None
                                # Try AutoGen model_context object
                                if messages_list is None and "model_context" in kwargs:
                                    mc = kwargs["model_context"]
                                    if mc is not None:
                                        if hasattr(mc, "_messages"):
                                            messages_list = getattr(mc, "_messages", None)
                                        elif hasattr(mc, "messages"):
                                            messages_list = mc.messages

                            if messages_list:
                                span.set_attribute("gen_ai.request.messages.count", len(messages_list))

                                # Start index after system messages already recorded (if any)
                                prompt_index = len(kwargs.get("system_messages", []))

                                for msg in messages_list:
                                    content = None
                                    role = "user"

                                    if isinstance(msg, str):
                                        content = msg
                                        role = "user"
                                    else:
                                        content = getattr(msg, "content", None)
                                        role = str(getattr(msg, "role", "user"))

                                    if content is None:
                                        continue

                                    span.set_attribute(f"gen_ai.prompt.{prompt_index}.content", safe_str(content))
                                    span.set_attribute(f"gen_ai.prompt.{prompt_index}.role", role)
                                    prompt_index += 1

                            # Extract model information from kwargs
                            model_client = kwargs.get("model_client")
                            if model_client:
                                # Try different attributes to get model name
                                model_name = None
                                if hasattr(model_client, "model"):
                                    model_name = getattr(model_client, "model", None)
                                elif hasattr(model_client, "_model"):
                                    model_name = getattr(model_client, "_model", None)
                                elif hasattr(model_client, "model_name"):
                                    model_name = getattr(model_client, "model_name", None)
                                elif hasattr(model_client, "_resolved_model"):
                                    model_name = getattr(model_client, "_resolved_model", None)

                                if model_name:
                                    span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, str(model_name))

                            # Extract system messages list if present
                            system_messages = kwargs.get("system_messages", [])
                            if system_messages:
                                span.set_attribute("gen_ai.request.system_message_count", len(system_messages))
                                # Extract first system message content
                                if hasattr(system_messages[0], "content"):
                                    span.set_attribute(
                                        "gen_ai.request.system_message", safe_str(system_messages[0].content)
                                    )

                                # Already counted above, but also record explicit system prompts for completeness
                                for idx, sm in enumerate(system_messages):
                                    if hasattr(sm, "content") and sm.content:
                                        span.set_attribute(f"gen_ai.prompt.{idx}.content", safe_str(sm.content))
                                        span.set_attribute(f"gen_ai.prompt.{idx}.role", "system")

                            # Track agent name from kwargs
                            if "agent_name" in kwargs:
                                span.set_attribute("gen_ai.agent.name", kwargs["agent_name"])

                            # Track completion data
                            accumulated_content = ""
                            total_tokens = 0
                            prompt_tokens = 0
                            completion_tokens = 0
                            finish_reason = None
                            chunk_count = 0

                            try:
                                # Process the async generator
                                async for chunk in result:
                                    chunk_count += 1

                                    # AutoGen uses different event types
                                    if hasattr(chunk, "__class__"):
                                        # Handle different AutoGen event types
                                        if hasattr(chunk, "content"):
                                            # This might be a completion event
                                            content = getattr(chunk, "content", None)
                                            if content:
                                                accumulated_content += str(content)

                                        # Try to extract usage from the chunk
                                        if hasattr(chunk, "usage"):
                                            usage = chunk.usage

                                            if usage:
                                                # Prefer individual counts if available so we can always compute totals
                                                prompt_tokens = getattr(usage, "prompt_tokens", prompt_tokens)
                                                completion_tokens = getattr(
                                                    usage, "completion_tokens", completion_tokens
                                                )
                                                total_tokens = getattr(
                                                    usage, "total_tokens", prompt_tokens + completion_tokens
                                                )

                                                # Set both legacy (input/output) and standard (prompt/completion) keys for compatibility
                                                span.set_attribute(
                                                    SpanAttributes.LLM_USAGE_PROMPT_TOKENS, prompt_tokens
                                                )
                                                span.set_attribute(
                                                    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, completion_tokens
                                                )
                                                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                                                # Legacy naming still used by some dashboards
                                                span.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
                                                span.set_attribute("gen_ai.usage.output_tokens", completion_tokens)

                                                # Check for finish reason within usage if present (OpenAI style)
                                                if hasattr(usage, "finish_reason") and usage.finish_reason:
                                                    finish_reason = usage.finish_reason

                                    # Also handle OpenAI-style chunks
                                    if hasattr(chunk, "choices") and chunk.choices:
                                        choice = chunk.choices[0]
                                        if hasattr(choice, "delta") and hasattr(choice.delta, "content"):
                                            if choice.delta.content:
                                                accumulated_content += choice.delta.content

                                        if hasattr(choice, "finish_reason") and choice.finish_reason:
                                            finish_reason = choice.finish_reason

                                    # Done processing usage for this chunk
                                yield chunk

                                # Set final attributes
                                if accumulated_content:
                                    span.set_attribute("gen_ai.completion.0.content", safe_str(accumulated_content))
                                    span.set_attribute("gen_ai.completion.0.content_length", len(accumulated_content))

                                if finish_reason:
                                    span.set_attribute("gen_ai.completion.0.finish_reason", finish_reason)

                                if total_tokens > 0:
                                    # Set both legacy (input/output) and standard (prompt/completion) keys for compatibility
                                    span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, prompt_tokens)
                                    span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, completion_tokens)
                                    span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                                    span.set_attribute("gen_ai.usage.input_tokens", prompt_tokens)
                                    span.set_attribute("gen_ai.usage.output_tokens", completion_tokens)

                                span.set_attribute("gen_ai.response.chunk_count", chunk_count)
                                span.set_status(Status(StatusCode.OK))

                            except Exception as e:
                                logger.debug(f"[AutoGen DEBUG] Error processing LLM stream: {e}")
                                span.set_status(Status(StatusCode.ERROR, str(e)))
                                # Re-raise to maintain original behavior
                                raise

                    return instrumented_async_generator()

                elif inspect.iscoroutine(result):
                    # Wrap coroutine to keep span active during execution
                    async def instrumented_coroutine():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set common attributes for all LLM calls
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "_call_llm")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.LLM.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "llm")

                            try:
                                # Await the result and process it
                                llm_result = await result

                                # Extract and set completion attributes from result
                                if hasattr(llm_result, "choices") and llm_result.choices:
                                    choice = llm_result.choices[0]
                                    if hasattr(choice, "message") and hasattr(choice.message, "content"):
                                        content = choice.message.content
                                        if content:
                                            span.set_attribute("gen_ai.completion.0.content", safe_str(content))

                                    if hasattr(choice, "finish_reason"):
                                        span.set_attribute("gen_ai.completion.0.finish_reason", choice.finish_reason)

                                # Extract usage information
                                if hasattr(llm_result, "usage") and llm_result.usage:
                                    if hasattr(llm_result.usage, "total_tokens"):
                                        span.set_attribute(
                                            SpanAttributes.LLM_USAGE_TOTAL_TOKENS, llm_result.usage.total_tokens
                                        )
                                    if hasattr(llm_result.usage, "prompt_tokens"):
                                        span.set_attribute(
                                            SpanAttributes.LLM_USAGE_PROMPT_TOKENS, llm_result.usage.prompt_tokens
                                        )
                                    if hasattr(llm_result.usage, "completion_tokens"):
                                        span.set_attribute(
                                            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS,
                                            llm_result.usage.completion_tokens,
                                        )

                                span.set_status(Status(StatusCode.OK))
                                return llm_result

                            except Exception as e:
                                logger.debug(f"[AutoGen DEBUG] Error processing LLM result: {e}")
                                span.set_status(Status(StatusCode.ERROR, str(e)))
                                raise

                    return instrumented_coroutine()
                else:
                    # Synchronous result
                    with self.tracer.start_as_current_span(span_name) as span:
                        span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                        span.set_attribute("gen_ai.agent.name", str(agent_name))
                        span.set_attribute("gen_ai.operation.name", "_call_llm")
                        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.LLM.value)
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "llm")

                        # For synchronous calls, we already have the result
                        # Extract completion information
                        if hasattr(result, "choices") and result.choices:
                            choice = result.choices[0]
                            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                                content = choice.message.content
                                if content:
                                    span.set_attribute("gen_ai.completion.0.content", safe_str(content))

                            if hasattr(choice, "finish_reason"):
                                span.set_attribute("gen_ai.completion.0.finish_reason", choice.finish_reason)

                        # Extract usage information
                        if hasattr(result, "usage") and result.usage:
                            if hasattr(result.usage, "total_tokens"):
                                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, result.usage.total_tokens)
                            if hasattr(result.usage, "prompt_tokens"):
                                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, result.usage.prompt_tokens)
                            if hasattr(result.usage, "completion_tokens"):
                                span.set_attribute(
                                    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, result.usage.completion_tokens
                                )

                        return result

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in _call_llm wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper

    def _execute_tool_call_wrapper(self):
        """Generic wrapper for capturing tool executions."""

        def wrapper(wrapped, instance, args, kwargs):
            try:
                agent_name = getattr(instance, "name", "unnamed_agent")

                # Extract tool information
                tool_call = args[0] if args else kwargs.get("tool_call")
                tool_name = "unknown_tool"
                if tool_call and hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
                    tool_name = tool_call.function.name

                span_name = f"tool.{tool_name}.tool"

                # Call the original method first to get the result
                result = wrapped(*args, **kwargs)

                # Check if result is async and wrap it
                if inspect.iscoroutine(result):
                    # Wrap coroutine to keep span active during execution
                    async def instrumented_coroutine():
                        with self.tracer.start_as_current_span(span_name) as span:
                            # Set tool attributes
                            span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                            span.set_attribute("gen_ai.agent.name", str(agent_name))
                            span.set_attribute("gen_ai.operation.name", "_execute_tool_call")
                            span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.TOOL.value)
                            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "tool")

                            # Extract tool arguments if available
                            if (
                                tool_call
                                and hasattr(tool_call, "function")
                                and hasattr(tool_call.function, "arguments")
                            ):
                                span.set_attribute("tool.arguments", safe_str(tool_call.function.arguments))

                            try:
                                # Await the result and capture tool output
                                tool_result = await result

                                # Attempt to derive a better tool name from the result if unknown
                                if tool_name == "unknown_tool":
                                    derived_name = None
                                    # Common Autogen pattern: (FunctionCall, FunctionExecutionResult)
                                    if isinstance(tool_result, (tuple, list)):
                                        for item in tool_result:
                                            derived_name = getattr(item, "name", None)
                                            if derived_name:
                                                break
                                    else:
                                        derived_name = getattr(tool_result, "name", None)
                                    if derived_name:
                                        tool_name_local = str(derived_name)
                                        span.update_name(f"tool.{tool_name_local}.{agent_name}.tool")
                                        span.set_attribute("tool.name", tool_name_local)

                                # Set tool result if available
                                if tool_result:
                                    span.set_attribute("tool.result", safe_str(tool_result))

                                span.set_status(Status(StatusCode.OK))
                                return tool_result

                            except Exception as e:
                                logger.debug(f"[AutoGen DEBUG] Error in tool execution: {e}")
                                span.set_status(Status(StatusCode.ERROR, str(e)))
                                raise

                    return instrumented_coroutine()
                else:
                    # Synchronous result
                    with self.tracer.start_as_current_span(span_name) as span:
                        span.set_attribute(SpanAttributes.LLM_SYSTEM, "autogen")
                        span.set_attribute("gen_ai.agent.name", str(agent_name))
                        span.set_attribute("gen_ai.operation.name", "_execute_tool_call")
                        span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.TOOL.value)
                        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, "tool")
                        span.set_attribute("tool.name", tool_name)

                        # Extract tool arguments if available
                        if tool_call and hasattr(tool_call, "function") and hasattr(tool_call.function, "arguments"):
                            span.set_attribute("tool.arguments", safe_str(tool_call.function.arguments))

                        # Set tool result if available
                        if result:
                            span.set_attribute("tool.result", safe_str(result))

                        return result

            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Error in tool execution wrapper: {e}")
                return wrapped(*args, **kwargs)

        return wrapper


# Agent Instrumentor Classes


class BaseChatAgentInstrumentor(CommonAgentWrappers):
    """Instrumentor for AutoGen BaseChatAgent."""

    def get_wrappers(self):
        """Get list of methods to wrap for BaseChatAgent."""
        # Return tuples of (class_name, method_name, wrapper_factory) to avoid circular imports
        return [
            ("BaseChatAgent", "run", lambda: self._run_wrapper()),
            ("BaseChatAgent", "run_stream", lambda: self._run_stream_wrapper()),
            ("BaseChatAgent", "on_messages", lambda: self._on_messages_wrapper()),
            ("BaseChatAgent", "on_messages_stream", lambda: self._on_messages_stream_wrapper()),
            # ("BaseChatAgent", "_call_llm", lambda: self._call_llm_wrapper()),
            # ("BaseChatAgent", "_execute_tool_call", lambda: self._execute_tool_call_wrapper()),
        ]


class AssistantAgentInstrumentor(CommonAgentWrappers):
    """Instrumentor for AutoGen AssistantAgent with specialized LLM and tool instrumentation."""

    def get_wrappers(self):
        """Get list of methods to wrap for AssistantAgent."""
        # Add all the standard agent wrappers
        wrappers = [
            ("AssistantAgent", "__init__", lambda: self._create_agent_wrapper()),
            ("AssistantAgent", "run", lambda: self._run_wrapper()),
            ("AssistantAgent", "run_stream", lambda: self._run_stream_wrapper()),
            ("AssistantAgent", "on_messages_stream", lambda: self._on_messages_stream_wrapper()),
            ("AssistantAgent", "_call_llm", lambda: self._call_llm_wrapper()),
            ("AssistantAgent", "_execute_tool_call", lambda: self._execute_tool_call_wrapper()),
        ]

        return wrappers


class UserProxyAgentInstrumentor(CommonAgentWrappers):
    """Instrumentor for AutoGen UserProxyAgent."""

    def get_wrappers(self):
        """Get list of methods to wrap for UserProxyAgent."""
        return [
            ("UserProxyAgent", "__init__", lambda: self._create_agent_wrapper()),
            ("UserProxyAgent", "run", lambda: self._run_wrapper()),
            ("UserProxyAgent", "run_stream", lambda: self._run_stream_wrapper()),
            ("UserProxyAgent", "on_messages", lambda: self._on_messages_wrapper()),
            ("UserProxyAgent", "on_messages_stream", lambda: self._on_messages_stream_wrapper()),
        ]


class CodeExecutorAgentInstrumentor(CommonAgentWrappers):
    """Instrumentor for AutoGen CodeExecutorAgent."""

    def get_wrappers(self):
        """Get list of methods to wrap for CodeExecutorAgent."""
        # Standard agent wrappers plus LLM and tool-call wrappers so we capture model usage.
        return [
            ("CodeExecutorAgent", "__init__", lambda: self._create_agent_wrapper()),
            ("CodeExecutorAgent", "run", lambda: self._run_wrapper()),
            ("CodeExecutorAgent", "run_stream", lambda: self._run_stream_wrapper()),
            ("CodeExecutorAgent", "on_messages", lambda: self._on_messages_wrapper()),
            ("CodeExecutorAgent", "on_messages_stream", lambda: self._on_messages_stream_wrapper()),
            ("CodeExecutorAgent", "_call_llm", lambda: self._call_llm_wrapper()),
            ("CodeExecutorAgent", "_reflect_on_code_block_results_flow", lambda: self._call_llm_wrapper()),
        ]


class SocietyOfMindAgentInstrumentor(CommonAgentWrappers):
    """Instrumentor for AutoGen SocietyOfMindAgent."""

    def get_wrappers(self):
        """Get list of methods to wrap for SocietyOfMindAgent."""
        return [
            ("SocietyOfMindAgent", "__init__", lambda: self._create_agent_wrapper()),
            ("SocietyOfMindAgent", "run", lambda: self._run_wrapper()),
            ("SocietyOfMindAgent", "run_stream", lambda: self._run_stream_wrapper()),
            ("SocietyOfMindAgent", "on_messages", lambda: self._on_messages_wrapper()),
            ("SocietyOfMindAgent", "on_messages_stream", lambda: self._on_messages_stream_wrapper()),
        ]
