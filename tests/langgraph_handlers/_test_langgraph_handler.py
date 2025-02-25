import asyncio
import os
from uuid import UUID
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from agentops.partners.langgraph_callback_handler import (
    LanggraphCallbackHandler,
    AsyncLanggraphCallbackHandler,
)

load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def create_sync_workflow(handler: LanggraphCallbackHandler):
    """Create a synchronous movie recommendation workflow"""
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", callbacks=[handler])

    @tool
    def movie_finder(genre: str) -> str:
        """Find movies by genre. Returns movie title as string."""
        if "comedy" in genre.lower():
            return "Pineapple Express"
        return "Dune: Part 2"

    movie_finder.callbacks = [handler]

    workflow = StateGraph(state_schema=dict)

    def tool_node(state: dict):
        return {"movie": movie_finder.invoke(state.get("genre", ""))}

    def llm_node(state: dict):
        response = llm.invoke([HumanMessage(content=f"Create a tweet about this movie: {state['movie']}")])
        return {"response": response.content}

    workflow.add_node("find_movie", tool_node)
    workflow.add_node("generate_content", llm_node)

    workflow.set_entry_point("find_movie")
    workflow.add_edge("find_movie", "generate_content")
    workflow.add_edge("generate_content", END)

    return workflow.compile()


def create_async_workflow(handler: AsyncLanggraphCallbackHandler):
    """Create an asynchronous movie recommendation workflow"""
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", streaming=True, callbacks=[handler])

    @tool
    async def async_movie_finder(genre: str) -> str:
        """Find movies by genre (async version). Returns movie title as string."""
        if "horror" in genre.lower():
            return "Talk to Me"
        return "Oppenheimer"

    async_movie_finder.callbacks = [handler]

    workflow = StateGraph(state_schema=dict)

    async def async_tool_node(state: dict):
        return {"movie": await async_movie_finder.ainvoke(state.get("genre", ""))}

    async def async_llm_node(state: dict):
        response = await llm.ainvoke([HumanMessage(content=f"Write a LinkedIn post about: {state['movie']}")])
        return {"response": response.content}

    workflow.add_node("find_movie", async_tool_node)
    workflow.add_node("generate_content", async_llm_node)

    workflow.set_entry_point("find_movie")
    workflow.add_edge("find_movie", "generate_content")
    workflow.add_edge("generate_content", END)

    return workflow.compile()


# Sync test


def run_sync_test():
    """Test synchronous workflow with callback handler"""
    handler = LanggraphCallbackHandler(api_key=AGENTOPS_API_KEY, default_tags=["langgraph", "sync-test"])

    app = create_sync_workflow(handler)
    result = app.invoke({"genre": "comedy"})

    assert isinstance(handler.current_session_ids, list), "Session tracking failed"
    assert len(handler.current_session_ids) > 0, "No session IDs recorded"

    return result


# Async test


async def run_async_test():
    """Test asynchronous workflow with callback handler"""
    handler = AsyncLanggraphCallbackHandler(api_key=AGENTOPS_API_KEY, default_tags=["langgraph", "async-test"])

    app = create_async_workflow(handler)
    result = await app.ainvoke({"genre": "historical drama"})

    assert isinstance(handler.current_session_ids, list), "Async session tracking failed"
    assert len(handler.current_session_ids) > 0, "No async session IDs recorded"

    return result


async def main():
    print("Running sync workflow test...")
    sync_result = run_sync_test()
    print(f"Sync test result: {sync_result}\n")

    print("Running async workflow test...")
    async_result = await run_async_test()
    print(f"Async test result: {async_result}")


if __name__ == "__main__":
    asyncio.run(main())
