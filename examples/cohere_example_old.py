import cohere
import agentops
from dotenv import load_dotenv
load_dotenv()

agentops.init()
co = cohere.Client()

chat = co.chat(
    chat_history=[
        {"role": "SYSTEM", "message": "You are a boomer who only types in CAPS"},
        {
            "role": "CHATBOT",
            "message": "WHO YOU CALLING BOOMER - SENT FROM MY IPHONE",
        },
    ],
    message="What is the latest version of Cohere?",
    connectors=[{"id": "web-search", "options": {"site": "https://docs.cohere.com/changelog"}}]
)

print(chat)

# chat = co.chat(
#     chat_history=[
#         {"role": "SYSTEM", "message": "You are a boomer who only types in CAPS"},
#         {
#             "role": "CHATBOT",
#             "message": "WHO YOU CALLING BOOMER - SENT FROM MY IPHONE",
#         },
#     ],
#     message="Is it pronounced ceaux-hear or co-hehray?"
# )

# print(chat)

# stream = co.chat_stream(
#     message="Write me a haiku about the synergies between Cohere and AgentOps"
# )

# for event in stream:
#     if event.event_type == "text-generation":
#         print(event.text, end='')


agentops.end_session('Success')
