"""Stream wrappers for IBM watsonx.ai.

This module provides stream wrapper classes and functions for IBM watsonx.ai's streaming
responses, implementing telemetry tracking for streaming content.
"""

import json
from opentelemetry.trace import get_tracer, SpanKind
from agentops.logging import logger
from agentops.instrumentation.ibm_watsonx_ai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.ibm_watsonx_ai.attributes.common import (
    extract_params_attributes,
    convert_params_to_dict,
    extract_prompt_from_args,
    extract_messages_from_args,
    extract_params_from_args,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues, CoreAttributes, MessageAttributes


class TracedStream:
    """A wrapper for IBM watsonx.ai's streaming response that adds telemetry."""

    def __init__(self, original_stream, span):
        """Initialize with the original stream and span."""
        self.original_stream = original_stream
        self.span = span
        self.completion_content = ""
        self.input_tokens = 0
        self.output_tokens = 0
        self.model_id = None

    def __iter__(self):
        """Iterate through chunks, tracking content and attempting to extract token data."""
        try:
            for yielded_chunk in self.original_stream:
                # Initialize data for this chunk
                generated_text_chunk = ""
                model_id_chunk = None

                try:
                    # Attempt to access internal frame local variable 'chunk' for full data
                    internal_chunk_data_str = getattr(self.original_stream, "gi_frame", {}).f_locals.get("chunk")

                    if isinstance(internal_chunk_data_str, str) and internal_chunk_data_str.startswith("data: "):
                        try:
                            # Remove 'data: ' prefix and parse JSON
                            json_payload_str = internal_chunk_data_str[len("data: ") :]
                            json_payload = json.loads(json_payload_str)

                            # Determine if it's generate_text_stream or chat_stream structure
                            if "results" in json_payload:  # Likely generate_text_stream
                                model_id_chunk = json_payload.get("model_id")
                                if isinstance(json_payload["results"], list):
                                    for result in json_payload["results"]:
                                        if isinstance(result, dict):
                                            # Use yielded_chunk for generated_text as internal one might be partial
                                            if isinstance(yielded_chunk, str):
                                                generated_text_chunk = yielded_chunk
                                            # Use the first non-zero input token count found
                                            if self.input_tokens == 0 and result.get("input_token_count", 0) > 0:
                                                self.input_tokens = result.get("input_token_count", 0)
                                            # Accumulate output tokens
                                            self.output_tokens += result.get("generated_token_count", 0)

                            elif "choices" in json_payload:  # Likely chat_stream
                                # model_id might be at top level or within choices in other APIs, check top first
                                model_id_chunk = json_payload.get("model_id") or json_payload.get("model")
                                if isinstance(json_payload["choices"], list) and json_payload["choices"]:
                                    choice = json_payload["choices"][0]
                                    if isinstance(choice, dict):
                                        delta = choice.get("delta", {})
                                        if isinstance(delta, dict):
                                            generated_text_chunk = delta.get("content", "")

                                        # Check for finish reason to potentially get final usage
                                        finish_reason = choice.get("finish_reason")
                                        if finish_reason == "stop":
                                            try:
                                                final_response_data = getattr(
                                                    self.original_stream, "gi_frame", {}
                                                ).f_locals.get("parsed_response")
                                                if (
                                                    isinstance(final_response_data, dict)
                                                    and "usage" in final_response_data
                                                ):
                                                    usage = final_response_data["usage"]
                                                    if isinstance(usage, dict):
                                                        # Update token counts with final values
                                                        self.input_tokens = usage.get(
                                                            "prompt_tokens", self.input_tokens
                                                        )
                                                        self.output_tokens = usage.get(
                                                            "completion_tokens", self.output_tokens
                                                        )
                                                        # Update span immediately with final counts
                                                        if self.input_tokens is not None:
                                                            self.span.set_attribute(
                                                                SpanAttributes.LLM_USAGE_PROMPT_TOKENS,
                                                                self.input_tokens,
                                                            )
                                                        if self.output_tokens is not None:
                                                            self.span.set_attribute(
                                                                SpanAttributes.LLM_USAGE_COMPLETION_TOKENS,
                                                                self.output_tokens,
                                                            )
                                                        if (
                                                            self.input_tokens is not None
                                                            and self.output_tokens is not None
                                                        ):
                                                            self.span.set_attribute(
                                                                SpanAttributes.LLM_USAGE_TOTAL_TOKENS,
                                                                self.input_tokens + self.output_tokens,
                                                            )

                                            except AttributeError as final_attr_err:
                                                logger.debug(
                                                    f"Could not access internal generator state for final response: {final_attr_err}"
                                                )
                                            except Exception as final_err:
                                                logger.debug(
                                                    f"Error accessing or processing final response data: {final_err}"
                                                )

                        except json.JSONDecodeError as json_err:
                            logger.debug(f"Failed to parse JSON from internal chunk data: {json_err}")
                            # Fallback to using the yielded chunk directly
                            if isinstance(yielded_chunk, dict):  # chat_stream yields dicts
                                if "choices" in yielded_chunk and yielded_chunk["choices"]:
                                    delta = yielded_chunk["choices"][0].get("delta", {})
                                    generated_text_chunk = delta.get("content", "")
                            elif isinstance(yielded_chunk, str):  # generate_text_stream yields strings
                                generated_text_chunk = yielded_chunk
                        except Exception as parse_err:
                            logger.debug(f"Error processing internal chunk data: {parse_err}")
                            if isinstance(yielded_chunk, dict):  # Fallback for chat
                                if "choices" in yielded_chunk and yielded_chunk["choices"]:
                                    delta = yielded_chunk["choices"][0].get("delta", {})
                                    generated_text_chunk = delta.get("content", "")
                            elif isinstance(yielded_chunk, str):  # Fallback for generate
                                generated_text_chunk = yielded_chunk
                    else:
                        # If internal data not found or not in expected format, use yielded chunk
                        if isinstance(yielded_chunk, dict):  # chat_stream yields dicts
                            if "choices" in yielded_chunk and yielded_chunk["choices"]:
                                delta = yielded_chunk["choices"][0].get("delta", {})
                                generated_text_chunk = delta.get("content", "")
                        elif isinstance(yielded_chunk, str):  # generate_text_stream yields strings
                            generated_text_chunk = yielded_chunk

                except AttributeError as attr_err:
                    logger.debug(f"Could not access internal generator state (gi_frame.f_locals): {attr_err}")
                    if isinstance(yielded_chunk, dict):  # Fallback for chat
                        if "choices" in yielded_chunk and yielded_chunk["choices"]:
                            delta = yielded_chunk["choices"][0].get("delta", {})
                            generated_text_chunk = delta.get("content", "")
                    elif isinstance(yielded_chunk, str):  # Fallback for generate
                        generated_text_chunk = yielded_chunk
                except Exception as e:
                    logger.debug(f"Error accessing or processing internal generator state: {e}")
                    if isinstance(yielded_chunk, dict):  # Fallback for chat
                        if "choices" in yielded_chunk and yielded_chunk["choices"]:
                            delta = yielded_chunk["choices"][0].get("delta", {})
                            generated_text_chunk = delta.get("content", "")
                    elif isinstance(yielded_chunk, str):  # Fallback for generate
                        generated_text_chunk = yielded_chunk

                # Accumulate completion content regardless of where it came from
                self.completion_content += generated_text_chunk

                # Update span attributes within the loop if data is available
                if model_id_chunk and not self.model_id:
                    self.model_id = model_id_chunk
                    self.span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, self.model_id)

                if self.input_tokens is not None:
                    self.span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, self.input_tokens)
                if self.output_tokens is not None:
                    self.span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, self.output_tokens)
                if self.input_tokens is not None and self.output_tokens is not None:
                    self.span.set_attribute(
                        SpanAttributes.LLM_USAGE_TOTAL_TOKENS, self.input_tokens + self.output_tokens
                    )

                # Yield the original chunk that the user expects
                yield yielded_chunk
        finally:
            # Update final completion content attribute after stream finishes
            if self.completion_content:
                self.span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")
                self.span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
                self.span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), self.completion_content)

            # Final update for token counts
            if self.input_tokens is not None:
                self.span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, self.input_tokens)
            if self.output_tokens is not None:
                self.span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, self.output_tokens)
            if self.input_tokens is not None and self.output_tokens is not None:
                self.span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, self.input_tokens + self.output_tokens)

            # End the span when the stream is exhausted
            if self.span.is_recording():
                self.span.end()


def generate_text_stream_wrapper(wrapped, instance, args, kwargs):
    """Wrapper for the Model.generate_text_stream method."""
    tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION)
    span = tracer.start_span(
        "watsonx.generate_text_stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.COMPLETION.value},
    )

    # Extract prompt using helper function
    prompt = extract_prompt_from_args(args, kwargs)
    if prompt:
        span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=0), "user")
        span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=0), prompt)
        span.set_attribute(MessageAttributes.PROMPT_TYPE.format(i=0), "text")

    # Extract parameters using helper function
    params = extract_params_from_args(args, kwargs)
    if params:
        params_dict = convert_params_to_dict(params)
        if params_dict:
            try:
                span_attributes = extract_params_attributes(params_dict)
                for key, value in span_attributes.items():
                    span.set_attribute(key, value)
            except Exception as e:
                logger.debug(f"Error extracting attributes from params dict: {e}")

    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)

    try:
        stream = wrapped(*args, **kwargs)
        return TracedStream(stream, span)
    except Exception as e:
        span.record_exception(e)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
        span.end()
        raise


def chat_stream_wrapper(wrapped, instance, args, kwargs):
    """Wrapper for the Model.chat_stream method."""
    tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION)
    span = tracer.start_span(
        "watsonx.chat_stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    # Extract messages using helper function
    messages = extract_messages_from_args(args, kwargs)
    if messages and isinstance(messages, list):
        for i, message in enumerate(messages):
            if isinstance(message, dict):
                role = message.get("role")
                content = message.get("content")
                # Handle complex content (list of dicts) vs simple string
                if isinstance(content, list):
                    text_content = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content.append(item.get("text", ""))
                    content_str = " ".join(text_content)
                else:
                    content_str = str(content)

                if role:
                    span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=i), role)
                if content_str:
                    span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=i), content_str)
                    span.set_attribute(MessageAttributes.PROMPT_TYPE.format(i=i), "text")

    # Extract parameters using helper function
    params = extract_params_from_args(args, kwargs)
    if params:
        params_dict = convert_params_to_dict(params)
        if params_dict:
            try:
                span_attributes = extract_params_attributes(params_dict)
                for key, value in span_attributes.items():
                    span.set_attribute(key, value)
            except Exception as e:
                logger.debug(f"Error extracting attributes from params dict: {e}")

    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)

    try:
        stream = wrapped(*args, **kwargs)
        return TracedStream(stream, span)
    except Exception as e:
        span.record_exception(e)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
        span.end()
        raise
