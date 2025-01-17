import google.generativeai as genai
import agentops
from agentops.llms.providers.gemini import GeminiProvider

# Configure the API key
genai.configure(api_key="AIzaSyCRrIbBqHnL4t1_Qrk88P1k3-jo-_N2YGk")

# Initialize AgentOps and model
ao_client = agentops.init()
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize and override Gemini provider
provider = GeminiProvider(model)
provider.override()

try:
    # Test synchronous generation
    print("\nTesting synchronous generation:")
    response = model.generate_content("What is artificial intelligence?", session=ao_client)
    print(response.text)
    print("\nResponse metadata:", response.prompt_feedback)
    
    # Test streaming generation
    print("\nTesting streaming generation:")
    response = model.generate_content("Explain quantum computing", stream=True, session=ao_client)
    for chunk in response:
        print(chunk.text, end="")
    
    # End session and check stats
    agentops.end_session(end_state="Success", end_state_reason="Gemini integration test completed successfully")

finally:
    # Clean up
    provider.undo_override()
