# # Anthropic Async Example
#
# Anthropic supports both sync and async! This is great because we can wait for functions to finish before we use them!
#
# In this example, we will make a program called "Titan Support Protocol." In this example, we will assign our mech a personality type and have a message generated based on our Titan's health (Which we randomly choose). We also send four generated UUIDs which are generated while the LLM runs
# First, we start by importing Agentops and Anthropic
# %pip install agentops
# %pip install anthropic
# Setup our generic default statements
from anthropic import Anthropic
import agentops
from dotenv import load_dotenv
import os
import random
import asyncio
import uuid

# And set our API keys.
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
#
# Now let's set the client as Anthropic and open an agentops trace!
client = Anthropic()
agentops.init(trace_name="Anthropic Async Example", tags=["anthropic-async", "agentops-example"])
# Now we create three personality presets;
#
# Legion is a relentless and heavy-hitting Titan that embodies brute strength and defensive firepower, Northstar is a precise and agile sniper that excels in long-range combat and flight, while Ronin is a swift and aggressive melee specialist who thrives on close-quarters hit-and-run tactics.
TitanPersonality = [
    "Legion is a relentless and heavy-hitting Titan that embodies brute strength and defensive firepower. He speaks bluntly.,",
    "Northstar is a precise and agile sniper that excels in long-range combat and flight. He speaks with an edge of coolness to him",
    "Ronin is a swift and aggressive melee specialist who thrives on close-quarters hit-and-run tactics. He talks like a Samurai might.",
]
# And our comabt log generator! We select from four health presets!
TitanHealth = [
    "Fully functional",
    "Slightly Damaged",
    "Moderate Damage",
    "Considerable Damage",
    "Near Destruction",
]
# Now to the real core of this; making our message stream! We create this as a function we can call later! I create examples since the LLM's context size can handle it!
Personality = {random.choice(TitanPersonality)}
Health = {random.choice(TitanHealth)}


async def req():
    # Start a streaming message request
    stream = client.messages.create(
        max_tokens=1024,
        model="claude-3-7-sonnet-20250219",
        messages=[
            {
                "role": "user",
                "content": "You are a Titan; a mech from Titanfall 2. Based on your titan's personality and status, generate a message for your pilot. If Near Destruction, make an all caps death message such as AVENGE ME or UNTIL NEXT TIME.",
            },
            {
                "role": "assistant",
                "content": "Personality: Legion is a relentless and heavy-hitting Titan that embodies brute strength and defensive firepower. He speaks bluntly. Status: Considerable Damage",
            },
            {
                "role": "assistant",
                "content": "Heavy damage detected. Reinforcements would be appreciated, but I can still fight.",
            },
            {
                "role": "user",
                "content": "You are a Titan; a mech from Titanfall 2. Based on your titan's personality and status, generate a message for your pilot. If Near Destruction, make an all caps death message such as AVENGE ME or UNTIL NEXT TIME.",
            },
            {
                "role": "assistant",
                "content": f"Personality: {Personality}. Status: {Health}",
            },
        ],
        stream=True,
    )

    response = ""
    for event in stream:
        if event.type == "content_block_delta":
            response += event.delta.text
        elif event.type == "message_stop":
            break  # Exit the loop when the message completes

    return response


async def generate_uuids():
    uuids = [str(uuid.uuid4()) for _ in range(4)]
    return uuids


# Now we wrap it all in a nice main function! Run this for the magic to happen! Go to your AgentOps dashboard and you should see this trace reflected!
async def main():
    # Start both tasks concurrently
    uuids, message = await asyncio.gather(generate_uuids(), req())

    print("Personality:", Personality)
    print("Health Status:", Health)
    print("Combat log incoming from encrypted area")

    print("Verification matrix activated.:")
    for u in uuids:
        print(u)

    print(". Titan Message: ", message)


# Run the main function
asyncio.run(main())
# We can observe the trace in the AgentOps dashboard by going to the trace URL provided above.


# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=None)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise
