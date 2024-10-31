import os
import sys
from dotenv import load_dotenv
import openai
import litellm
import logging

# Add the project root to Python path to use local agentops
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import agentops

# Load environment variables
load_dotenv()

# Enable debug logging
agentops.logger.setLevel(logging.DEBUG)

def test_openai_only():
    print("\n=== Testing OpenAI with local AgentOps changes ===")
    
    # Initialize AgentOps
    agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))
    
    # Set API keys
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    try:
        # Make OpenAI calls
        for i in range(3):
            print(f"\nOpenAI Call {i+1}:")
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user", 
                    "content": f"Say 'OpenAI Test {i+1} successful when LiteLLM is imported'"
                }]
            )
            print(f"Response {i+1}:", response.choices[0].message.content)
            
    except Exception as e:
        print("\nError occurred:", str(e))
        raise e
    finally:
        agentops.end_session("Success")

if __name__ == "__main__":
    test_openai_only()
