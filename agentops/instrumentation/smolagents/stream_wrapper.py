"""Stream wrapper for SmoLAgents model streaming responses."""

import time
import uuid

from opentelemetry.trace import Status, StatusCode

from agentops.semconv.message import MessageAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes
from .attributes.model import get_stream_attributes


def model_stream_wrapper(tracer):
    """Wrapper for model streaming methods.

    Args:
        tracer: OpenTelemetry tracer

    Returns:
        Wrapped function
    """

    def wrapper(wrapped, instance, args, kwargs):
        messages = kwargs.get("messages", [])
        model_id = instance.model_id if hasattr(instance, "model_id") else "unknown"

        with tracer.start_as_current_span(
            name=f"{model_id}.generate_stream", attributes=get_stream_attributes(model_id=model_id, messages=messages)
        ) as span:
            try:
                # Start streaming
                stream = wrapped(*args, **kwargs)
                first_token_received = False
                start_time = time.time()
                accumulated_text = ""

                # Process stream
                for chunk in stream:
                    if not first_token_received:
                        first_token_received = True
                        span.set_attribute("gen_ai.time_to_first_token", time.time() - start_time)

                    # Accumulate text and update attributes
                    if hasattr(chunk, "content") and chunk.content:
                        accumulated_text += chunk.content
                        span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), accumulated_text)
                        span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")

                    yield chunk

                # Set final attributes
                span.set_attribute("gen_ai.streaming_duration", time.time() - start_time)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def agent_stream_wrapper(tracer):
    """Wrapper for agent streaming methods.

    Args:
        tracer: OpenTelemetry tracer

    Returns:
        Wrapped function
    """

    def wrapper(wrapped, instance, args, kwargs):
        task = kwargs.get("task", args[0] if args else "unknown")
        agent_type = instance.__class__.__name__
        agent_id = str(uuid.uuid4())

        with tracer.start_as_current_span(
            name=f"{agent_type}.run_stream",
            attributes={
                AgentAttributes.AGENT_ID: agent_id,
                AgentAttributes.AGENT_NAME: agent_type,
                AgentAttributes.AGENT_ROLE: "executor",
                AgentAttributes.AGENT_REASONING: task,
            },
        ) as span:
            try:
                # Initialize counters
                step_count = 0
                planning_steps = 0
                tools_used = set()
                start_time = time.time()

                # Process stream
                stream = wrapped(*args, **kwargs)
                for step in stream:
                    step_count += 1

                    # Track step types
                    if hasattr(step, "type"):
                        if step.type == "planning":
                            planning_steps += 1
                        elif step.type == "tool_call":
                            tools_used.add(step.tool_name)
                            # Add tool-specific attributes
                            span.set_attribute(ToolAttributes.TOOL_NAME, step.tool_name)
                            if hasattr(step, "arguments"):
                                span.set_attribute(ToolAttributes.TOOL_PARAMETERS, step.arguments)

                    # Update span attributes
                    span.set_attribute("agent.step_count", step_count)
                    span.set_attribute("agent.planning_steps", planning_steps)
                    span.set_attribute(AgentAttributes.AGENT_TOOLS, list(tools_used))

                    yield step

                # Set final attributes
                span.set_attribute("agent.execution_time", time.time() - start_time)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper
