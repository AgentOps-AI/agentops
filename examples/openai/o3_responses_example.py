# OpenAI o3 Responses API Example
#
# This example demonstrates AgentOps integration with OpenAI's o3 reasoning model
# through the Responses API. The o3 model excels at complex problem solving and
# multi-step reasoning with tool calls.
#
# This example tests both streaming and non-streaming modes, as well as async versions.

import openai
import agentops
import json
import os
import asyncio
from dotenv import load_dotenv
from agentops.sdk.decorators import agent
from typing import List, Dict, Any

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Initialize AgentOps
agentops.init(
    trace_name="o3-responses-example",
    tags=["o3", "responses-api"],
    auto_start_session=False,
)
tracer = agentops.start_trace(trace_name="o3 Responses API Example", tags=["o3", "responses-api"])

# Initialize OpenAI client
client = openai.OpenAI()
async_client = openai.AsyncOpenAI()

# ANSI escape codes for colors
LIGHT_BLUE = "\033[94m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET_COLOR = "\033[0m"


def create_decision_prompt(scenario: str, available_actions: List[str]) -> str:
    """Create a prompt for decision making."""
    return f"""
You are a strategic decision-making agent. You need to analyze the current scenario and choose the best action from the available options.

Current Scenario:
{scenario}

Available Actions:
{chr(10).join(f"- {action}" for action in available_actions)}

Your goal is to make the best strategic decision based on the scenario. Consider:
1. The immediate benefits of each action
2. Potential long-term consequences
3. Risk vs reward trade-offs
4. Strategic positioning

Reason carefully about the best action to take and explain your reasoning.
"""


@agent
class O3DecisionAgent:
    """A decision-making agent that uses OpenAI's o3 model with the Responses API."""

    def __init__(self, model: str = "o3-mini", color: str = LIGHT_BLUE):
        self.model = model
        self.color = color

    def make_decision_sync(self, scenario: str, available_actions: List[str], stream: bool = False) -> Dict[str, Any]:
        """
        Make a decision using the o3 model synchronously.

        Args:
            scenario: Description of the current situation
            available_actions: List of possible actions to choose from
            stream: Whether to use streaming mode

        Returns:
            Dictionary containing the chosen action and reasoning
        """

        # Define the tool for action selection
        tools = [
            {
                "type": "function",
                "name": "select_action",
                "description": "Select the best action from the available options.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "The selected action from the available options"},
                        "reasoning": {
                            "type": "string",
                            "description": "Detailed reasoning for why this action was chosen",
                        },
                    },
                    "required": ["action", "reasoning"],
                    "additionalProperties": False,
                },
            }
        ]

        # Create the prompt
        system_prompt = create_decision_prompt(scenario, available_actions)
        user_message = f"Select the best action from these options: {available_actions}. Provide your reasoning and make your choice."

        mode_desc = "streaming" if stream else "non-streaming"
        print(f"{self.color}Making decision with o3 model ({mode_desc})...{RESET_COLOR}")
        print(f"{self.color}Scenario: {scenario}{RESET_COLOR}")
        print(f"{self.color}Available actions: {available_actions}{RESET_COLOR}")

        # Make the API call using the Responses API
        if stream:
            response = client.responses.create(
                model=self.model,
                input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                tools=tools,  # type: ignore
                tool_choice="required",
                stream=True,
            )

            # Process streaming response
            tool_call = None

            for event in response:
                if hasattr(event, "type"):
                    if event.type == "response.output_text.delta":
                        # Handle text deltas (if any)
                        pass
                    elif event.type == "response.function_call_arguments.delta":
                        # Tool arguments are accumulated by the API
                        pass
                    elif event.type == "response.output_item.added":
                        # New tool call started
                        if hasattr(event, "output_item") and event.output_item.type == "function_call":
                            pass  # Tool call tracking handled elsewhere
                    elif event.type == "response.completed":
                        # Process final response
                        if hasattr(event, "response") and hasattr(event.response, "output"):
                            for output_item in event.response.output:
                                if output_item.type == "function_call":
                                    tool_call = output_item
                                    break

            if tool_call:
                args = json.loads(tool_call.arguments)
                chosen_action = args["action"]
                reasoning = args["reasoning"]

                print(f"{self.color}Chosen action: {chosen_action}{RESET_COLOR}")
                print(f"{self.color}Tool reasoning: {reasoning}{RESET_COLOR}")

                return {
                    "action": chosen_action,
                    "reasoning": reasoning,
                    "available_actions": available_actions,
                    "scenario": scenario,
                    "mode": "sync_streaming",
                }
        else:
            response = client.responses.create(
                model=self.model,
                input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                tools=tools,  # type: ignore
                tool_choice="required",
            )

            # Process non-streaming response
            tool_call = None
            reasoning_text = ""

            for output_item in response.output:
                if output_item.type == "function_call":
                    tool_call = output_item
                elif output_item.type == "message" and hasattr(output_item, "content"):
                    for content in output_item.content:
                        if hasattr(content, "type"):
                            if content.type == "text" and hasattr(content, "text"):
                                reasoning_text += content.text
                                print(f"{self.color}Reasoning: {content.text}{RESET_COLOR}")
                            elif content.type == "refusal" and hasattr(content, "refusal"):
                                print(f"{self.color}Refusal: {content.refusal}{RESET_COLOR}")

            if tool_call:
                args = json.loads(tool_call.arguments)
                chosen_action = args["action"]
                reasoning = args["reasoning"]

                print(f"{self.color}Chosen action: {chosen_action}{RESET_COLOR}")
                print(f"{self.color}Tool reasoning: {reasoning}{RESET_COLOR}")

                return {
                    "action": chosen_action,
                    "reasoning": reasoning,
                    "full_reasoning": reasoning_text,
                    "available_actions": available_actions,
                    "scenario": scenario,
                    "mode": "sync_non_streaming",
                }

        # Fallback
        print(f"{self.color}No tool call found, using fallback{RESET_COLOR}")
        return {
            "action": available_actions[0] if available_actions else "no_action",
            "reasoning": "Fallback: No tool call received",
            "available_actions": available_actions,
            "scenario": scenario,
            "mode": f"sync_{mode_desc}_fallback",
        }

    async def make_decision_async(
        self, scenario: str, available_actions: List[str], stream: bool = False
    ) -> Dict[str, Any]:
        """
        Make a decision using the o3 model asynchronously.

        Args:
            scenario: Description of the current situation
            available_actions: List of possible actions to choose from
            stream: Whether to use streaming mode

        Returns:
            Dictionary containing the chosen action and reasoning
        """

        # Define the tool for action selection
        tools = [
            {
                "type": "function",
                "name": "select_action",
                "description": "Select the best action from the available options.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "The selected action from the available options"},
                        "reasoning": {
                            "type": "string",
                            "description": "Detailed reasoning for why this action was chosen",
                        },
                    },
                    "required": ["action", "reasoning"],
                    "additionalProperties": False,
                },
            }
        ]

        # Create the prompt
        system_prompt = create_decision_prompt(scenario, available_actions)
        user_message = f"Select the best action from these options: {available_actions}. Provide your reasoning and make your choice."

        mode_desc = "streaming" if stream else "non-streaming"
        print(f"{self.color}Making async decision with o3 model ({mode_desc})...{RESET_COLOR}")
        print(f"{self.color}Scenario: {scenario}{RESET_COLOR}")
        print(f"{self.color}Available actions: {available_actions}{RESET_COLOR}")

        # Make the API call using the Responses API
        if stream:
            response = await async_client.responses.create(
                model=self.model,
                input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                tools=tools,  # type: ignore
                tool_choice="required",
                stream=True,
            )

            # Process streaming response
            tool_call = None

            async for event in response:
                if hasattr(event, "type"):
                    if event.type == "response.output_text.delta":
                        # Handle text deltas (if any)
                        pass
                    elif event.type == "response.function_call_arguments.delta":
                        # Tool arguments are accumulated by the API
                        pass
                    elif event.type == "response.output_item.added":
                        # New tool call started
                        if hasattr(event, "output_item") and event.output_item.type == "function_call":
                            pass  # Tool call tracking handled elsewhere
                    elif event.type == "response.completed":
                        # Process final response
                        if hasattr(event, "response") and hasattr(event.response, "output"):
                            for output_item in event.response.output:
                                if output_item.type == "function_call":
                                    tool_call = output_item
                                    break

            if tool_call:
                args = json.loads(tool_call.arguments)
                chosen_action = args["action"]
                reasoning = args["reasoning"]

                print(f"{self.color}Chosen action: {chosen_action}{RESET_COLOR}")
                print(f"{self.color}Tool reasoning: {reasoning}{RESET_COLOR}")

                return {
                    "action": chosen_action,
                    "reasoning": reasoning,
                    "available_actions": available_actions,
                    "scenario": scenario,
                    "mode": "async_streaming",
                }
        else:
            response = await async_client.responses.create(
                model=self.model,
                input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                tools=tools,  # type: ignore
                tool_choice="required",
            )

            # Process non-streaming response
            tool_call = None
            reasoning_text = ""

            for output_item in response.output:
                if output_item.type == "function_call":
                    tool_call = output_item
                elif output_item.type == "message" and hasattr(output_item, "content"):
                    for content in output_item.content:
                        if hasattr(content, "type"):
                            if content.type == "text" and hasattr(content, "text"):
                                reasoning_text += content.text
                                print(f"{self.color}Reasoning: {content.text}{RESET_COLOR}")
                            elif content.type == "refusal" and hasattr(content, "refusal"):
                                print(f"{self.color}Refusal: {content.refusal}{RESET_COLOR}")

            if tool_call:
                args = json.loads(tool_call.arguments)
                chosen_action = args["action"]
                reasoning = args["reasoning"]

                print(f"{self.color}Chosen action: {chosen_action}{RESET_COLOR}")
                print(f"{self.color}Tool reasoning: {reasoning}{RESET_COLOR}")

                return {
                    "action": chosen_action,
                    "reasoning": reasoning,
                    "full_reasoning": reasoning_text,
                    "available_actions": available_actions,
                    "scenario": scenario,
                    "mode": "async_non_streaming",
                }

        # Fallback
        print(f"{self.color}No tool call found, using fallback{RESET_COLOR}")
        return {
            "action": available_actions[0] if available_actions else "no_action",
            "reasoning": "Fallback: No tool call received",
            "available_actions": available_actions,
            "scenario": scenario,
            "mode": f"async_{mode_desc}_fallback",
        }


async def run_example():
    """Run the example with multiple scenarios in different modes."""

    # Create agents with different colors for different modes
    sync_agent = O3DecisionAgent(model="o3-mini", color=LIGHT_BLUE)

    # Test scenario
    scenario = {
        "scenario": "You're managing a project with limited resources and need to prioritize tasks.",
        "actions": ["focus_on_critical_path", "distribute_resources_evenly", "outsource_some_tasks", "extend_deadline"],
    }

    results = []

    # Test 2: Sync streaming
    print(f"\n{'=' * 60}")
    print(f"{LIGHT_BLUE}Test: Synchronous Streaming{RESET_COLOR}")
    print(f"{'=' * 60}")
    result = sync_agent.make_decision_sync(
        scenario=scenario["scenario"], available_actions=scenario["actions"], stream=True
    )
    results.append(result)

    # Test 3: Sync non-streaming
    print(f"\n{'=' * 60}")
    print(f"{LIGHT_BLUE}Test: Synchronous Non-Streaming{RESET_COLOR}")
    print(f"{'=' * 60}")
    result = sync_agent.make_decision_sync(
        scenario=scenario["scenario"], available_actions=scenario["actions"], stream=False
    )
    results.append(result)

    # Test 4: Async streaming
    print(f"\n{'=' * 60}")
    print(f"{LIGHT_BLUE}Test: Asynchronous Streaming{RESET_COLOR}")
    print(f"{'=' * 60}")
    result = await sync_agent.make_decision_async(
        scenario=scenario["scenario"], available_actions=scenario["actions"], stream=True
    )
    results.append(result)

    # Test 5: Async non-streaming
    print(f"\n{'=' * 60}")
    print(f"{LIGHT_BLUE}Test: Asynchronous Non-Streaming{RESET_COLOR}")
    print(f"{'=' * 60}")
    result = await sync_agent.make_decision_async(
        scenario=scenario["scenario"], available_actions=scenario["actions"], stream=False
    )
    results.append(result)

    return results


def main():
    """Main function to run the example."""
    print("Starting OpenAI o3 Responses API Example (All Modes)")
    print("=" * 60)

    try:
        # Run async example
        results = asyncio.run(run_example())

        print(f"\n{'=' * 60}")
        print("Example Summary")
        print(f"{'=' * 60}")

        for i, result in enumerate(results, 1):
            print(f"Test {i} ({result.get('mode', 'unknown')}): {result['action']}")

        # End the trace
        agentops.end_trace(tracer, end_state="Success")

        # Validate the trace
        print(f"\n{'=' * 60}")
        print("Validating AgentOps Trace")
        print(f"{'=' * 60}")

        try:
            validation_result = agentops.validate_trace_spans(trace_context=tracer)
            agentops.print_validation_summary(validation_result)
            print("✅ Example completed successfully!")
        except agentops.ValidationError as e:
            print(f"❌ Error validating spans: {e}")
            raise

    except Exception as e:
        print(f"❌ Example failed: {e}")
        agentops.end_trace(tracer, end_state="Error")
        raise


if __name__ == "__main__":
    main()
