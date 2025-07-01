"""Agno Agent session metrics attributes handler."""

from typing import Optional, Tuple, Dict, Any

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes


def get_metrics_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract span attributes for Agent._set_session_metrics calls.

    Args:
        args: Positional arguments passed to the _set_session_metrics method (self, run_messages)
        kwargs: Keyword arguments passed to the _set_session_metrics method
        return_value: The return value from the _set_session_metrics method

    Returns:
        A dictionary of span attributes to be set on the metrics span
    """
    attributes: AttributeMap = {}

    # Base attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = "llm"
    attributes[SpanAttributes.LLM_SYSTEM] = "agno"
    attributes[SpanAttributes.AGENTOPS_ENTITY_NAME] = "LLM"

    # Initialize usage tracking variables
    usage_data = {}

    # Initialize counters for indexed messages
    prompt_count = 0
    completion_count = 0

    # Extract agent and run_messages from args (self, run_messages)
    if args and len(args) >= 2:
        agent = args[0]  # self (Agent instance)
        run_messages = args[1]  # RunMessages object

        # Add agent display name for LLM calls
        if hasattr(agent, "name") and agent.name:
            attributes["agno.llm.display_name"] = f"{agent.name} → LLM"

        # Model information - get additional request parameters if available
        if hasattr(agent, "model") and agent.model:
            model = agent.model
            # Set model ID first
            if hasattr(model, "id"):
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = str(model.id)
                attributes[SpanAttributes.LLM_RESPONSE_MODEL] = str(model.id)
            # Additional model parameters
            if hasattr(model, "temperature") and model.temperature is not None:
                attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = str(model.temperature)
            if hasattr(model, "max_tokens") and model.max_tokens is not None:
                attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = str(model.max_tokens)
            if hasattr(model, "top_p") and model.top_p is not None:
                attributes[SpanAttributes.LLM_REQUEST_TOP_P] = str(model.top_p)
            if hasattr(model, "provider"):
                attributes["agno.model.provider"] = str(model.provider)

            # Add model class name for better identification (with null check)
            if hasattr(model, "__class__") and hasattr(model.__class__, "__name__"):
                model_class = model.__class__.__name__
                attributes["agno.model.class"] = model_class

        if hasattr(run_messages, "messages") and run_messages.messages:
            messages = run_messages.messages

            # Initialize token tracking
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_output_tokens = 0
            total_input_tokens = 0
            total_tokens = 0
            total_time = 0.0

            # Process messages to create individual indexed gen_ai.prompt.{i} and gen_ai.completion.{i} attributes
            for i, msg in enumerate(messages):
                # Extract message content for prompts/completions
                if hasattr(msg, "role") and hasattr(msg, "content"):
                    # Only process messages with actual content
                    if msg.content is not None and str(msg.content).strip() != "" and str(msg.content) != "None":
                        content = str(msg.content)
                        # No truncation - keep full content for observability

                        if msg.role == "user":
                            attributes[f"{SpanAttributes.LLM_PROMPTS}.{prompt_count}.role"] = "user"
                            attributes[f"{SpanAttributes.LLM_PROMPTS}.{prompt_count}.content"] = content
                            prompt_count += 1
                        elif msg.role == "assistant":
                            attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_count}.role"] = "assistant"
                            attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{completion_count}.content"] = content
                            completion_count += 1
                        elif msg.role == "system":
                            attributes[f"{SpanAttributes.LLM_PROMPTS}.{prompt_count}.role"] = "system"
                            attributes[f"{SpanAttributes.LLM_PROMPTS}.{prompt_count}.content"] = content
                            prompt_count += 1

                # Extract token metrics from message
                if hasattr(msg, "metrics") and msg.metrics:
                    metrics = msg.metrics

                    # Handle different token metric patterns
                    if hasattr(metrics, "prompt_tokens") and metrics.prompt_tokens > 0:
                        total_prompt_tokens += metrics.prompt_tokens
                    if hasattr(metrics, "completion_tokens") and metrics.completion_tokens > 0:
                        total_completion_tokens += metrics.completion_tokens
                    if hasattr(metrics, "total_tokens") and metrics.total_tokens > 0:
                        total_tokens += metrics.total_tokens
                    # For messages that only have output_tokens
                    if hasattr(metrics, "output_tokens") and metrics.output_tokens > 0:
                        total_output_tokens += metrics.output_tokens
                    if hasattr(metrics, "input_tokens") and metrics.input_tokens > 0:
                        total_input_tokens += metrics.input_tokens
                    if hasattr(metrics, "time") and metrics.time:
                        total_time += metrics.time

        # Token metrics from agent session metrics
        if hasattr(agent, "session_metrics") and agent.session_metrics:
            session_metrics = agent.session_metrics

            # Try to get model name from session metrics if not already set
            if SpanAttributes.LLM_REQUEST_MODEL not in attributes:
                if hasattr(session_metrics, "model") and session_metrics.model:
                    model_id = str(session_metrics.model)
                    attributes[SpanAttributes.LLM_REQUEST_MODEL] = model_id
                    attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model_id

            # Only set token variables if the attributes actually exist
            session_prompt_tokens = None
            session_completion_tokens = None
            session_output_tokens = None
            session_input_tokens = None
            session_total_tokens = None

            if hasattr(session_metrics, "prompt_tokens"):
                session_prompt_tokens = session_metrics.prompt_tokens

            if hasattr(session_metrics, "completion_tokens"):
                session_completion_tokens = session_metrics.completion_tokens

            if hasattr(session_metrics, "output_tokens"):
                session_output_tokens = session_metrics.output_tokens

            if hasattr(session_metrics, "input_tokens"):
                session_input_tokens = session_metrics.input_tokens

            if hasattr(session_metrics, "total_tokens"):
                session_total_tokens = session_metrics.total_tokens

            # For Anthropic, output_tokens represents completion tokens
            if session_output_tokens is not None and session_output_tokens > 0:
                if session_completion_tokens is None or session_completion_tokens == 0:
                    session_completion_tokens = session_output_tokens

            # For some providers, input_tokens represents prompt tokens
            if session_input_tokens is not None and session_input_tokens > 0:
                if session_prompt_tokens is None or session_prompt_tokens == 0:
                    session_prompt_tokens = session_input_tokens

            # Only set token attributes if we have actual values
            if session_total_tokens is not None and session_total_tokens > 0:
                usage_data["total_tokens"] = session_total_tokens

                # Set breakdown if available
                if session_prompt_tokens is not None and session_prompt_tokens > 0:
                    usage_data["prompt_tokens"] = session_prompt_tokens
                if session_completion_tokens is not None and session_completion_tokens > 0:
                    usage_data["completion_tokens"] = session_completion_tokens

            # Additional token types from session metrics - only set if present
            if hasattr(session_metrics, "cached_tokens") and session_metrics.cached_tokens > 0:
                usage_data["cache_read_input_tokens"] = session_metrics.cached_tokens
            if hasattr(session_metrics, "reasoning_tokens") and session_metrics.reasoning_tokens > 0:
                usage_data["reasoning_tokens"] = session_metrics.reasoning_tokens

        # If we don't have token data from session metrics, try message aggregation
        if "total_tokens" not in usage_data:
            # Set aggregated token usage from messages
            if total_prompt_tokens > 0 or total_input_tokens > 0:
                usage_data["prompt_tokens"] = total_prompt_tokens or total_input_tokens
            if total_completion_tokens > 0 or total_output_tokens > 0:
                usage_data["completion_tokens"] = total_completion_tokens or total_output_tokens
            if total_tokens > 0:
                usage_data["total_tokens"] = total_tokens

        # Extract user message info if available
        if hasattr(run_messages, "user_message") and run_messages.user_message:
            user_msg = run_messages.user_message
            if hasattr(user_msg, "content"):
                content = str(user_msg.content)
                attributes["agno.metrics.user_input"] = content

    # Set individual LLM usage attributes only for values we actually have
    if "prompt_tokens" in usage_data:
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage_data["prompt_tokens"]
    if "completion_tokens" in usage_data:
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage_data["completion_tokens"]
    if "total_tokens" in usage_data:
        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage_data["total_tokens"]
    if "cache_read_input_tokens" in usage_data:
        attributes[SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS] = usage_data["cache_read_input_tokens"]
    if "reasoning_tokens" in usage_data:
        attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = usage_data["reasoning_tokens"]

    # But only if we have any usage data
    if usage_data:
        for key, value in usage_data.items():
            attributes[f"gen_ai.usage.{key}"] = value

    return attributes
