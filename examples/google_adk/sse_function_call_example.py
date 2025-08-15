import os
import asyncio
from typing import Optional

import agentops
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# Attempt to import RunConfig/StreamingMode from likely ADK locations
RunConfig: Optional[object] = None
StreamingMode: Optional[object] = None
try:
    from google.adk.runners import RunConfig as _RunConfig, StreamingMode as _StreamingMode  # type: ignore

    RunConfig = _RunConfig
    StreamingMode = _StreamingMode
except Exception:
    try:
        from google.adk.types import RunConfig as _RunConfig2, StreamingMode as _StreamingMode2  # type: ignore

        RunConfig = _RunConfig2
        StreamingMode = _StreamingMode2
    except Exception:
        RunConfig = None
        StreamingMode = None


# Initialize AgentOps (set AGENTOPS_API_KEY in your environment)
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"), trace_name="adk_sse_text_function_call")

APP_NAME = "adk_sse_text_function_call_app"
USER_ID = "user_sse_text_fc"
SESSION_ID = "session_sse_text_fc"
MODEL_NAME = "gemini-2.0-flash"


# Simple tool to trigger a function call
async def get_weather(location: str) -> str:
    return f"Weather for {location}: sunny and 25°C."


weather_tool = FunctionTool(func=get_weather)

# Agent configured with the tool so the model can trigger a function call
agent = LlmAgent(
    model=MODEL_NAME,
    name="WeatherAgent",
    description="Provides weather using a tool",
    instruction=(
        "You are a helpful assistant. When asked about weather, call the get_weather tool with the given location."
    ),
    tools=[weather_tool],
    output_key="weather_output",
)

# Session service and runner
session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


async def main():
    # Ensure session exists
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

    # Create user message
    user_message = types.Content(role="user", parts=[types.Part(text="What's the weather in Paris?")])

    # Configure SSE streaming with TEXT modality, as reported by the user
    run_config_kw = {}
    if RunConfig is not None and StreamingMode is not None:
        run_config_kw["run_config"] = RunConfig(streaming_mode=StreamingMode.SSE, response_modalities=["TEXT"])  # type: ignore

    final_text = None
    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=user_message, **run_config_kw
    ):
        # Print out any parts safely; this will include function_call parts when they occur
        if hasattr(event, "content") and event.content and getattr(event.content, "parts", None):
            for part in event.content.parts:
                text = getattr(part, "text", None)
                func_call = getattr(part, "function_call", None)
                if text:
                    print(f"Assistant: {text}")
                    final_text = text
                elif func_call is not None:
                    name = getattr(func_call, "name", "<unknown>")
                    args = getattr(func_call, "args", {})
                    print(f"Function call: {name} args={args}")

    print("Final text:", final_text)


if __name__ == "__main__":
    asyncio.run(main())
