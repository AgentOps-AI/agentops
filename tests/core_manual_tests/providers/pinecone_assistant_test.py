import agentops
from dotenv import load_dotenv
from pinecone import Pinecone
import os
from pinecone_plugins.assistant.models.chat import Message

load_dotenv()

def test_assistant_operations():
    """Test Pinecone Assistant operations"""
    # Initialize Pinecone and Provider
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    provider = agentops.llms.PineconeProvider(pc)
    
    try:
        # List existing assistants
        print("\nListing assistants...")
        assistants = provider.list_assistants(pc)
        print(f"Current assistants: {assistants}")
        
        # Create a new assistant
        print("\nCreating assistant...")
        assistant = provider.create_assistant(
            pc,
            assistant_name="test-assistant",
            instructions="You are a helpful assistant for testing purposes."
        )
        print(f"Created assistant: {assistant}")
        
        # Check assistant status
        print("\nChecking assistant status...")
        status = provider.get_assistant(pc, "test-assistant")
        print(f"Assistant status: {status}")
        
        # Update assistant
        print("\nUpdating assistant...")
        updated = provider.update_assistant(
            pc,
            assistant_name="test-assistant",
            instructions="Updated instructions for testing."
        )
        print(f"Updated assistant: {updated}")
        
        # Upload file
        print("\nUploading file...")
        with open("test_data.txt", "w") as f:
            f.write("This is test data for the assistant.")
        
        file_upload = provider.upload_file(
            pc,
            assistant_name="test-assistant",
            file_path="test_data.txt"
        )
        print(f"File upload: {file_upload}")
        
        # Describe uploaded file
        print("\nDescribing uploaded file...")
        file_description = provider.describe_file(
            pc,
            assistant_name="test-assistant",
            file_id=file_upload["id"]  # Now this should work since file_upload is a dict
        )
        print(f"File description: {file_description}")
        
        # Test chat with OpenAI-compatible interface
        print("\nTesting chat completions...")
        chat_completion = provider.chat_completions(
            pc,
            assistant_name="test-assistant",
            messages=[{"content": "What information can you find in the uploaded file?"}]
        )
        print(f"Chat completion response: {chat_completion}")
        
        # Delete uploaded file
        print("\nDeleting uploaded file...")
        delete_response = provider.delete_file(
            pc,
            assistant_name="test-assistant",
            file_id=file_upload["id"]
        )
        print(f"File deletion response: {delete_response}")
        
        # Clean up
        print("\nCleaning up...")
        # Delete assistant
        provider.delete_assistant(pc, "test-assistant")
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