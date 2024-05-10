import cohere
import agentops
from dotenv import load_dotenv
load_dotenv()

agentops.init(endpoint='http://localhost:8000')
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
