import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import tool, AgentExecutor, create_openai_tools_agent
from dotenv import load_dotenv
from agentops.partners.langchain_callback_handler import (
    LangchainCallbackHandler as AgentOpsLangchainCallbackHandler,
    AsyncLangchainCallbackHandler as AgentOpsAsyncLangchainCallbackHandler,
)

load_dotenv()

AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# Sync test
def run_sync_test():
    agentops_handler = AgentOpsLangchainCallbackHandler(
        api_key=AGENTOPS_API_KEY, default_tags=["Langchain", "Sync Handler Test"]
    )

    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        callbacks=[agentops_handler],
        model="gpt-4o-mini",
        streaming=False,  # Disable streaming for sync handler
    )

    @tool
    def find_movie(genre) -> str:
        """Find available movies"""
        if genre == "drama":
            return "Dune 2"
        else:
            return "Pineapple Express"

    tools = [find_movie]
    for t in tools:
        t.callbacks = [agentops_handler]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. Respond only in Spanish."),
            ("user", "{input}"),
            ("system", "Here is the current conversation state:\n{agent_scratchpad}"),
        ]
    )

    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, callbacks=[agentops_handler])

    return agent_executor.invoke({"input": "What comedies are playing?"})


# Async test
async def run_async_test():
    agentops_handler = AgentOpsAsyncLangchainCallbackHandler(
        api_key=AGENTOPS_API_KEY, default_tags=["Langchain", "Async Handler Test"]
    )

    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, callbacks=[agentops_handler], model="gpt-4o-mini", streaming=True)

    @tool
    def find_movie(genre) -> str:
        """Find available movies"""
        if genre == "drama":
            return "Dune 2"
        else:
            return "Pineapple Express"

    tools = [find_movie]
    for t in tools:
        t.callbacks = [agentops_handler]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant. Respond only in Spanish."),
            ("user", "{input}"),
            ("system", "Here is the current conversation state:\n{agent_scratchpad}"),
        ]
    )

    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, callbacks=[agentops_handler])

    return await agent_executor.ainvoke({"input": "What comedies are playing?"})


async def main():
    # Run sync test
    print("Running sync test...")
    sync_result = run_sync_test()
    print(f"Sync test result: {sync_result}\n")

    # Run async test
    print("Running async test...")
    async_result = await run_async_test()
    print(f"Async test result: {async_result}")


if __name__ == "__main__":
    asyncio.run(main())
