import os
import agentops
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

# Initialize AgentOps
agentops.init(tags=['anthropic-streaming'])

# Ensure you have ANTHROPIC_API_KEY in your .env file
client = anthropic.Anthropic()

# Example: Streaming Chat Completion (Messages API)
print("Streaming Response:")
full_response = ""
with client.messages.stream(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Write a short poem about the ocean."}
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
        full_response += text

print("\n\n--- End of Stream ---")
print("Full response received.") # Full response is already printed during the stream

# You can access final message details after the stream is finished
final_message = stream.get_final_message()
print("\nUsage details:", final_message.usage)

# End AgentOps session
agentops.end_session('Success') 