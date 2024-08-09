from agentops.helpers import get_ISO_time
from agentops.time_travel import fetch_completion_override_from_time_travel_cache


def override_litellm_completion(tracker):
    import litellm
    from openai.types.chat import (
        ChatCompletion,
    )  # Note: litellm calls all LLM APIs using the OpenAI format

    original_create = litellm.completion

    def patched_function(*args, **kwargs):
        init_timestamp = get_ISO_time()

        session = kwargs.get("session", None)
        if "session" in kwargs.keys():
            del kwargs["session"]

        completion_override = fetch_completion_override_from_time_travel_cache(kwargs)
        if completion_override:
            result_model = ChatCompletion.model_validate_json(completion_override)
            return tracker.handle_response_v1_openai(
                tracker, result_model, kwargs, init_timestamp, session=session
            )

        # prompt_override = fetch_prompt_override_from_time_travel_cache(kwargs)
        # if prompt_override:
        #     kwargs["messages"] = prompt_override["messages"]

        # Call the original function with its original arguments
        result = original_create(*args, **kwargs)
        return tracker.handle_response_v1_openai(
            tracker, result, kwargs, init_timestamp, session=session
        )

    litellm.completion = patched_function


def override_litellm_async_completion(tracker):
    import litellm
    from openai.types.chat import (
        ChatCompletion,
    )  # Note: litellm calls all LLM APIs using the OpenAI format

    original_create_async = litellm.acompletion

    async def patched_function(*args, **kwargs):
        init_timestamp = get_ISO_time()

        session = kwargs.get("session", None)
        if "session" in kwargs.keys():
            del kwargs["session"]

        completion_override = fetch_completion_override_from_time_travel_cache(kwargs)
        if completion_override:
            result_model = ChatCompletion.model_validate_json(completion_override)
            return tracker.handle_response_v1_openai(
                tracker, result_model, kwargs, init_timestamp, session=session
            )

        # prompt_override = fetch_prompt_override_from_time_travel_cache(kwargs)
        # if prompt_override:
        #     kwargs["messages"] = prompt_override["messages"]

        # Call the original function with its original arguments
        result = await original_create_async(*args, **kwargs)
        return tracker.handle_response_v1_openai(
            tracker, result, kwargs, init_timestamp, session=session
        )

    # Override the original method with the patched one
    litellm.acompletion = patched_function
