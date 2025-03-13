import asyncio

from agents import Agent, FileSearchTool, Runner, trace

from dotenv import load_dotenv
import os
import agentops

load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "your-api-key"
agentops.init(api_key=AGENTOPS_API_KEY)


async def main():
    agent = Agent(
        name="File searcher",
        instructions="You are a helpful agent.",
        tools=[
            FileSearchTool(
                max_num_results=3,
                vector_store_ids=["vs_67bf88953f748191be42b462090e53e7"],
                include_search_results=True,
            )
        ],
    )

    with trace("File search example"):
        result = await Runner.run(agent, "Be concise, and tell me 1 sentence about Arrakis I might not know.")
        print(result.final_output)
        """
        Arrakis, the desert planet in Frank Herbert's "Dune," was inspired by the scarcity of water
        as a metaphor for oil and other finite resources.
        """

        print("\n".join([str(out) for out in result.new_items]))
        """
        {"id":"...", "queries":["Arrakis"], "results":[...]}
        """


if __name__ == "__main__":
    asyncio.run(main())
