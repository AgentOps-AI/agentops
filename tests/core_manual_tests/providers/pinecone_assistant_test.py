import agentops
from dotenv import load_dotenv
from pinecone import Pinecone
import os
import time

load_dotenv()

def test_assistant_operations():
    """Test Pinecone Assistant operations"""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    try:
        # List existing assistants
        print("\nListing assistants...")
        assistants = pc.list_assistants()
        print(f"Current assistants: {assistants}")
        
        # Create a new assistant
        print("\nCreating assistant...")
        assistant = pc.create_assistant(
            name="test-assistant",
            instructions="You are a helpful assistant for testing purposes.",
            model="gpt-4"
        )
        print(f"Created assistant: {assistant}")
        
        # Check assistant status
        status = pc.check_assistant_status(assistant.id)
        print(f"Assistant status: {status}")
        
        # Update assistant
        print("\nUpdating assistant...")
        updated = pc.update_assistant(
            assistant_id=assistant.id,
            instructions="Updated instructions for testing."
        )
        print(f"Updated assistant: {updated}")
        
        # Upload file
        print("\nUploading file...")
        with open("test_data.txt", "w") as f:
            f.write("This is test data for the assistant.")
        
        file_upload = pc.upload_file(
            assistant_id=assistant.id,
            file_path="test_data.txt"
        )
        print(f"File upload: {file_upload}")
        
        # Describe file
        file_info = pc.describe_file(
            assistant_id=assistant.id,
            file_id=file_upload.id
        )
        print(f"File info: {file_info}")
        
        # Test chat
        print("\nTesting chat...")
        chat_response = pc.chat(
            assistant_id=assistant.id,
            messages=[{"role": "user", "content": "Hello, can you help me with testing?"}]
        )
        print(f"Chat response: {chat_response}")
        
        # Test OpenAI-compatible chat
        print("\nTesting OpenAI-compatible chat...")
        openai_response = pc.chat_openai(
            assistant_id=assistant.id,
            messages=[{"role": "user", "content": "Hello using OpenAI format"}]
        )
        print(f"OpenAI-compatible response: {openai_response}")
        
        # Test evaluation
        print("\nTesting evaluation...")
        eval_response = pc.evaluate(
            assistant_id=assistant.id,
            question="What is 2+2?",
            answer="4",
            context="Basic arithmetic testing."
        )
        print(f"Evaluation response: {eval_response}")
        
        # Clean up
        print("\nCleaning up...")
        # Delete file
        pc.delete_file(
            assistant_id=assistant.id,
            file_id=file_upload.id
        )
        print("File deleted")
        
        # Delete assistant
        pc.delete_assistant(assistant.id)
        print("Assistant deleted")
        
        os.remove("test_data.txt")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        agentops.end_session(end_state="Fail")
        return
    
    agentops.end_session(end_state="Success")
    print("\nAssistant tests completed successfully!")

if __name__ == "__main__":
    agentops.init(default_tags=["pinecone-assistant-test"])
    test_assistant_operations() 