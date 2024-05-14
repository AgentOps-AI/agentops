import cohere
import agentops
from dotenv import load_dotenv
load_dotenv()

agentops.init()
co = cohere.Client()

chat = co.chat(
    chat_history=[
        {"role": "USER", "message": "Who discovered gravity?"},
        {
            "role": "CHATBOT",
            "message": "The man who is widely credited with discovering gravity is Sir Isaac Newton",
        },
    ],
    message="What year was he born?",
)

print(chat)

stream = co.chat_stream(
    message="Tell me a short story"
)

for event in stream:
    if event.event_type == "text-generation":
        print(event.text, end='')

agentops.end_session('Success')
