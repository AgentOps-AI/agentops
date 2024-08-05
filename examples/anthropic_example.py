import anthropic
import agentops
from dotenv import load_dotenv

load_dotenv()

agentops.init(tags=["anthropic", "agentops-demo"])
client = anthropic.Anthropic()

stream = client.messages.create(
    messages=[
        {
            "role": "user",
            "content": "Tell me everything you can about AgentOps",
        },
        {
            "role": "assistant",
            "content": "This is my answer:",
        },
    ],
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    stream=True,
)

response = ""
for event in stream:
    if event.type == "content_block_start":
        response += event.content_block.text
    elif event.type == "content_block_start":
        response += event.delta.text
    elif event.type == "message_stop":
        print("\n")
        print(response)
        print("\n")

agentops.end_session("Success")
