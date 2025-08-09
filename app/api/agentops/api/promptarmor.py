import httpx
import os
import asyncio

from .log_config import logger

API_KEY = os.environ.get("PROMPTARMOR_API_KEY")


async def evaluate(prompt, session_id: str, mode: str, source=None, destination=None) -> bool:
    """
    Evaluate a prompt with the PromptArmor API.
    Args:
        prompt: the content that you are sending to an LLM
        session_id: the session id for set of calls to the LLM
        mode: the mode of the evaluation. Either "input" or "output"
        source(optional) : the source of this content that you are sending to the LLM
        destination (optional) : the destination of this output that will come from the LLM
    Returns (bool):
        The response from the API. {"containsInjection":true}
    """
    if mode not in ["input", "output"]:
        raise ValueError("mode must be either 'input' or 'output'")

    if mode == "input":
        url = "https://api.aidr.promptarmor.com/v1/analyze/input"
    else:
        url = "https://api.aidr.promptarmor.com/v1/analyze/output"

    promptarmor_headers = {
        "PromptArmor-Auth": f"Bearer {API_KEY}",
        # The session ID is unique to each user session(e.g. a workflow or conversation)
        "PromptArmor-Session-ID": session_id,
        "Content-Type": "application/json",
    }

    data = {"content": prompt, "source": source, "destination": destination}

    async with httpx.AsyncClient() as async_client:
        response = await async_client.post(url, headers=promptarmor_headers, json=data)

    return response.json().get("detection", None)


async def get_promptarmor_flag(prompt, completion, session_id) -> bool | None:
    "TODO: Implement other specific flags https://promptarmor.readme.io/reference/v1analyzeinput"
    try:
        input_check, output_check = await asyncio.gather(
            evaluate(prompt, session_id, mode="input"),
            evaluate(completion, session_id, mode="output"),
        )
        return input_check or output_check
    except Exception as e:
        logger.warning(f"Unable to get Promptarmor Flag: {e}")
        return None
