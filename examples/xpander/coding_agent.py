"""
Copyright (c) 2025 Xpander, Inc. All rights reserved.
Modified to use AgentOps callback handlers for tool instrumentation.
Single-file implementation combining MyAgent and XpanderEventListener.
"""
# ruff: noqa: E402

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

import agentops

print("🔧 Initializing AgentOps...")
agentops.init(
    api_key=os.getenv("AGENTOPS_API_KEY"),
    trace_name="my-xpander-coding-agent-callbacks",
    default_tags=["xpander", "coding-agent", "callbacks"],
)
print("✅ AgentOps initialized")

print("📦 Importing xpander_sdk...")
from xpander_sdk import XpanderClient, LLMProvider, LLMTokens, Tokens, Agent
from xpander_utils.events import XpanderEventListener, AgentExecutionResult, AgentExecution, ExecutionStatus
from openai import AsyncOpenAI

# Simple logger setup
logger.remove()
logger.add(sys.stderr, format="{time:HH:mm:ss} | {message}", level="INFO")


class MyAgent:
    def __init__(self):
        logger.info("🚀 Initializing MyAgent...")

        # Load config
        config_path = Path(__file__).parent / "xpander_config.json"
        config = json.loads(config_path.read_text())

        # Get API keys
        xpander_key = config.get("api_key") or os.getenv("XPANDER_API_KEY")
        agent_id = config.get("agent_id") or os.getenv("XPANDER_AGENT_ID")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not all([xpander_key, agent_id, openai_key]):
            raise ValueError("Missing required API keys")

        # Initialize
        self.openai = AsyncOpenAI(api_key=openai_key)
        xpander_client = XpanderClient(api_key=xpander_key)
        self.agent_backend: Agent = xpander_client.agents.get(agent_id=agent_id)
        self.agent_backend.select_llm_provider(LLMProvider.OPEN_AI)

        logger.info(f"Agent: {self.agent_backend.name}")
        logger.info(f"Tools: {len(self.agent_backend.tools)} available")
        logger.info("✅ Ready!")

    async def run(self, user_txt_input: str) -> dict:
        step = 0
        start_time = time.perf_counter()
        tokens = Tokens(worker=LLMTokens(0, 0, 0))
        try:
            while not self.agent_backend.is_finished():
                step += 1
                logger.info(f"Step {step} - Calling LLM...")
                response = await self.openai.chat.completions.create(
                    model="gpt-4.1",
                    messages=self.agent_backend.messages,
                    tools=self.agent_backend.get_tools(),
                    tool_choice=self.agent_backend.tool_choice,
                    temperature=0,
                )
                if hasattr(response, "usage"):
                    tokens.worker.prompt_tokens += response.usage.prompt_tokens
                    tokens.worker.completion_tokens += response.usage.completion_tokens
                    tokens.worker.total_tokens += response.usage.total_tokens

                self.agent_backend.add_messages(response.model_dump())
                self.agent_backend.report_execution_metrics(llm_tokens=tokens, ai_model="gpt-4.1")
                tool_calls = self.agent_backend.extract_tool_calls(response.model_dump())

                if tool_calls:
                    logger.info(f"Executing {len(tool_calls)} tools...")
                    tool_results = await asyncio.to_thread(self.agent_backend.run_tools, tool_calls)
                    for res in tool_results:
                        emoji = "✅" if res.is_success else "❌"
                        logger.info(f"Tool result: {emoji} {res.function_name}")

            duration = time.perf_counter() - start_time
            logger.info(f"Done! Duration: {duration:.1f}s | Total tokens: {tokens.worker.total_tokens}")
            result = self.agent_backend.retrieve_execution_result()
            return {"result": result.result, "thread_id": result.memory_thread_id}
        except Exception as e:
            logger.error(f"Exception: {e}")
            raise


# === Load Configuration ===
logger.info("[xpander_handler] Loading xpander_config.json")
config_path = Path(__file__).parent / "xpander_config.json"
with open(config_path, "r") as config_file:
    xpander_config: dict = json.load(config_file)
logger.info(f"[xpander_handler] Loaded config: {xpander_config}")

# === Initialize Event Listener ===
logger.info(f"[xpander_handler] Initializing XpanderEventListener with config: {xpander_config}")
listener = XpanderEventListener(**xpander_config)
logger.info(f"[xpander_handler] Listener initialized: {listener}")


# === Define Execution Handler ===
async def on_execution_request(execution_task: AgentExecution) -> AgentExecutionResult:
    logger.info(f"[on_execution_request] Called with execution_task: {execution_task}")
    my_agent = MyAgent()
    logger.info(f"[on_execution_request] Instantiated MyAgent: {my_agent}")

    user_info = ""
    user = getattr(execution_task.input, "user", None)

    if user:
        name = f"{user.first_name} {user.last_name}".strip()
        email = getattr(user, "email", "")
        user_info = f"👤 From user: {name}\n📧 Email: {email}"

    IncomingEvent = f"\n📨 Incoming message: {execution_task.input.text}\n{user_info}"

    logger.info(f"[on_execution_request] IncomingEvent: {IncomingEvent}")
    logger.info(f"[on_execution_request] Calling agent_backend.init_task with execution={execution_task.model_dump()}")
    my_agent.agent_backend.init_task(execution=execution_task.model_dump())

    # extract just the text input for quick start purpose. for more robust use the object
    user_txt_input = execution_task.input.text
    logger.info(f"[on_execution_request] Running agent with user_txt_input: {user_txt_input}")
    try:
        await my_agent.run(user_txt_input)
        logger.info("[on_execution_request] Agent run completed")
        execution_result = my_agent.agent_backend.retrieve_execution_result()
        logger.info(f"[on_execution_request] Execution result: {execution_result}")
        result_obj = AgentExecutionResult(
            result=execution_result.result,
            is_success=execution_result.status == ExecutionStatus.COMPLETED,
        )
        logger.info(f"[on_execution_request] Returning AgentExecutionResult: {result_obj}")
        return result_obj
    except Exception as e:
        logger.error(f"[on_execution_request] Exception: {e}")
        raise
    finally:
        logger.info("[on_execution_request] Exiting handler")


# === Register Callback ===
logger.info("[xpander_handler] Registering on_execution_request callback")
listener.register(on_execution_request=on_execution_request)
logger.info("[xpander_handler] Callback registered")


# Example usage for direct interaction
if __name__ == "__main__":

    async def main():
        agent = MyAgent()
        while True:
            task = input("\nAsk Anything (Type exit to end) \nInput: ")
            if task.lower() == "exit":
                break
            agent.agent_backend.add_task(input=task)
            result = await agent.run(task)
            print(f"\nResult: {result['result']}")

    asyncio.run(main())
