import base64
import uuid
import datetime
import json
from decimal import Decimal
from tokencost import TOKEN_COSTS, count_string_tokens, count_message_tokens
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from agentops.api.promptarmor import get_promptarmor_flag
from agentops.api.log_config import logger
from agentops.api.exceptions import InvalidModelError
from agentops.api.db.supabase_client import AsyncSupabaseClient, get_async_supabase
from agentops.api.environment import SUPABASE_URL


async def handle_actions(event, session_id, supabase: AsyncSupabaseClient = None):
    if supabase is None:
        supabase = await get_async_supabase()

    async def process_screenshot(screenshot, session_id):
        if screenshot is None:
            return None

        if screenshot.startswith("http://") or screenshot.startswith("https://"):
            return screenshot

        # screenshot is a base64 string
        base64_img_bytes = screenshot.replace("data:image/png;base64,", "")
        base64_img_bytes += "=" * ((4 - len(base64_img_bytes) % 4) % 4)
        img_bytes = base64.b64decode(base64_img_bytes)
        timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        try:
            await supabase.storage.from_("screenshots").upload(f"{session_id}/{timestamp_utc}.png", img_bytes)
        except RuntimeError as e:
            logger.warning(f"Error posting screenshot: {e}")
            return None

        return f"{SUPABASE_URL}/storage/v1/object/screenshots/{session_id}/{timestamp_utc}.png"

    action = {
        "id": event.get("id", str(uuid.uuid4())),
        "session_id": session_id,
        "agent_id": event.get("agent_id", None),
        "action_type": event.get("action_type", None),
        "logs": event.get("logs", None),
        "screenshot": await process_screenshot(event.get("screenshot", None), session_id),
        "params": event.get("params", None),
        "returns": event.get("returns", None),
        "init_timestamp": event["init_timestamp"],
        "end_timestamp": event["end_timestamp"],
    }
    return action


async def handle_llms(event, premium, session_id, supabase: AsyncSupabaseClient = None):
    if supabase is None:
        supabase = await get_async_supabase()

    def count_prompt_tokens(prompt):
        try:
            if model not in TOKEN_COSTS:
                raise InvalidModelError(f'Invalid model "{model}" provided.')
            if type(prompt) is str:
                return count_string_tokens(prompt, model)
            else:
                return count_message_tokens(prompt, model)
        except Exception as e:
            logger.warning(e)
            return 0

    def count_completion_tokens(completion):
        try:
            if model not in TOKEN_COSTS:
                raise InvalidModelError(f'Invalid model "{model}" provided.')
            # User may send dict containing the completion content or just the completion content
            # completion = {role:"assistant", content:"some message", function_call: ..., tool_calls: ...}
            # completion = "some message"
            return count_string_tokens(completion.get("content", completion), model)
        except Exception as e:
            logger.warning(e)
            return 0

    chatml_schema_prompt = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "required": ["role"],
            "properties": {
                "role": {"type": "string"},
                "name": {"type": "string"},
                "content": {
                    "oneOf": [
                        {"type": ["string", "null"]},
                        {"type": "array"},
                        {"type": "object"},
                    ]
                },
                "tool_calls": {"type": ["array", "null"]},
                "tool_call_id": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
    }

    chatml_schema_completion = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["role"],
        "properties": {
            "role": {"type": "string"},
            "content": {"type": ["string", "null", "object", "array"]},
            "tool_calls": {"type": ["array", "null"]},
            "function_call": {"type": ["object", "null"]},
        },
        "additionalProperties": True,
    }

    def coerce_llm_message_to_chatml_schema(message, chatml_schema):
        try:
            validate(instance=message, schema=chatml_schema)

            wrapped_message = {"type": "chatml", "messages": message}
            return wrapped_message
        except ValidationError:
            # If validation fails, wrap the message as a "string" type
            wrapped_message = {
                "type": "string",
                "string": (json.dumps(message) if not isinstance(message, str) else message),
            }

        return wrapped_message

    model = event.get("model", None)
    prompt = event.get("prompt", None)
    completion = event.get("completion", None)
    prompt_tokens = event.get("prompt_tokens") or count_prompt_tokens(prompt)
    completion_tokens = event.get("completion_tokens") or count_completion_tokens(completion)

    if premium:
        promptarmor_flag = await get_promptarmor_flag(prompt, completion, session_id)
    else:
        promptarmor_flag = None

    cost = event.get("cost")
    if (cost is None) and (model in TOKEN_COSTS):
        cost_per_prompt_token = Decimal(str(TOKEN_COSTS[model]["input_cost_per_token"]))
        cost_per_completion_token = Decimal(str(TOKEN_COSTS[model]["output_cost_per_token"]))
        cost = str((prompt_tokens * cost_per_prompt_token) + (completion_tokens * cost_per_completion_token))

    llm = {
        "id": event.get("id", str(uuid.uuid4())),
        "session_id": session_id,
        "agent_id": event.get("agent_id", None),
        "thread_id": event.get("thread_id", None),
        "prompt": coerce_llm_message_to_chatml_schema(prompt, chatml_schema_prompt),
        "completion": coerce_llm_message_to_chatml_schema(completion, chatml_schema_completion),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost": cost,
        "promptarmor_flag": promptarmor_flag,
        "params": event.get("params", None),
        "returns": event.get("returns", None),
        "init_timestamp": event["init_timestamp"],
        "end_timestamp": event["end_timestamp"],
    }

    return llm


async def handle_tools(event, session_id, supabase: AsyncSupabaseClient = None):
    if supabase is None:
        supabase = await get_async_supabase()

    tool = {
        "id": event.get("id", str(uuid.uuid4())),
        "session_id": session_id,
        "agent_id": event.get("agent_id", None),
        "name": event.get("name", None),
        "logs": event.get("logs", None),
        "params": event.get("params", None),
        "returns": event.get("returns", None),
        "init_timestamp": event["init_timestamp"],
        "end_timestamp": event["end_timestamp"],
    }
    return tool


async def handle_errors(event, session_id, supabase: AsyncSupabaseClient = None):
    if supabase is None:
        supabase = await get_async_supabase()

    error = {
        "session_id": session_id,
        "trigger_event_id": event.get("trigger_event_id", None),
        "trigger_event_type": event.get("trigger_event_type", None),
        "error_type": event.get("error_type", None),
        "code": event.get("code", None),
        "details": event.get("details", None),
        "logs": event.get("logs", None),
        "timestamp": event.get("timestamp", None),
    }
    return error
