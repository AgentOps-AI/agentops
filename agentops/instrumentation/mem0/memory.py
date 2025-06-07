"""Memory operation attribute extractors and wrappers for Mem0 instrumentation."""

from typing import Optional, Tuple, Dict, Any

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, LLMRequestTypeValues, MessageAttributes
from .common import (
    get_common_attributes,
    _extract_common_kwargs_attributes,
    _extract_memory_response_attributes,
    create_universal_mem0_wrapper,
)


def get_add_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's add method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    print(f"args: {args}")
    print(f"kwargs: {kwargs}")
    print(f"return_value: {return_value}")
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "add"
    attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.CHAT.value

    # Extract message content from args
    if args and len(args) > 0:
        messages = args[0]
        # Get user_id from kwargs for speaker, default to "user" if not found
        speaker = kwargs.get("user_id", "user") if kwargs else "user"

        if isinstance(messages, str):
            attributes["mem0.message"] = messages
            # Set as prompt for consistency with LLM patterns
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = messages
            attributes[MessageAttributes.PROMPT_SPEAKER.format(i=0)] = speaker
        elif isinstance(messages, list):
            attributes["mem0.message_count"] = len(messages)
            # Extract message types if available
            message_types = set()
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    if "role" in msg:
                        message_types.add(msg["role"])
                        attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = msg["role"]
                    if "content" in msg:
                        attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = msg["content"]
                    # Set speaker for each message
                    attributes[MessageAttributes.PROMPT_SPEAKER.format(i=i)] = speaker
                else:
                    # String message
                    attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = str(msg)

                    attributes[MessageAttributes.PROMPT_SPEAKER.format(i=i)] = speaker
            if message_types:
                attributes["mem0.message_types"] = ",".join(message_types)

    # Extract kwargs attributes
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

        # Extract memory type
        if "memory_type" in kwargs:
            attributes["mem0.memory_type"] = str(kwargs["memory_type"])

        # Extract inference flag
        if "infer" in kwargs:
            attributes[SpanAttributes.MEM0_INFER] = str(kwargs["infer"])

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_search_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's search method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    print(f"get_search_attributes args: {args}")
    print(f"get_search_attributes kwargs: {kwargs}")
    print(f"get_search_attributes return_value: {return_value}")
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "search"
    attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.CHAT.value

    # Extract search query from args
    if args and len(args) > 0:
        query = args[0]
        # Get user_id from kwargs for speaker, default to "user" if not found
        speaker = kwargs.get("user_id", "user") if kwargs else "user"

        if isinstance(query, str):
            attributes["mem0.message"] = query
            # Set as prompt for consistency
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = query
            attributes[MessageAttributes.PROMPT_SPEAKER.format(i=0)] = speaker

    # Extract kwargs attributes
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

        # Extract memory type
        if "memory_type" in kwargs:
            attributes["mem0.memory_type"] = str(kwargs["memory_type"])

        # Extract limit parameter
        if "limit" in kwargs:
            attributes["mem0.search.limit"] = str(kwargs["limit"])

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_get_all_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's get_all method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "get_all"

    # Extract kwargs attributes
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

        # Extract memory type
        if "memory_type" in kwargs:
            attributes["mem0.memory_type"] = str(kwargs["memory_type"])

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_get_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's get method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "get"

    # Extract memory ID from args
    if args and len(args) > 0:
        memory_id = args[0]
        if memory_id:
            attributes["mem0.memory_id"] = str(memory_id)

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_delete_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's delete method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "delete"

    # Extract memory ID from args if available
    if args and len(args) > 0:
        memory_id = args[0]
        if memory_id:
            attributes["mem0.memory_id"] = str(memory_id)

    # Extract kwargs attributes if available
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

        # Extract memory type
        if "memory_type" in kwargs:
            attributes["mem0.memory_type"] = str(kwargs["memory_type"])

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_update_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's update method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "update"

    # Extract memory ID from args (if available)
    if args and len(args) > 0:
        memory_id = args[0]
        if memory_id:
            attributes["mem0.memory_id"] = str(memory_id)

    # Extract data from args (if available)
    if args and len(args) > 1:
        data = args[1]
        if isinstance(data, str):
            attributes["mem0.message"] = data
            # Set as prompt for consistency
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = data
        elif isinstance(data, dict):
            # Handle case where data is a dictionary with "memory" key
            if "memory" in data:
                memory_text = data["memory"]
                attributes["mem0.message"] = memory_text
                # Set as prompt for consistency
                attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = memory_text

            # Extract metadata from data dict if present
            if "metadata" in data and isinstance(data["metadata"], dict):
                for key, value in data["metadata"].items():
                    attributes[f"mem0.metadata.{key}"] = str(value)

    # Extract kwargs attributes (if available)
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

        # Extract memory type
        if "memory_type" in kwargs:
            attributes["mem0.memory_type"] = str(kwargs["memory_type"])

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_delete_all_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's delete_all method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "delete_all"

    # Extract kwargs attributes if available
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

        # Extract memory type
        if "memory_type" in kwargs:
            attributes["mem0.memory_type"] = str(kwargs["memory_type"])

        # Extract user_id for tracking which user's memories are being deleted
        if "user_id" in kwargs:
            attributes["mem0.delete_all.user_id"] = str(kwargs["user_id"])

        # Extract agent_id for tracking which agent's memories are being deleted
        if "agent_id" in kwargs:
            attributes["mem0.delete_all.agent_id"] = str(kwargs["agent_id"])

        # Extract run_id for tracking which run's memories are being deleted
        if "run_id" in kwargs:
            attributes["mem0.delete_all.run_id"] = str(kwargs["run_id"])

    # Extract response attributes
    if return_value:
        attributes.update(_extract_memory_response_attributes(return_value))

    return attributes


def get_history_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, return_value: Optional[Any] = None
) -> AttributeMap:
    """Extract attributes for Mem0's history method.

    Args:
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        return_value: Return value from the method

    Returns:
        Dictionary of extracted attributes
    """
    attributes = get_common_attributes()
    attributes[SpanAttributes.OPERATION_NAME] = "history"

    # Extract memory ID from args
    if args and len(args) > 0:
        memory_id = args[0]
        if memory_id:
            attributes["mem0.memory_id"] = str(memory_id)

    # Extract kwargs attributes if available
    if kwargs:
        attributes.update(_extract_common_kwargs_attributes(kwargs))

    # Extract history data from return value
    if return_value and isinstance(return_value, list):
        attributes["mem0.history.count"] = len(return_value)

        # Extract event types and other details from history entries
        event_types = set()
        actor_ids = set()
        roles = set()

        for i, entry in enumerate(return_value):
            if isinstance(entry, dict):
                # Extract event type
                if "event" in entry:
                    event_types.add(entry["event"])
                    attributes[f"mem0.history.{i}.event"] = entry["event"]

                # Extract memory content changes
                if "old_memory" in entry:
                    if entry["old_memory"]:
                        attributes[f"mem0.history.{i}.old_memory"] = entry["old_memory"]

                if "new_memory" in entry:
                    if entry["new_memory"]:
                        attributes[f"mem0.history.{i}.new_memory"] = entry["new_memory"]

                # Extract timestamps
                if "created_at" in entry:
                    attributes[f"mem0.history.{i}.created_at"] = entry["created_at"]

                if "updated_at" in entry and entry["updated_at"]:
                    attributes[f"mem0.history.{i}.updated_at"] = entry["updated_at"]

                # Extract actor information
                if "actor_id" in entry and entry["actor_id"]:
                    actor_ids.add(entry["actor_id"])
                    attributes[f"mem0.history.{i}.actor_id"] = entry["actor_id"]

                if "role" in entry and entry["role"]:
                    roles.add(entry["role"])
                    attributes[f"mem0.history.{i}.role"] = entry["role"]

                # Extract deletion status
                if "is_deleted" in entry:
                    attributes[f"mem0.history.{i}.is_deleted"] = str(entry["is_deleted"])

                # Extract history entry ID
                if "id" in entry:
                    attributes[f"mem0.history.{i}.id"] = entry["id"]

        # Set aggregated attributes
        if event_types:
            attributes["mem0.history.event_types"] = ",".join(event_types)

        if actor_ids:
            attributes["mem0.history.actor_ids"] = ",".join(actor_ids)

        if roles:
            attributes["mem0.history.roles"] = ",".join(roles)

    return attributes


# Create universal Mem0 wrappers that work for both sync and async operations
mem0_add_wrapper = create_universal_mem0_wrapper("add", get_add_attributes)
mem0_search_wrapper = create_universal_mem0_wrapper("search", get_search_attributes)
mem0_get_all_wrapper = create_universal_mem0_wrapper("get_all", get_get_all_attributes)
mem0_get_wrapper = create_universal_mem0_wrapper("get", get_get_attributes)
mem0_delete_wrapper = create_universal_mem0_wrapper("delete", get_delete_attributes)
mem0_update_wrapper = create_universal_mem0_wrapper("update", get_update_attributes)
mem0_delete_all_wrapper = create_universal_mem0_wrapper("delete_all", get_delete_all_attributes)
mem0_history_wrapper = create_universal_mem0_wrapper("history", get_history_attributes)
