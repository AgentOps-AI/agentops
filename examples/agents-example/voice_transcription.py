from dotenv import load_dotenv
load_dotenv()

import asyncio
import random
import numpy as np
from pathlib import Path

from agents import (
    Agent,
    function_tool,
    set_tracing_disabled,
)
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    VoicePipeline,
)
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

import agentops
agentops.init(tags=["openai-agents", "example", "voice"])

BASE_PATH = Path(__file__).parent


@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."


agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to someone from San Francisco, CA, so be polite and concise. ",
    ),
    model="gpt-4o-mini",
    tools=[get_weather],
)


async def main():
    pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))
    
    buffer = np.fromfile(BASE_PATH / "voice-input.wav", dtype=np.int16)
    audio_input = AudioInput(buffer=buffer)

    result = await pipeline.run(audio_input)

    response_chunks = []
    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            response_chunks.append(event.data)


if __name__ == "__main__":
    asyncio.run(main())