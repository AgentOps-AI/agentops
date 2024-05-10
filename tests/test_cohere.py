import cohere
import agentops
from dotenv import load_dotenv
load_dotenv()

agentops.init(endpoint='http://localhost:8000')
co = cohere.Client()

chat = co.chat(
    chat_history=[
        {
            "role": "CHATBOT",
            "content": "test"
        }
    ],
    message="hello world!",
    model="command"
)

print(chat)

# import cohere
# import agentops
# from dotenv import load_dotenv
# load_dotenv()

# agentops.init(endpoint='http://localhost:8000')
# co = cohere.Client()

# stream = co.chat_stream(
#     message="Tell me a short story"
# )

# for event in stream:
#     if event.event_type == "text-generation":
#         print(event.text, end='')
