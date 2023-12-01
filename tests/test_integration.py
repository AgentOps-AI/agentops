from langchain.agents import AgentType, Tool, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from agentops.integrations import CallbackHandler
from agentops import Client

ao_client = Client()

tools = [
    Tool(
        name="movie getter",
        func=lambda x: 'Citizen Kane',
        description="movie getter tool",
    ),
]


llm = ChatOpenAI(model_name="gpt-3.5-turbo")

handler = CallbackHandler(client=ao_client)
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    memory=ConversationBufferMemory(memory_key="chat_history"),
    callbacks=[handler]
)

agent_executor.run("what are some movies showing 9/21/2023?",
                   callbacks=[handler])
