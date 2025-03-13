import agentops
from agentops.sdk.decorators import session

# Initialize AgentOps
agentops.init()


# Example 1: Using the session decorator with a function
@session
def process_data(data):
    """Process some data within a session."""
    print(f"Processing data: {data}")
    import openai

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Write a one-line joke"}]
    )

    # Simulate some processing
    result = data.upper()
    return result


# Call the decorated function
result = process_data("hello world")
print(f"Result: {result}")
