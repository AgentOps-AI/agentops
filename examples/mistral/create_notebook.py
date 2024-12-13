import nbformat as nbf
import asyncio

nb = nbf.v4.new_notebook()

# Create cells
cells = []

# Add markdown cells
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """# Monitoring Mistral with AgentOps

This notebook demonstrates how to monitor and analyze Mistral model runs using AgentOps. We'll cover:
- Basic model completions with monitoring
- Streaming responses and real-time tracking
- Async operations and parallel requests
- Error handling and debugging
- Cost tracking and optimization
- Session replay and analysis

Here's an example of monitoring Mistral model runs with AgentOps:

![Mistral Session Monitoring](img/mistral_session.png)

## Prerequisites

Before running this notebook, make sure you have:
1. An AgentOps API key (get one at [app.agentops.ai](https://app.agentops.ai))
2. A Mistral API key (get one at [console.mistral.ai](https://console.mistral.ai))

## Setup

First, let's install the required packages:"""
        ),
    ]
)

# Add setup cells
cells.extend(
    [
        nbf.v4.new_code_cell("""%pip install -U mistralai agentops python-dotenv"""),
        nbf.v4.new_markdown_cell("Import dependencies and initialize clients:"),
        nbf.v4.new_code_cell(
            """import asyncio
import os
from dotenv import load_dotenv
from mistralai import Mistral
import agentops

# Load environment variables
load_dotenv()

# Function to validate API keys
def validate_api_keys():
    mistral_key = os.getenv("MISTRAL_API_KEY")
    agentops_key = os.getenv("AGENTOPS_API_KEY")

    if not mistral_key or not agentops_key:
        print("Warning: Missing API keys. Please set MISTRAL_API_KEY and AGENTOPS_API_KEY in your .env file")
        print("Using placeholder responses for demonstration purposes.")
        return False
    return True

# Initialize clients with validation
has_valid_keys = validate_api_keys()

try:
    if has_valid_keys:
        agentops.init(os.getenv("AGENTOPS_API_KEY"))
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        print("Successfully initialized AgentOps and Mistral clients")
    else:
        print("Running in demonstration mode with placeholder responses")
except Exception as e:
    print(f"Error initializing clients: {str(e)}")
    has_valid_keys = False"""
        ),
    ]
)

# Add basic completion section with error handling
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """## Basic Completion with Monitoring

Let's create a simple function that gets completions from Mistral and is monitored by AgentOps:"""
        ),
        nbf.v4.new_code_cell(
            '''@agentops.track_agent(name='mistral-agent')
def get_completion(prompt):
    """Get a completion from Mistral with monitoring."""
    if not has_valid_keys:
        return "This is a placeholder response. Please set valid API keys to get actual completions."

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting completion: {str(e)}")
        return f"Error: {str(e)}"

# Example usage
response = get_completion("Explain quantum computing in simple terms")
print(response)'''
        ),
    ]
)

# Add streaming section with error handling
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """## Streaming Responses

For longer responses, you might want to use streaming to get tokens as they're generated:"""
        ),
        nbf.v4.new_code_cell(
            '''@agentops.track_agent(name='mistral-stream-agent')
def get_streaming_completion(prompt):
    """Get a streaming completion from Mistral with monitoring."""
    if not has_valid_keys:
        print("This is a placeholder streaming response. Please set valid API keys.")
        return "Placeholder streaming response"

    try:
        response = client.chat.stream(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )

        result = ""
        for chunk in response:
            if chunk.data.choices[0].finish_reason == "stop":
                return result
            result += chunk.data.choices[0].delta.content
            print(chunk.data.choices[0].delta.content, end="")
        return result
    except Exception as e:
        print(f"Error in streaming: {str(e)}")
        return f"Error: {str(e)}"

# Example usage
response = get_streaming_completion("What is machine learning?")'''
        ),
    ]
)

# Add async section with proper async handling
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """## Async Operations

For better performance in async applications:"""
        ),
        nbf.v4.new_code_cell(
            '''@agentops.track_agent(name='mistral-async-agent')
async def get_async_completion(prompt):
    """Get an async completion from Mistral with monitoring."""
    if not has_valid_keys:
        return "This is a placeholder async response. Please set valid API keys."

    try:
        response = await client.chat.complete_async(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in async completion: {str(e)}")
        return f"Error: {str(e)}"

# Example usage with proper async handling
async def run_main():
    response = await get_async_completion("What are the benefits of async programming?")
    print(response)

# Use asyncio.run to properly handle async code
if __name__ == "__main__":
    asyncio.run(run_main())'''
        ),
    ]
)

# Add error handling section
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """## Error Handling and Debugging

AgentOps provides comprehensive error tracking and debugging capabilities. Let's explore how to handle common scenarios:

![Session Overview](img/session-overview.png)"""
        ),
        nbf.v4.new_code_cell(
            '''@agentops.track_agent(name="mistral-error-handler")
def handle_model_errors(prompt, max_retries=3):
    """Demonstrate error handling with AgentOps monitoring."""
    for attempt in range(max_retries):
        try:
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise

# Example usage with error scenarios
try:
    # Test with invalid model to trigger error
    response = handle_model_errors("Test prompt", model="invalid-model")
except Exception as e:
    print(f"Error caught and tracked: {str(e)}")'''
        ),
    ]
)

# Add cost tracking section
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """## Cost Tracking and Optimization

AgentOps automatically tracks token usage and costs across all your Mistral API calls. This helps you:
- Monitor spending patterns
- Optimize prompt lengths
- Track costs across different models
- Identify cost-saving opportunities

![Cost Analysis](img/session-waterfall.png)"""
        ),
        nbf.v4.new_code_cell(
            '''@agentops.track_agent(name="mistral-cost-tracker")
def analyze_costs(prompts):
    """Analyze token usage and costs across different prompts."""
    results = []
    for prompt in prompts:
        try:
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            results.append(response.choices[0].message.content)
        except Exception as e:
            print(f"Error: {str(e)}")
            results.append(None)
    return results

# Test with different prompt lengths
test_prompts = [
    "What is AI?",  # Short prompt
    "Explain machine learning concepts.",  # Medium prompt
    "Write a detailed essay about artificial intelligence, its history, current applications, and future potential."  # Long prompt
]

print("Analyzing costs across different prompt lengths...")
responses = analyze_costs(test_prompts)

for i, (prompt, response) in enumerate(zip(test_prompts, responses)):
    print(f"\\nPrompt {i+1} ({len(prompt)} chars):")
    print(f"Response: {response[:100]}..." if response else "Error")'''
        ),
    ]
)

# Add session replay section
cells.extend(
    [
        nbf.v4.new_markdown_cell(
            """## Session Replay and Analysis

AgentOps provides powerful session replay capabilities to analyze model behavior over time:
- Track response patterns
- Monitor performance metrics
- Identify optimization opportunities
- Debug complex interactions

Let's create a comprehensive analysis session:"""
        ),
        nbf.v4.new_code_cell(
            '''# Start a new analysis session
agentops.init(os.getenv("AGENTOPS_API_KEY"), session_name="mistral-analysis")

@agentops.track_agent(name="mistral-analyzer")
def comprehensive_analysis():
    """Run a comprehensive analysis of Mistral model behavior."""
    try:
        # Test different scenarios
        prompts = [
            "What is AI?",  # Short prompt
            "Explain the concept of machine learning.",  # Medium prompt
            "Write a detailed analysis of artificial intelligence.",  # Long prompt
        ]

        results = []
        for prompt in prompts:
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            results.append(response.choices[0].message.content)

        # Analyze results
        for i, (prompt, result) in enumerate(zip(prompts, results)):
            print(f"Analysis {i+1}:")
            print(f"Prompt length: {len(prompt)} chars")
            print(f"Response length: {len(result)} chars")

        return "Analysis completed successfully"
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return str(e)

# Run the analysis
result = comprehensive_analysis()
print(f"Analysis result: {result}")

# End the session with status
agentops.end_session("Analysis completed")'''
        ),
    ]
)

nb.cells = cells

# Write the notebook
with open("monitoring_mistral.ipynb", "w") as f:
    nbf.write(nb, f)
