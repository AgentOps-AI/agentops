import ollama
from agentops import Client
import asyncio

# Initialize the AgentOps client with your API key
client = Client(api_key="203ba1f9-da1b-4861-b058-e7107e87c35a")

# Start a session
session_id = client.start_session(tags=["ollama_test"])

try:
    # Synchronous chat call to Ollama API
    sync_response = ollama.chat(
        model='orca-mini',
        messages=[{'role': 'user', 'content': 'Why is the sky blue?'}]
    )
    print("Sync Response:", sync_response)

    # Asynchronous chat call to Ollama API using asyncio.to_thread to run the sync method
    async def async_chat():
        response = await asyncio.to_thread(ollama.chat,
                                           model="orca-mini",
                                           messages=[{"role": "user", "content": "Why is the sky blue?"}])
        return response

    async def main():
        async_response = await async_chat()
        print("Async Response:", async_response)

    asyncio.run(main())

    # End the session successfully
    client.end_session("Success")

except Exception as e:
    # End the session with failure if there is an exception
    client.end_session("Fail", str(e))
    raise
