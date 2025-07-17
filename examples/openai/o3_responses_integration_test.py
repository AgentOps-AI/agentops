# OpenAI o3 Responses API Integration Test
#
# This example demonstrates AgentOps integration with OpenAI's o3 reasoning model
# through the Responses API. The o3 model excels at complex problem solving and
# multi-step reasoning with tool calls.
#
# This test creates a simple decision-making agent that uses the o3 model to
# make choices based on available options, similar to the Pokémon battle example
# but simplified for testing purposes.

import openai
import agentops
import json
import os
from dotenv import load_dotenv
from agentops.sdk.decorators import agent
from typing import List, Dict, Any

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Initialize AgentOps
agentops.init(trace_name="o3-responses-test", tags=["o3", "responses-api", "integration-test"])
tracer = agentops.start_trace(
    trace_name="o3 Responses API Integration Test", 
    tags=["o3", "responses-api", "integration-test"]
)

# Initialize OpenAI client
client = openai.OpenAI()

# ANSI escape codes for colors
LIGHT_BLUE = "\033[94m"
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
    
    def __init__(self, model: str = "o3"):
        self.model = model
        self.color = LIGHT_BLUE
    
    def make_decision(self, scenario: str, available_actions: List[str]) -> Dict[str, Any]:
        """
        Make a decision using the o3 model with tool calls.
        
        Args:
            scenario: Description of the current situation
            available_actions: List of possible actions to choose from
            
        Returns:
            Dictionary containing the chosen action and reasoning
        """
        
        # Define the tool for action selection
        tools = [{
            "type": "function",
            "name": "select_action",
            "description": "Select the best action from the available options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The selected action from the available options"
                    },
                    "reasoning": {
                        "type": "string", 
                        "description": "Detailed reasoning for why this action was chosen"
                    }
                },
                "required": ["action", "reasoning"],
                "additionalProperties": False
            }
        }]
        
        # Create the prompt
        system_prompt = create_decision_prompt(scenario, available_actions)
        user_message = f"Select the best action from these options: {available_actions}. Provide your reasoning and make your choice."
        
        print(f"{self.color}Making decision with o3 model...{RESET_COLOR}")
        print(f"{self.color}Scenario: {scenario}{RESET_COLOR}")
        print(f"{self.color}Available actions: {available_actions}{RESET_COLOR}")
        
        # Make the API call using the Responses API
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            tools=tools,
            tool_choice="required"
        )
        
        # Process the response
        tool_call = None
        reasoning_text = ""
        
        for output_item in response.output:
            if output_item.type == 'function_call':
                tool_call = output_item
            elif output_item.type == 'message' and hasattr(output_item, 'content'):
                for content in output_item.content:
                    if hasattr(content, 'text'):
                        reasoning_text += content.text
                        print(f"{self.color}Reasoning: {content.text}{RESET_COLOR}")
        
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
                "scenario": scenario
            }
        else:
            print(f"{self.color}No tool call found, using fallback{RESET_COLOR}")
            return {
                "action": available_actions[0] if available_actions else "no_action",
                "reasoning": "Fallback: No tool call received",
                "full_reasoning": reasoning_text,
                "available_actions": available_actions,
                "scenario": scenario
            }

def run_integration_test():
    """Run the integration test with multiple scenarios."""
    
    # Create the agent
    agent = O3DecisionAgent(model="o3")
    
    # Test scenarios
    test_scenarios = [
        {
            "scenario": "You're in a battle and your opponent has a strong defensive position. You need to choose your next move carefully.",
            "actions": ["attack_aggressively", "defend_and_wait", "use_special_ability", "retreat_temporarily"]
        },
        {
            "scenario": "You're managing a project with limited resources and need to prioritize tasks.",
            "actions": ["focus_on_critical_path", "distribute_resources_evenly", "outsource_some_tasks", "extend_deadline"]
        },
        {
            "scenario": "You're playing a strategy game and need to choose your next move based on the current board state.",
            "actions": ["expand_territory", "consolidate_position", "attack_opponent", "build_defenses"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}")
        print(f"{'='*60}")
        
        result = agent.make_decision(
            scenario=test_case["scenario"],
            available_actions=test_case["actions"]
        )
        results.append(result)
        
        print(f"\nResult: {result['action']}")
        print(f"Reasoning: {result['reasoning']}")
    
    return results

def main():
    """Main function to run the integration test."""
    print("Starting OpenAI o3 Responses API Integration Test")
    print("=" * 60)
    
    try:
        results = run_integration_test()
        
        print(f"\n{'='*60}")
        print("Integration Test Summary")
        print(f"{'='*60}")
        
        for i, result in enumerate(results, 1):
            print(f"Test {i}: {result['action']}")
        
        # End the trace
        agentops.end_trace(tracer, end_state="Success")
        
        # Validate the trace
        print(f"\n{'='*60}")
        print("Validating AgentOps Trace")
        print(f"{'='*60}")
        
        try:
            validation_result = agentops.validate_trace_spans(trace_context=tracer)
            agentops.print_validation_summary(validation_result)
            print("✅ Integration test completed successfully!")
        except agentops.ValidationError as e:
            print(f"❌ Error validating spans: {e}")
            raise
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        agentops.end_trace(tracer, end_state="Error")
        raise

if __name__ == "__main__":
    main()