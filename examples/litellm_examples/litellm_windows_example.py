"""
Example of using LiteLLM with AgentOps on Windows.
This example works without uvloop which is not supported on Windows.
"""
import os
import litellm
import agentops
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    litellm.callbacks = ["otel"]
    
    # Get API keys from environment variables or set them directly
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "<your_openai_key>"
    AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"
    
    # Initialize AgentOps
    agentops.init(AGENTOPS_API_KEY, default_tags=["litellm-windows-example"])
    
    # Example LiteLLM completion
    messages = [{"role": "user", "content": "Write a 12 word poem about secret agents."}]
    response = litellm.completion(
        model="gpt-4", 
        messages=messages
    )
    
    # Print the response
    print(response.choices[0].message.content)
    
    # End the AgentOps session
    agentops.end_session("Success")

if __name__ == "__main__":
    main() 