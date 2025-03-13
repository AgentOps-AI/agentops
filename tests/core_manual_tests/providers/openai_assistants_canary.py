import agentops
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
agentops.init(default_tags=["openai-assistants-test"])
openai = OpenAI()

try:
    # Basic Assistant Creation
    assistant = openai.beta.assistants.create(
        name="Math Tutor",
        instructions="You are a personal math tutor. Write and run code to answer math questions.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4o-mini",
    )
    print(f"\nCreated assistant: {assistant.id}")
    print(f"Assistant name: {assistant.name}")
    print(f"Assistant instructions: {assistant.instructions}")
    print(f"Assistant model: {assistant.model}")
    print(f"Assistant tools: {assistant.tools}")

    # Thread Creation and Message Handling
    thread = openai.beta.threads.create()
    print(f"\nCreated thread: {thread.id}")

    # Add Multiple Messages
    message1 = openai.beta.threads.messages.create(
        thread_id=thread.id, role="user", content="I need to solve the equation `3x + 11 = 14`. Can you help me?"
    )
    message2 = openai.beta.threads.messages.create(
        thread_id=thread.id, role="user", content="Also, what is the square root of 144?"
    )
    print("\nAdded messages:")
    print(f"Message 1 ID: {message1.id}")
    print(f"Message 1 content: {message1.content[0].text.value}")
    print(f"Message 2 ID: {message2.id}")
    print(f"Message 2 content: {message2.content[0].text.value}")

    # Run Assistant with Multiple Questions
    run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
    print(f"\nStarted run: {run.id}")

    # Run Status Monitoring
    while run.status not in ["completed", "failed"]:
        run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")

    if run.status == "failed":
        print("\nRun failed!")
        if run.last_error:
            print(f"Error code: {run.last_error.code}")
            print(f"Error message: {run.last_error.message}")

    # Message Retrieval and Display
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    print("\nThread Messages:")
    for msg in reversed(messages.data):
        print(f"{msg.role.capitalize()}: {msg.content[0].text.value}")

    # Assistant Update
    updated_assistant = openai.beta.assistants.update(
        assistant.id,
        name="Advanced Math Tutor",
        instructions="You are an advanced math tutor. Explain concepts in detail.",
    )
    print(f"\nUpdated assistant: {updated_assistant.id}")
    print(f"New name: {updated_assistant.name}")
    print(f"New instructions: {updated_assistant.instructions}")

    # Run Step Retrieval
    run_steps = openai.beta.threads.runs.steps.list(thread_id=thread.id, run_id=run.id)
    print("\nRun Steps:")
    for step in run_steps.data:
        print(f"Step ID: {step.id}")
        print(f"Status: {step.status}")
        if hasattr(step.step_details, "message_creation"):
            print(f"Message ID: {step.step_details.message_creation.message_id}")

    # Thread Update
    updated_thread = openai.beta.threads.update(thread.id, metadata={"test": "value"})
    print(f"\nUpdated thread: {updated_thread.id}")

    # Message Retrieval and Display
    messages = openai.beta.threads.messages.list(thread_id=updated_thread.id)
    print("\nThread Messages:")
    for msg in reversed(messages.data):
        print(f"{msg.role.capitalize()}: {msg.content[0].text.value}")

finally:
    # Clean up
    if "assistant" in locals():
        openai.beta.assistants.delete(assistant.id)
        print(f"\nDeleted assistant: {assistant.id}")

agentops.end_session(end_state="Success")
