import asyncio
import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from tokencost import update_token_costs

# HACK to add deploy directory to Python path for jockey imports
deploy_path = Path(__file__).parent.parent / "deploy"
if deploy_path.exists():
    sys.path.insert(0, str(deploy_path))


load_dotenv()
from agentops.app import app


async def update_tokencosts_periodically():
    while True:
        logging.info("Updating Token Costs")
        await update_token_costs()
        await asyncio.sleep(3600)


async def run_server():
    # Start the token cost update task
    update_tokencosts_task = asyncio.create_task(update_tokencosts_periodically())

    # Configure uvicorn server
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, reload=True, log_level="info")

    # Create and start the server
    server = uvicorn.Server(config)
    await server.serve()

    # Wait for the token cost update task
    await update_tokencosts_task


if __name__ == "__main__":
    asyncio.run(run_server())
