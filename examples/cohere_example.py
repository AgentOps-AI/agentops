import cohere
import agentops
from dotenv import load_dotenv
load_dotenv()

agentops.init()
# co = cohere.Client()

# stream = co.chat_stream(
#     message="Write me a haiku about the synergies between Cohere and AgentOps"
# )

# for event in stream:
#     if event.event_type == "text-generation":
#         print(event.text, end='')


# chat = co.chat(
#     chat_history=[
#         {"role": "SYSTEM", "message": "You are Adam Silverman: die-hard advocate of AgentOps, leader in AI Agent observability"},
#         {
#             "role": "CHATBOT",
#             "message": "How's your day going?",
#         },
#     ],
#     message="Great! Cohere is looking for an observability partner, know of any good ones?",
#     connectors=[{"id": "web-search", "options": {"site": "https://docs.agentops.ai/v1/quickstart"}}]
# )

# print(chat)

agentops.end_session('Success')
