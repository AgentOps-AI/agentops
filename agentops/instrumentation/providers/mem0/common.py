"""Common utilities and base wrapper functions for Mem0 instrumentation."""

from typing import Dict, Any
from opentelemetry import context as context_api
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, LLMRequestTypeValues


def get_common_attributes() -> AttributeMap:
    """Get common instrumentation attributes for Mem0 operations.

    Returns:
        Dictionary of common Mem0 attributes
    """
    attributes = {}
    attributes[SpanAttributes.LLM_SYSTEM] = "Mem0"
    return attributes


def _extract_common_kwargs_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract common attributes from kwargs that apply to multiple operations.

    Args:
        kwargs: Keyword arguments from the method call

    Returns:
        Dictionary of extracted common attributes
    """
    attributes = {}

    # Extract user/agent/run IDs
    for id_type in ["user_id", "agent_id", "run_id"]:
        if id_type in kwargs and kwargs[id_type]:
            # Use the new mem0-specific attributes
            if id_type == "user_id":
                attributes["mem0.user_id"] = str(kwargs[id_type])
            elif id_type == "agent_id":
                attributes["mem0.agent_id"] = str(kwargs[id_type])
            elif id_type == "run_id":
                attributes["mem0.run_id"] = str(kwargs[id_type])

    # Extract metadata
    if "metadata" in kwargs:
        metadata = kwargs["metadata"]
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                attributes[f"mem0.metadata.{key}"] = str(value)

    return attributes


def _extract_memory_response_attributes(return_value: Any) -> AttributeMap:
    """Extract attributes from memory operation response.

    Args:
        return_value: The response from the memory operation

    Returns:
        Dictionary of extracted response attributes
    """
    attributes = {}

    if return_value:
        if isinstance(return_value, dict):
            # Check if this is an update/delete response (simple message format)
            if "message" in return_value and len(return_value) == 1:
                # Handle update/delete operation response
                attributes["mem0.operation.message"] = return_value["message"]
                return attributes

            # Check if this is a single memory object (like from get method)
            if "id" in return_value and "memory" in return_value and "results" not in return_value:
                # Handle single memory object
                attributes["mem0.memory_id"] = return_value["id"]
                attributes["mem0.memory.0.id"] = return_value["id"]
                attributes["mem0.memory.0.content"] = return_value["memory"]
                attributes["mem0.results_count"] = 1

                # Extract hash
                if "hash" in return_value:
                    attributes["mem0.memory.0.hash"] = return_value["hash"]

                # Extract score (might be None for get operations)
                if "score" in return_value and return_value["score"] is not None:
                    attributes["mem0.memory.0.score"] = str(return_value["score"])

                # Extract metadata
                if "metadata" in return_value and isinstance(return_value["metadata"], dict):
                    for key, value in return_value["metadata"].items():
                        attributes[f"mem0.memory.0.metadata.{key}"] = str(value)

                # Extract timestamps
                if "created_at" in return_value:
                    attributes["mem0.memory.0.created_at"] = return_value["created_at"]

                if "updated_at" in return_value and return_value["updated_at"]:
                    attributes["mem0.memory.0.updated_at"] = return_value["updated_at"]

                # Extract user_id
                if "user_id" in return_value:
                    attributes["mem0.memory.0.user_id"] = return_value["user_id"]
                    attributes["mem0.user_ids"] = return_value["user_id"]

                return attributes

            # Extract status if present
            if "status" in return_value:
                attributes["mem0.status"] = str(return_value["status"])

            # Extract results array - this is the main structure from mem0 (add/search operations)
            if "results" in return_value and isinstance(return_value["results"], list):
                results = return_value["results"]
                attributes["mem0.results_count"] = len(results)

                # Extract event types
                event_types = set()
                memory_ids = []
                memory_contents = []
                scores = []
                user_ids = set()

                for i, result in enumerate(results):
                    if isinstance(result, dict):
                        # Extract event type
                        if "event" in result:
                            event_types.add(result["event"])

                        # Extract memory ID
                        if "id" in result:
                            memory_ids.append(result["id"])
                            # Set individual memory ID attributes
                            attributes[f"mem0.memory.{i}.id"] = result["id"]

                        # Extract memory content
                        if "memory" in result:
                            memory_contents.append(result["memory"])
                            # Set individual memory content attributes
                            attributes[f"mem0.memory.{i}.content"] = result["memory"]

                        # Extract event for individual result
                        if "event" in result:
                            attributes[f"mem0.memory.{i}.event"] = result["event"]

                        # Extract hash
                        if "hash" in result:
                            attributes[f"mem0.memory.{i}.hash"] = result["hash"]

                        # Extract score (for search results)
                        if "score" in result:
                            scores.append(result["score"])
                            attributes[f"mem0.memory.{i}.score"] = str(result["score"])

                        # Extract metadata
                        if "metadata" in result and isinstance(result["metadata"], dict):
                            for key, value in result["metadata"].items():
                                attributes[f"mem0.memory.{i}.metadata.{key}"] = str(value)

                        # Extract timestamps
                        if "created_at" in result:
                            attributes[f"mem0.memory.{i}.created_at"] = result["created_at"]

                        if "updated_at" in result and result["updated_at"]:
                            attributes[f"mem0.memory.{i}.updated_at"] = result["updated_at"]

                        # Extract user_id
                        if "user_id" in result:
                            user_ids.add(result["user_id"])
                            attributes[f"mem0.memory.{i}.user_id"] = result["user_id"]

                # Set aggregated attributes
                if event_types:
                    attributes["mem0.event_types"] = ",".join(event_types)

                if memory_ids:
                    # Set primary memory ID (first one) as the main memory ID
                    attributes["mem0.memory_id"] = memory_ids[0]
                    # Set all memory IDs as a comma-separated list
                    attributes["mem0.memory.ids"] = ",".join(memory_ids)

                if memory_contents:
                    # Set all memory contents as a combined attribute
                    attributes["mem0.memory.contents"] = " | ".join(memory_contents)

                if scores:
                    # Set average and max scores for search results
                    attributes["mem0.search.avg_score"] = str(sum(scores) / len(scores))
                    attributes["mem0.search.max_score"] = str(max(scores))
                    attributes["mem0.search.min_score"] = str(min(scores))

                if user_ids:
                    # Set user IDs (typically should be the same user for all results)
                    attributes["mem0.user_ids"] = ",".join(user_ids)

            # Extract relations count if present (for backward compatibility)
            if "relations" in return_value:
                attributes["mem0.relations_count"] = len(return_value["relations"])

        elif isinstance(return_value, list):
            # For operations that return lists directly (like search, get_all)
            attributes["mem0.results_count"] = len(return_value)

            # If it's a list of memory objects, extract similar attributes
            for i, item in enumerate(return_value):
                if isinstance(item, dict):
                    if "id" in item:
                        attributes[f"mem0.memory.{i}.id"] = item["id"]
                    if "memory" in item:
                        attributes[f"mem0.memory.{i}.content"] = item["memory"]
                    if "event" in item:
                        attributes[f"mem0.memory.{i}.event"] = item["event"]
                    if "hash" in item:
                        attributes[f"mem0.memory.{i}.hash"] = item["hash"]
                    if "score" in item:
                        attributes[f"mem0.memory.{i}.score"] = str(item["score"])
                    if "user_id" in item:
                        attributes[f"mem0.memory.{i}.user_id"] = item["user_id"]

    return attributes


def create_mem0_wrapper(operation_name: str, attribute_extractor):
    """Create a wrapper function for Mem0 operations that ensures proper span hierarchy.

    This function creates wrappers that explicitly use the current context to ensure
    mem0 spans are properly nested within the current AgentOps session or OpenAI spans.

    Args:
        operation_name: Name of the mem0 operation (add, search, etc.)
        attribute_extractor: Function to extract attributes for this operation

    Returns:
        A wrapper function that creates properly nested spans
    """

    def wrapper(tracer):
        def actual_wrapper(wrapped, instance, args, kwargs):
            # Skip instrumentation if suppressed
            from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY

            if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
                return wrapped(*args, **kwargs)

            # Get current context to ensure proper parent-child relationship
            current_context = context_api.get_current()
            span = tracer.start_span(
                f"mem0.memory.{operation_name}",
                context=current_context,
                kind=SpanKind.CLIENT,
                attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
            )

            return_value = None
            try:
                # Add the input attributes to the span before execution
                attributes = attribute_extractor(args=args, kwargs=kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                return_value = wrapped(*args, **kwargs)
                # Add the output attributes to the span after execution
                attributes = attribute_extractor(return_value=return_value)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                # Add everything we have in the case of an error
                attributes = attribute_extractor(args=args, kwargs=kwargs, return_value=return_value)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                span.end()

            return return_value

        return actual_wrapper

    return wrapper


def create_async_mem0_wrapper(operation_name: str, attribute_extractor):
    """Create an async wrapper function for Mem0 operations that ensures proper span hierarchy.

    This function creates async wrappers that explicitly use the current context to ensure
    mem0 spans are properly nested within the current AgentOps session or OpenAI spans.

    Args:
        operation_name: Name of the mem0 operation (add, search, etc.)
        attribute_extractor: Function to extract attributes for this operation

    Returns:
        An async wrapper function that creates properly nested spans
    """

    def wrapper(tracer):
        def actual_wrapper(wrapped, instance, args, kwargs):
            # Skip instrumentation if suppressed
            from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY

            if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
                return wrapped(*args, **kwargs)

            async def async_wrapper():
                # Get current context to ensure proper parent-child relationship
                current_context = context_api.get_current()
                span = tracer.start_span(
                    f"mem0.AsyncMemory.{operation_name}",
                    context=current_context,
                    kind=SpanKind.CLIENT,
                    attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
                )

                return_value = None
                try:
                    # Add the input attributes to the span before execution
                    attributes = attribute_extractor(args=args, kwargs=kwargs)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    return_value = await wrapped(*args, **kwargs)

                    # Add the output attributes to the span after execution
                    attributes = attribute_extractor(return_value=return_value)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    span.set_status(Status(StatusCode.OK))
                except Exception as e:
                    # Add everything we have in the case of an error
                    attributes = attribute_extractor(args=args, kwargs=kwargs, return_value=return_value)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    span.end()

                return return_value

            return async_wrapper()

        return actual_wrapper

    return wrapper


def create_universal_mem0_wrapper(operation_name: str, attribute_extractor):
    """Create a universal wrapper that handles both sync and async methods.

    This function detects whether the wrapped method is async and applies the appropriate wrapper.
    """

    def wrapper(tracer):
        def actual_wrapper(wrapped, instance, args, kwargs):
            import asyncio

            # Check if the wrapped function is async
            if asyncio.iscoroutinefunction(wrapped):
                # Use async wrapper
                async_wrapper_func = create_async_mem0_wrapper(operation_name, attribute_extractor)
                return async_wrapper_func(tracer)(wrapped, instance, args, kwargs)
            else:
                # Use sync wrapper
                sync_wrapper_func = create_mem0_wrapper(operation_name, attribute_extractor)
                return sync_wrapper_func(tracer)(wrapped, instance, args, kwargs)

        return actual_wrapper

    return wrapper
