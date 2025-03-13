import asyncio

from .manager import ResearchManager

from dotenv import load_dotenv
import os
import agentops

load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "your-api-key"
agentops.init(api_key=AGENTOPS_API_KEY)


async def main() -> None:
    query = input("What would you like to research? ")
    await ResearchManager().run(query)


if __name__ == "__main__":
    asyncio.run(main())
