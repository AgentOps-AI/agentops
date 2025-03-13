#!/usr/bin/env python3
"""
Groq API - Synchronous Example

This script demonstrates how to use the Groq API in a synchronous manner with AgentOps integration.
It shows how to:
1. Initialize the Groq client
2. Send a completion request
3. Process the response
4. Track the interaction with AgentOps
"""

import os
from dotenv import load_dotenv
from groq import Groq
import agentops

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or "<your_groq_api_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"

# Initialize AgentOps
agentops.init(api_key=AGENTOPS_API_KEY, default_tags=["groq-sync-example"])
print("AgentOps initialized. Your Groq API interactions will be tracked.")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

def main():
    """
    Main function to demonstrate synchronous Groq API usage.
    """
    # Define the prompt
    prompt = """
    Write a short poem about artificial intelligence and creativity.
    Make it thoughtful but concise, no more than 4 lines.
    """
    
    print("\nSending request to Groq API...\n")
    
    # Make a synchronous completion request
    response = client.chat.completions.create(
        model="llama3-8b-8192",  # You can also use "llama3-70b-8192" or other available models
        messages=[
            {"role": "system", "content": "You are a creative assistant that writes concise, thoughtful content."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=100
    )
    
    # Process and display the response
    assistant_message = response.choices[0].message.content
    
    print("-" * 50)
    print("Response from Groq API:")
    print("-" * 50)
    print(assistant_message)
    print("-" * 50)
    
    # Display token usage information
    print("\nToken Usage:")
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")

if __name__ == "__main__":
    main()
    print("\nCheck your AgentOps dashboard to see the tracked interaction!") 