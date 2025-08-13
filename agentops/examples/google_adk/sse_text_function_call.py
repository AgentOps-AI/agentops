import os
import asyncio

import agentops
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types


# Initialize AgentOps (this is required to reproduce the original reported error)
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"), trace_name="adk_sse_text_function_call")

APP_NAME = "adk_sse_text_function_call_app"
USER_ID = "user_sse_text"
SESSION_ID = "session_sse_text"
MODEL_NAME = os.getenv("GOOGLE_ADK_MODEL", "gemini-1.5-flash")


# Simple weather tool to force a function_call from the model
async def get_weather(city: str) -> str:
	return f"The weather in {city} is sunny and 25C."


weather_tool = FunctionTool(func=get_weather)


# Agent that will likely trigger a function call
agent = LlmAgent(
	model=MODEL_NAME,
	name="WeatherAgent",
	description="Provides weather info using a tool.",
	instruction="""
	You are a helpful agent. When the user asks about weather for a city, you MUST call the get_weather tool
	with the exact city provided by the user. Do not answer directly without calling the tool.
	""",
	tools=[weather_tool],
	output_key="final_text",
)


# Create session service and runner
session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)


async def main():
	# Ensure session exists
	await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

	# User message that should trigger a function call
	user_message = types.Content(role="user", parts=[types.Part(text="What's the weather in Paris today?")])

	# Use RunConfig with SSE and TEXT modalities exactly as reported
	# Import path for RunConfig can vary across ADK versions; fall back to dict if import fails
	try:
		from google.adk.runtime import RunConfig  # type: ignore
	except Exception:
		RunConfig = None  # type: ignore

	run_config = RunConfig(streaming_mode="sse", response_modalities=["TEXT"]) if RunConfig else {  # type: ignore
		"streaming_mode": "sse",
		"response_modalities": ["TEXT"],
	}

	# Stream events
	async for event in runner.run_async(
		user_id=USER_ID,
		session_id=SESSION_ID,
		new_message=user_message,
		run_config=run_config,  # type: ignore
	):
		# Handle text and non-text parts defensively
		if getattr(event, "content", None) and getattr(event.content, "parts", None):
			for part in event.content.parts:
				text = getattr(part, "text", None)
				if text:
					print(f"Assistant: {text}")
				elif hasattr(part, "function_call") and part.function_call:
					print(f"Function Call: {getattr(part.function_call, 'name', '')} args={getattr(part.function_call, 'args', {})}")
				elif hasattr(part, "function_response") and part.function_response:
					print(f"Function Response: {getattr(part.function_response, 'response', None)}")


if __name__ == "__main__":
	asyncio.run(main())