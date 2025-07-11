# # OpenAI Agents Patterns Demonstration
#
# This notebook demonstrates various common agentic patterns using the Agents SDK and how one can observe them using the AgentOps platform.
#
# **Note: This notebook was edited using Claude MCP NotebookEdit tool!**
#
# ## General Flow
#
# This notebook will walk you through several key agent patterns:
#
# 1. **Agents as Tools** - Using agents as callable tools within other agents
# 2. **Deterministic Flows** - Breaking down tasks into sequential steps
# 3. **Forcing Tool Use** - Controlling when and how agents use tools
# 4. **Input Guardrails** - Validating inputs before agent execution
# 5. **LLM as a Judge** - Using LLMs to evaluate and improve outputs
# 6. **Output Guardrails** - Validating outputs after agent execution
# 7. **Parallelization** - Running multiple agents concurrently
# 8. **Routing** - Directing requests to specialized agents
# 9. **Streaming Guardrails** - Real-time validation during streaming
#
# Each pattern demonstrates how AgentOps automatically tracks and monitors your agent interactions, providing valuable insights into performance, costs, and behavior.
# ## Prerequisites
#
# Before running this notebook, you'll need:
#
# 1. **AgentOps Account**: Create a free account at [app.agentops.ai](https://app.agentops.ai)
# 2. **AgentOps API Key**: Obtain your API key from your AgentOps dashboard
# 3. **OpenAI API Key**: Get your API key from [platform.openai.com](https://platform.openai.com)
#
# Make sure to set these as environment variables or create a `.env` file in your project root with:
#
# ```
# AGENTOPS_API_KEY=your_agentops_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
# ```
# # Install required packages
# %pip install agentops
# %pip install openai-agents
# %pip install pydotenv
# Required imports - Note: agentops must be imported before agents
import asyncio
import os
import uuid
from typing import Any, Literal
from dataclasses import dataclass
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Import agentops FIRST
import agentops

# Then import agents
from agents import (
    Agent,
    ItemHelpers,
    MessageOutputItem,
    Runner,
    trace,
    TResponseInputItem,
    FunctionToolResult,
    ModelSettings,
    RunContextWrapper,
    ToolsToFinalOutputFunction,
    ToolsToFinalOutputResult,
    function_tool,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    input_guardrail,
    output_guardrail,
)

from openai.types.responses import ResponseTextDeltaEvent

# Load environment variables and set API keys
load_dotenv()
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# Initialize AgentOps
agentops.init(
    auto_start_session=False,
    trace_name="OpenAI Agents Patterns",
    tags=["openai-agents", "patterns", "agentops-example"],
)
tracer = agentops.start_trace(
    trace_name="OpenAI Agents Patterns",
    tags=["openai-agents", "patterns", "agentops-example"],
)
# Note: tracer will be defined in each section's cell for clarity, using the specific tags for that pattern.
# ## 1. Agents as Tools Pattern
#
# The mental model for handoffs is that the new agent "takes over". It sees the previous conversation history, and owns the conversation from that point onwards. However, this is not the only way to use agents. You can also use agents as a tool - the tool agent goes off and runs on its own, and then returns the result to the original agent.
#
# For example, you could model the translation task above as tool calls instead: rather than handing over to the language-specific agent, you could call the agent as a tool, and then use the result in the next step. This enables things like translating multiple languages at once.
#
# This pattern demonstrates using agents as callable tools within other agents. The orchestrator agent receives a user message and then picks which specialized agents to call as tools.
# Agents as Tools Pattern Example

# Define specialized translation agents
spanish_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
    handoff_description="An english to spanish translator",
)

french_agent = Agent(
    name="french_agent",
    instructions="You translate the user's message to French",
    handoff_description="An english to french translator",
)

italian_agent = Agent(
    name="italian_agent",
    instructions="You translate the user's message to Italian",
    handoff_description="An english to italian translator",
)

# Orchestrator agent that uses other agents as tools
orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=(
        "You are a translation agent. You use the tools given to you to translate."
        "If asked for multiple translations, you call the relevant tools in order."
        "You never translate on your own, you always use the provided tools."
    ),
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate the user's message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate the user's message to French",
        ),
        italian_agent.as_tool(
            tool_name="translate_to_italian",
            tool_description="Translate the user's message to Italian",
        ),
    ],
)

synthesizer_agent = Agent(
    name="synthesizer_agent",
    instructions="You inspect translations, correct them if needed, and produce a final concatenated response.",
)


async def run_agents_as_tools_demo():
    msg = "Hello, how are you today?"
    print(f"Input: {msg}")

    with trace("Orchestrator evaluator"):
        orchestrator_result = await Runner.run(orchestrator_agent, msg)

        for item in orchestrator_result.new_items:
            if isinstance(item, MessageOutputItem):
                text = ItemHelpers.text_message_output(item)
                if text:
                    print(f"  - Translation step: {text}")

        synthesizer_result = await Runner.run(synthesizer_agent, orchestrator_result.to_input_list())

    print(f"Final response: {synthesizer_result.final_output}")


# Run the demo
# await run_agents_as_tools_demo()
# ## 2. Deterministic Flow Pattern
#
# A common tactic is to break down a task into a series of smaller steps. Each task can be performed by an agent, and the output of one agent is used as input to the next. For example, if your task was to generate a story, you could break it down into the following steps:
#
# 1. Generate an outline
# 2. Generate the story
# 3. Generate the ending
#
# Each of these steps can be performed by an agent. The output of one agent is used as input to the next.
#
# This pattern demonstrates breaking down a complex task into a series of smaller, sequential steps. Each step is performed by an agent, and the output of one agent is used as input to the next.
# Deterministic Flow Pattern Example

# Define the story generation workflow
story_outline_agent = Agent(
    name="story_outline_agent",
    instructions="Generate a very short story outline based on the user's input.",
)


class OutlineCheckerOutput(BaseModel):
    good_quality: bool
    is_scifi: bool


outline_checker_agent = Agent(
    name="outline_checker_agent",
    instructions="Read the given story outline, and judge the quality. Also, determine if it is a scifi story.",
    output_type=OutlineCheckerOutput,
)

story_agent = Agent(
    name="story_agent",
    instructions="Write a short story based on the given outline.",
    output_type=str,
)


async def run_deterministic_flow_demo():
    input_prompt = "A story about robots exploring space"
    print(f"Input: {input_prompt}")

    with trace("Deterministic story flow"):
        # 1. Generate an outline
        outline_result = await Runner.run(story_outline_agent, input_prompt)
        print("Outline generated")

        # 2. Check the outline
        outline_checker_result = await Runner.run(outline_checker_agent, outline_result.final_output)

        # 3. Add a gate to stop if the outline is not good quality or not a scifi story
        assert isinstance(outline_checker_result.final_output, OutlineCheckerOutput)
        if not outline_checker_result.final_output.good_quality:
            print("Outline is not good quality, so we stop here.")
            return

        if not outline_checker_result.final_output.is_scifi:
            print("Outline is not a scifi story, so we stop here.")
            return

        print("Outline is good quality and a scifi story, so we continue to write the story.")

        # 4. Write the story
        story_result = await Runner.run(story_agent, outline_result.final_output)
        print(f"Story: {story_result.final_output}")


# Run the demo
# await run_deterministic_flow_demo()
# ## 3. Forcing Tool Use Pattern
#
# This pattern shows how to force an agent to use a tool using `ModelSettings(tool_choice=\"required\")`. This is useful when you want to ensure the agent always uses a specific tool rather than generating a response directly.
#
# You can run it with 3 options:
# 1. `default`: The default behavior, which is to send the tool output to the LLM. In this case, `tool_choice` is not set, because otherwise it would result in an infinite loop - the LLM would call the tool, the tool would run and send the results to the LLM, and that would repeat (because the model is forced to use a tool every time.)
# 2. `first_tool_result`: The first tool result is used as the final output.
# 3. `custom`: A custom tool use behavior function is used. The custom function receives all the tool results, and chooses to use the first tool result to generate the final output.
#
# For this demo, we'll allow the user to choose which tool use behavior to test:
# Forcing Tool Use Pattern Example


# Define the weather tool and agent
class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str


@function_tool
def get_weather(city: str) -> Weather:
    print("[debug] get_weather called")
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind")


async def custom_tool_use_behavior(
    context: RunContextWrapper[Any], results: list[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    weather: Weather = results[0].output
    return ToolsToFinalOutputResult(is_final_output=True, final_output=f"{weather.city} is {weather.conditions}.")


async def run_forcing_tool_use_demo(tool_use_behavior: str):
    print(f"Testing {tool_use_behavior} behavior:")

    if tool_use_behavior == "default":
        behavior: Literal["run_llm_again", "stop_on_first_tool"] | ToolsToFinalOutputFunction = "run_llm_again"
    elif tool_use_behavior == "first_tool":
        behavior = "stop_on_first_tool"
    elif tool_use_behavior == "custom":
        behavior = custom_tool_use_behavior

    agent = Agent(
        name="Weather agent",
        instructions="You are a helpful agent.",
        tools=[get_weather],
        tool_use_behavior=behavior,
        model_settings=ModelSettings(tool_choice="required" if tool_use_behavior != "default" else None),
    )

    result = await Runner.run(agent, input="What's the weather in Tokyo?")
    print(f"Result: {result.final_output}")


async def run_all_forcing_tool_use_demos():
    """Run all three tool use behavior demos automatically"""
    print("Running all tool use behavior demos:")
    print("1. default - Send tool output to LLM")
    print("2. first_tool - Use first tool result as final output")
    print("3. custom - Use custom tool behavior function")
    print()

    # Test all three behaviors
    for behavior in ["default", "first_tool", "custom"]:
        await run_forcing_tool_use_demo(behavior)
        print("-" * 50)


# Run the demo
# await run_all_forcing_tool_use_demos()
# ## 4. Input Guardrails Pattern
#
# Related to parallelization, you often want to run input guardrails to make sure the inputs to your agents are valid. For example, if you have a customer support agent, you might want to make sure that the user isn't trying to ask for help with a math problem.
#
# You can definitely do this without any special Agents SDK features by using parallelization, but we support a special guardrail primitive. Guardrails can have a \"tripwire\" - if the tripwire is triggered, the agent execution will immediately stop and a `GuardrailTripwireTriggered` exception will be raised.
#
# This is really useful for latency: for example, you might have a very fast model that runs the guardrail and a slow model that runs the actual agent. You wouldn't want to wait for the slow model to finish, so guardrails let you quickly reject invalid inputs.
#
# This pattern demonstrates how to use input guardrails to validate user inputs before they reach the main agent. Guardrails can prevent inappropriate or off-topic requests from being processed.
# Input Guardrails Pattern Example


# Define the guardrail
class MathHomeworkOutput(BaseModel):
    reasoning: str
    is_math_homework: bool


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking you to do their math homework.",
    output_type=MathHomeworkOutput,
)


@input_guardrail
async def math_guardrail(
    context: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=context.context)
    final_output = result.final_output_as(MathHomeworkOutput)

    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=final_output.is_math_homework,
    )


async def run_input_guardrails_demo():
    agent = Agent(
        name="Customer support agent",
        instructions="You are a customer support agent. You help customers with their questions.",
        input_guardrails=[math_guardrail],
    )

    # Test with different inputs
    test_inputs = ["What's the capital of California?", "Can you help me solve for x: 2x + 5 = 11"]

    for user_input in test_inputs:
        print(f"Testing input: {user_input}")
        try:
            result = await Runner.run(agent, user_input)
            print(f"Response: {result.final_output}")
        except InputGuardrailTripwireTriggered:
            message = "Sorry, I can't help you with your math homework."
            print(f"Guardrail triggered: {message}")
        print()


# Run the demo
# await run_input_guardrails_demo()
# ## 5. LLM as a Judge Pattern
#
# LLMs can often improve the quality of their output if given feedback. A common pattern is to generate a response using a model, and then use a second model to provide feedback. You can even use a small model for the initial generation and a larger model for the feedback, to optimize cost.
#
# For example, you could use an LLM to generate an outline for a story, and then use a second LLM to evaluate the outline and provide feedback. You can then use the feedback to improve the outline, and repeat until the LLM is satisfied with the outline.
#
# This pattern shows how to use one LLM to evaluate and improve the output of another. The first agent generates content, and the second agent judges the quality and provides feedback for improvement.
# LLM as a Judge Pattern Example

# Define the story generation and evaluation agents
story_outline_generator = Agent(
    name="story_outline_generator",
    instructions=(
        "You generate a very short story outline based on the user's input."
        "If there is any feedback provided, use it to improve the outline."
    ),
)


@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "needs_improvement", "fail"]


evaluator = Agent[None](
    name="evaluator",
    instructions=(
        "You evaluate a story outline and decide if it's good enough."
        "If it's not good enough, you provide feedback on what needs to be improved."
        "Never give it a pass on the first try."
    ),
    output_type=EvaluationFeedback,
)


async def run_llm_as_judge_demo():
    msg = "A story about time travel"
    print(f"Input: {msg}")
    input_items: list[TResponseInputItem] = [{"content": msg, "role": "user"}]

    latest_outline: str | None = None
    iteration = 0
    max_iterations = 3  # Limit iterations for demo

    with trace("LLM as a judge"):
        while iteration < max_iterations:
            iteration += 1
            print(f"Iteration {iteration}:")

            story_outline_result = await Runner.run(
                story_outline_generator,
                input_items,
            )

            input_items = story_outline_result.to_input_list()
            latest_outline = ItemHelpers.text_message_outputs(story_outline_result.new_items)
            print("Story outline generated")

            evaluator_result = await Runner.run(evaluator, input_items)
            result: EvaluationFeedback = evaluator_result.final_output

            print(f"Evaluator score: {result.score}")

            if result.score == "pass":
                print("Story outline is good enough, exiting.")
                break

            print("Re-running with feedback")
            input_items.append({"content": f"Feedback: {result.feedback}", "role": "user"})

    print(f"Final story outline: {latest_outline}")


# Run the demo
# await run_llm_as_judge_demo()
# ## 6. Output Guardrails Pattern
#
# Related to parallelization, you often want to run output guardrails to make sure the outputs from your agents are valid. Guardrails can have a \"tripwire\" - if the tripwire is triggered, the agent execution will immediately stop and a `GuardrailTripwireTriggered` exception will be raised.
#
# This is really useful for latency: for example, you might have a very fast model that runs the guardrail and a slow model that runs the actual agent. You wouldn't want to wait for the slow model to finish, so guardrails let you quickly reject invalid outputs.
#
# This pattern demonstrates how to use output guardrails to validate agent outputs after they are generated. This can help prevent sensitive information from being shared or ensure outputs meet quality standards.
# Output Guardrails Pattern Example


# The agent's output type
class MessageOutput(BaseModel):
    reasoning: str = Field(description="Thoughts on how to respond to the user's message")
    response: str = Field(description="The response to the user's message")
    user_name: str | None = Field(description="The name of the user who sent the message, if known")


@output_guardrail
async def sensitive_data_check(
    context: RunContextWrapper, agent: Agent, output: MessageOutput
) -> GuardrailFunctionOutput:
    phone_number_in_response = "650" in output.response
    phone_number_in_reasoning = "650" in output.reasoning

    return GuardrailFunctionOutput(
        output_info={
            "phone_number_in_response": phone_number_in_response,
            "phone_number_in_reasoning": phone_number_in_reasoning,
        },
        tripwire_triggered=phone_number_in_response or phone_number_in_reasoning,
    )


output_guardrail_agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
    output_type=MessageOutput,
    output_guardrails=[sensitive_data_check],
)


async def run_output_guardrails_demo():
    # Test with safe input
    print("Testing with safe input:")
    try:
        result = await Runner.run(output_guardrail_agent, "What's the capital of California?")
        print("Safe message passed")
        print(f"Response: {result.final_output.response}")
    except OutputGuardrailTripwireTriggered as e:
        print(f"Unexpected guardrail trigger: {e.guardrail_result.output.output_info}")

    print()
    # Test with potentially sensitive input
    print("Testing with potentially sensitive input:")
    try:
        result = await Runner.run(output_guardrail_agent, "My phone number is 650-123-4567. Where do you think I live?")
        print(f"Guardrail didn't trip - this is unexpected. Output: {result.final_output.response}")
    except OutputGuardrailTripwireTriggered as e:
        print(f"Guardrail tripped as expected. Info: {e.guardrail_result.output.output_info}")


# Run the demo
# await run_output_guardrails_demo()
# ## 7. Parallelization Pattern
#
# Running multiple agents in parallel is a common pattern. This can be useful for both latency (e.g. if you have multiple steps that don't depend on each other) and also for other reasons e.g. generating multiple responses and picking the best one.
#
# This example runs a translation agent multiple times in parallel, and then picks the best translation.
#
# This pattern shows how to run multiple agents in parallel to improve latency or generate multiple options to choose from. In this example, we run translation agents multiple times and pick the best result.
# Parallelization Pattern Example

# Define agents for parallelization
spanish_translation_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
)

translation_picker = Agent(
    name="translation_picker",
    instructions="You pick the best Spanish translation from the given options.",
)


async def run_parallelization_demo():
    msg = "Good morning, I hope you have a wonderful day!"
    print(f"Input: {msg}")

    with trace("Parallel translation"):
        # Run three translation agents in parallel
        res_1, res_2, res_3 = await asyncio.gather(
            Runner.run(spanish_translation_agent, msg),
            Runner.run(spanish_translation_agent, msg),
            Runner.run(spanish_translation_agent, msg),
        )

        outputs = [
            ItemHelpers.text_message_outputs(res_1.new_items),
            ItemHelpers.text_message_outputs(res_2.new_items),
            ItemHelpers.text_message_outputs(res_3.new_items),
        ]

        translations = "\\n\\n".join(outputs)
        print(f"\\n\\nTranslations:\\n\\n{translations}")

        best_translation = await Runner.run(
            translation_picker,
            f"Input: {msg}\\n\\nTranslations:\\n{translations}",
        )

    print("\\n\\n-----")
    print(f"Best translation: {best_translation.final_output}")


# Run the demo
# await run_parallelization_demo()
# ## 8. Routing Pattern
#
# In many situations, you have specialized sub-agents that handle specific tasks. You can use handoffs to route the task to the right agent.
#
# For example, you might have a frontline agent that receives a request, and then hands off to a specialized agent based on the language of the request.
#
# This pattern demonstrates handoffs and routing between specialized agents. The triage agent receives the first message and hands off to the appropriate agent based on the language of the request.
# Routing Pattern Example

# Define language-specific agents
french_routing_agent = Agent(
    name="french_agent",
    instructions="You only speak French",
)

spanish_routing_agent = Agent(
    name="spanish_agent",
    instructions="You only speak Spanish",
)

english_routing_agent = Agent(
    name="english_agent",
    instructions="You only speak English",
)

triage_agent = Agent(
    name="triage_agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[french_routing_agent, spanish_routing_agent, english_routing_agent],
)


async def run_routing_demo():
    # Create an ID for this conversation
    conversation_id = str(uuid.uuid4().hex[:16])

    test_messages = ["Hello, how can you help me?", "Bonjour, comment allez-vous?", "Hola, ¿cómo estás?"]

    for msg in test_messages:
        print(f"\nTesting message: {msg}")

        with trace("Routing example", group_id=conversation_id):
            inputs = [{"content": msg, "role": "user"}]
            result = await Runner.run(triage_agent, input=inputs)
            print(f"Response: {result.final_output}")


# Run the demo
# await run_routing_demo()
# ## 9. Streaming Guardrails Pattern
#
# This example shows how to use guardrails as the model is streaming. Output guardrails run after the final output has been generated; this example runs guardrails every N tokens, allowing for early termination if bad output is detected.
#
# The expected output is that you'll see a bunch of tokens stream in, then the guardrail will trigger and stop the streaming.
#
# This pattern shows how to use guardrails during streaming to provide real-time validation. Unlike output guardrails that run after completion, streaming guardrails can interrupt the generation process early.
# Streaming Guardrails Pattern Example

# Define streaming guardrail agent
streaming_agent = Agent(
    name="Assistant",
    instructions=(
        "You are a helpful assistant. You ALWAYS write long responses, making sure to be verbose and detailed."
    ),
)


class GuardrailOutput(BaseModel):
    reasoning: str = Field(description="Reasoning about whether the response could be understood by a ten year old.")
    is_readable_by_ten_year_old: bool = Field(description="Whether the response is understandable by a ten year old.")


guardrail_streaming_agent = Agent(
    name="Checker",
    instructions=(
        "You will be given a question and a response. Your goal is to judge whether the response "
        "is simple enough to be understood by a ten year old."
    ),
    output_type=GuardrailOutput,
    model="gpt-4o-mini",
)


async def check_guardrail(text: str) -> GuardrailOutput:
    result = await Runner.run(guardrail_streaming_agent, text)
    return result.final_output_as(GuardrailOutput)


async def run_streaming_guardrails_demo():
    question = "What is a black hole, and how does it behave?"
    print(f"Question: {question}")

    result = Runner.run_streamed(streaming_agent, question)
    current_text = ""

    # We will check the guardrail every N characters
    next_guardrail_check_len = 300
    guardrail_task = None

    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)
            current_text += event.data.delta

            # Check if it's time to run the guardrail check
            if len(current_text) >= next_guardrail_check_len and not guardrail_task:
                print("\\n[Running guardrail check]")
                guardrail_task = asyncio.create_task(check_guardrail(current_text))
                next_guardrail_check_len += 300

        # Every iteration of the loop, check if the guardrail has been triggered
        if guardrail_task and guardrail_task.done():
            guardrail_result = guardrail_task.result()
            if not guardrail_result.is_readable_by_ten_year_old:
                print("\\n\\n================\\n\\n")
                print(f"Guardrail triggered. Reasoning:\\n{guardrail_result.reasoning}")
                break
            guardrail_task = None

    # Do one final check on the final output
    if current_text:
        guardrail_result = await check_guardrail(current_text)
        if not guardrail_result.is_readable_by_ten_year_old:
            print("\\n\\n================\\n\\n")
            print(f"Final guardrail triggered. Reasoning:\\n{guardrail_result.reasoning}")


# Run the demo
if __name__ == "__main__":
    # Run the streaming guardrails demo
    asyncio.run(run_streaming_guardrails_demo())
    agentops.end_trace(tracer, end_state="Success")

# Streaming Guardrails Pattern Example Complete

# Let's check programmatically that spans were recorded in AgentOps
print("\n" + "=" * 50)
print("Now let's verify that our LLM calls were tracked properly...")
try:
    agentops.validate_trace_spans(trace_context=tracer)
    print("\n✅ Success! All LLM spans were properly recorded in AgentOps.")
except agentops.ValidationError as e:
    print(f"\n❌ Error validating spans: {e}")
    raise

# ## Conclusion
#
# This notebook has demonstrated 9 key agent patterns that are commonly used in production AI applications. Each pattern showcases how agents can be orchestrated to perform complex tasks, validate inputs and outputs, and improve overall application performance.
#
# **AgentOps** provides comprehensive observability for AI agents, automatically tracking all these interactions and providing valuable insights into:
#
# - **Performance metrics** - Latency, throughput, success rates across all agent patterns
# - **Cost analysis** - Token usage, model costs, and optimization opportunities for complex workflows
# - **Quality monitoring** - Output quality assessment, guardrail effectiveness, and pattern success rates
# - **Debugging support** - Detailed trace visualization, error tracking, and workflow analysis
# - **Agent behavior insights** - Understanding how different patterns perform in production environments
# - **Workflow optimization** - Identifying bottlenecks and improving agent coordination
#
# Visit [app.agentops.ai](https://app.agentops.ai) to explore your agent sessions and gain deeper insights into your AI application's behavior.
