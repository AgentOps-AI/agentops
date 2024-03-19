import os
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from dotenv import load_dotenv
from langchain.agents import tool
from agentops.langchain_callback_handler import LangchainCallbackHandler as AgentOpsLangchainCallbackHandler


load_dotenv()


AGENTOPS_API_KEY = os.environ.get('AGENTOPS_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

agentops_handler = AgentOpsLangchainCallbackHandler(api_key=AGENTOPS_API_KEY, tags=['Langchain Example'])

print("Agent Ops session ID: " + str(agentops_handler.session_id))
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY,
                 callbacks=[agentops_handler],
                 model='gpt-3.5-turbo')


# @tool
# def find_movie(genre, actor) -> str:
#     """Find available movies"""
#     # raise ValueError("This is an intentional error for testing.")
#     if genre == 'drama':
#         if actor == 'Zendaya':
#             return 'Dune 2'
#         else:
#             return 'Citizen Kane'
#     else:
#         return 'Pineapple Express'


@tool
def find_movie(genre) -> str:
    """Find available movies"""
    # raise ValueError("This is an intentional error for testing.")
    if genre == 'drama':
        return 'Dune 2'
    else:
        return 'Pineapple Express'


tools = [find_movie]

for t in tools:
    t.callbacks = [agentops_handler]

agent = initialize_agent(tools,
                         llm,
                         agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                         verbose=True,
                         callbacks=[agentops_handler],  # You must pass in a callback handler to record your agent
                         handle_parsing_errors=True)


agent.run("What comedies are playing?", callbacks=[agentops_handler])
# agent.run("What dramas are playing?", callbacks=[agentops_handler])

# agent.run("What dramas are playing starring zendaya?", callbacks=[agentops_handler])
# agent.run("What movies are playing starring zendaya?", callbacks=[agentops_handler])
