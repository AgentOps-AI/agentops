import agentops
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
agentops.init(default_tags=["openai-assistants-test"])
openai = OpenAI()

try:
    # Create an assistant
    assistant = openai.beta.assistants.create(
        name="Math Tutor",
        instructions="You are a personal math tutor. Write and run code to answer math questions.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4o-mini",
    )
    print(f"Created assistant: {assistant.id}")

    # Create a thread
    thread = openai.beta.threads.create()
    print(f"Created thread: {thread.id}")

    # Add a message to the thread
    message = openai.beta.threads.messages.create(
        thread_id=thread.id, role="user", content="I need to solve the equation `3x + 11 = 14`. Can you help me?"
    )
    print(f"Added message: {message.id}")

    # Run the assistant
    run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
    print(f"Started run: {run.id}")

    # Wait for the run to complete
    while run.status not in ["completed", "failed"]:
        run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")

    if run.status == "failed":
        print("\nRun failed!")
        if run.last_error:
            print(f"Error code: {run.last_error.code}")
            print(f"Error message: {run.last_error.message}")

    # Retrieve messages and print in reverse order (most recent first)
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    print("\nThread Messages:")
    for msg in reversed(messages.data):
        print(f"{msg.role.capitalize()}: {msg.content[0].text.value}")
    print()

finally:
    # Clean up
    if "assistant" in locals():
        openai.beta.assistants.delete(assistant.id)
        print(f"Deleted assistant: {assistant.id}")

agentops.end_session(end_state="Success")
