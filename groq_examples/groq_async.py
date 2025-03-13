#!/usr/bin/env python3
"""
Groq API - Asynchronous Example

This script demonstrates how to use the Groq API in an asynchronous manner with AgentOps integration.
It shows how to:
1. Initialize the Groq async client
2. Send multiple completion requests concurrently
3. Process the responses as they complete
4. Track the interactions with AgentOps
"""

import os
import asyncio
from dotenv import load_dotenv
from groq.asyncio import AsyncGroq
import agentops

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or "<your_groq_api_key>"
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") or "<your_agentops_key>"

# Initialize AgentOps
agentops.init(api_key=AGENTOPS_API_KEY, default_tags=["groq-async-example"])
print("AgentOps initialized. Your Groq API interactions will be tracked.")

# Initialize Groq async client
client = AsyncGroq(api_key=GROQ_API_KEY)

async def generate_completion(prompt, system_message, model="llama3-8b-8192"):
    """
    Generate a completion using the Groq API asynchronously.
    
    Args:
        prompt: The user prompt to send to the model
        system_message: The system message to set the context
        model: The model to use for generation
        
    Returns:
        The generated text and token usage
    """
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=150
    )
    
    return {
        "text": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }

async def main():
    """
    Main function to demonstrate asynchronous Groq API usage.
    """
    # Define multiple prompts to process concurrently
    tasks = [
        generate_completion(
            "Write a short poem about artificial intelligence and creativity.",
            "You are a creative assistant that writes concise, thoughtful content."
        ),
        generate_completion(
            "Explain quantum computing in simple terms, in just 2-3 sentences.",
            "You are a science educator who explains complex topics simply."
        ),
        generate_completion(
            "Give me a quick recipe for a healthy breakfast smoothie.",
            "You are a nutrition expert who provides healthy recipes."
        )
    ]
    
    print("\nSending multiple requests to Groq API concurrently...\n")
    
    # Process all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Display the results
    for i, result in enumerate(results):
        print("-" * 50)
        print(f"Response {i+1}:")
        print("-" * 50)
        print(result["text"])
        print("-" * 50)
        print(f"Token Usage: Prompt={result['usage']['prompt_tokens']}, " 
              f"Completion={result['usage']['completion_tokens']}, "
              f"Total={result['usage']['total_tokens']}")
        print()
    
    # Close the client session
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
    print("\nCheck your AgentOps dashboard to see the tracked interactions!") 