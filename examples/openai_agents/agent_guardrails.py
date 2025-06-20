# # OpenAI Agents Guardrails Demonstration
#
# This notebook demonstrates guardrails using the Agents SDK and how one can observe them using the AgentOps platform.

# Install required packages
# %pip install agentops
# %pip install openai-agents
# %pip install dotenv pydantic

# Import dependencies
from pydantic import BaseModel
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
)

# Initialize agentops
import agentops

# Load API keys
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

agentops.init(api_key=os.environ["AGENTOPS_API_KEY"], tags=["agentops-example"])


# OpenAI Agents SDK guardrail example with AgentOps observability
class MathHomeworkOutput(BaseModel):
    is_math_homework: bool
    reasoning: str


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking you to do their math homework.",
    output_type=MathHomeworkOutput,
)


@input_guardrail
async def math_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_math_homework,
    )


agent = Agent(
    name="Customer support agent",
    instructions="You are a customer support agent. You help customers with their questions.",
    input_guardrails=[math_guardrail],
)


async def main():
    # This should trip the guardrail
    try:
        await Runner.run(agent, "Hello, can you help me solve for x: 2x + 3 = 11?")
        print("Guardrail didn't trip - this is unexpected")

    except InputGuardrailTripwireTriggered:
        print("Math homework guardrail tripped")


if __name__ == "__main__":
    asyncio.run(main())
