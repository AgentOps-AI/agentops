import datetime
import uuid
from decimal import Decimal

import jwt
from tokencost import TOKEN_COSTS, count_message_tokens, count_string_tokens
from typing_extensions import deprecated

from agentops.api.db.supabase_client import AsyncSupabaseClient, get_async_supabase
from agentops.api.environment import JWT_SECRET_KEY
from agentops.api.exceptions import ExpiredJWTError, InvalidAPIKeyError
from agentops.api.log_config import logger


@deprecated("use agentops.api.auth.generate_jwt")
def generate_jwt(session_id, jwt_secret):
    payload = {
        "session_id": session_id,
        "exp": (
            datetime.datetime.now() + datetime.timedelta(hours=24)  # Token expires in 24 hour
        ).timestamp(),
    }
    token = jwt.encode(payload, jwt_secret or JWT_SECRET_KEY, algorithm="HS256")
    return token


@deprecated("use agentops.api.auth.generate_jwt")
def verify_jwt(token, secret_key):
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload["session_id"]
    except jwt.ExpiredSignatureError:
        raise ExpiredJWTError(401, "Expired Token")
    except jwt.DecodeError:
        RuntimeError("Invalid token")


def validate_uuid(uuid_string) -> uuid.UUID:
    try:
        return uuid.UUID(uuid_string, version=4)
    except ValueError:
        raise InvalidAPIKeyError(401, "Invalid API KEY format")
    except TypeError:
        raise InvalidAPIKeyError(401, "Invalid API KEY format")
    except Exception as e:
        raise RuntimeError(f"Error validating UUID: {e}")


async def get_premium_status(supabase: AsyncSupabaseClient = None, user_id: str = None) -> bool:
    if supabase is None and user_id is not None:
        supabase = await get_async_supabase()

    try:
        # return await supabase.get("users", "premium", "id", user_id)
        # TODO: when we refactor premium management, add logic here
        return False
    except Exception as e:
        logger.warning(f"Could not fetch premium status: {e}")
        return False


async def update_stats(
    supabase: AsyncSupabaseClient,
    session_id,
    cost: Decimal | None,
    events,
    prompt_tokens,
    completion_tokens,
    errors,
):
    _current_stats = (
        await supabase.table("stats").select("*").eq("session_id", session_id).limit(1).single().execute()
    )
    if _current_stats.data:
        current_stats = _current_stats.data
    else:
        logger.error(f"Could not find stats for session {session_id}")
        return

    current_cost = (
        Decimal(str(current_stats["cost"])) if current_stats and current_stats["cost"] else Decimal(0)
    )
    updated_cost = current_cost + (cost if cost else Decimal(0))
    updated_cost = str(updated_cost) if updated_cost != Decimal(0) else None

    stats = {
        "session_id": session_id,
        "cost": updated_cost,
        "events": events + (current_stats["events"] if current_stats else 0),
        "prompt_tokens": prompt_tokens + (current_stats["prompt_tokens"] if current_stats else 0),
        "completion_tokens": completion_tokens + (current_stats["completion_tokens"] if current_stats else 0),
        "errors": errors + (current_stats["errors"] if current_stats else 0),
    }

    await supabase.table("stats").upsert(stats, on_conflict="session_id").execute()


def calculate_costs(model, prompt, completion):
    try:
        if model not in TOKEN_COSTS:
            raise RuntimeError(f"Model {model} not in TOKEN_COSTS")

        # Prompt cost
        if type(prompt) == str:
            prompt_tokens = count_string_tokens(prompt, model)
        else:
            prompt_tokens = count_message_tokens(prompt, model)

        # Completion cost
        completion_tokens = count_string_tokens(completion, model)

        # Calculate cost
        return str(
            prompt_tokens * Decimal(str(TOKEN_COSTS[model]["input_cost_per_token"]))
            + completion_tokens * Decimal(str(TOKEN_COSTS[model]["output_cost_per_token"]))
        )

    except RuntimeError as e:
        logger.error(f"An error occurred while calculating cost: {e}. ")
        return 0


def strip_host_env(d: dict):
    if d is None:
        return None

    if isinstance(d, dict):
        for k in list(d.keys()):  # convert dict_keys into list for in-place deletion
            if k == "host_env":
                del d[k]
            elif isinstance(d[k], dict):
                strip_host_env(d[k])
            elif isinstance(d[k], list):
                for i in d[k]:
                    strip_host_env(i)
    return d
