"""Example usage of OpenAI Assistants API integration."""

from agentops import Session
from agentops.integrations.openai_assistants import AssistantAgent


def main():
    # Create session
    session = Session()

    # Initialize assistant
    agent = AssistantAgent(
        assistant_id="YOUR_ASSISTANT_ID",  # Replace with actual assistant ID
        session=session,
    )

    # Create thread
    thread_id = agent.create_thread()

    # Add message
    agent.add_message(thread_id=thread_id, content="What is 2+2? Please use the code interpreter.")

    # Run assistant
    result = agent.run(thread_id)

    # Print messages
    for msg in result["messages"]:
        print(f"{msg.role}: {msg.content[0].text.value}")

    # End session
    session.end_session()


if __name__ == "__main__":
    main()
