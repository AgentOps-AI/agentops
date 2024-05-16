import cohere
import agentops
from dotenv import load_dotenv
load_dotenv()

agentops.init(tags=["cohere"])
co = cohere.Client()

stream = co.chat_stream(
    message="Tell me everything you can about AgentOps",
    connectors=[{"id": "web-search"}]
)

response = ""
for event in stream:
    if event.event_type == "text-generation":
        response += event.text
        print(event.text, end='')
    elif event.event_type == "stream-end":
        print(event)

print("\n")

stream = co.chat_stream(
    chat_history=[
        {"role": "SYSTEM", "message": "You are Adam Silverman: die-hard advocate of AgentOps, leader in AI Agent observability"},
        {
            "role": "CHATBOT",
            "message": "How's your day going? I'd like to tell you about AgentOps: {response}",
        },
    ],
    message="Based on your newfound knowledge of AgentOps, is Cohere a suitable partner for them and how could they integrate?",
    connectors=[{"id": "web-search"}]
)

response = ""
for event in stream:
    if event.event_type == "text-generation":
        response += event.text
        print(event.text, end='')
    elif event.event_type == "stream-end":
        print(event)

print("\n")

agentops.end_session('Success')
