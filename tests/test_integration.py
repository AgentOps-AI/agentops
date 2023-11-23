from langchain.agents import AgentType, Tool, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
import os

tools = [
    Tool(
        name="mock",
        func=lambda x: 'Citizen Kane',
        description="mock tool",
    ),
]


llm = ChatOpenAI(model_name="gpt-3.5-turbo")

agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    memory=ConversationBufferMemory(memory_key="chat_history")
)

agent_executor.invoke(
    {"input": "what are some movies showing 9/21/2023?"})["output"]
