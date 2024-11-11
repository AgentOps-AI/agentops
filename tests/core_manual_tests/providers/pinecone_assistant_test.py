import agentops
from dotenv import load_dotenv
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message
import time
import tempfile
import os

# Load environment variables
load_dotenv()

def test_assistant_operations():
    """Test Pinecone Assistant operations using in-memory or temporary file handling"""
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
        
        # Create in-memory file-like object with test data
        test_data_content = """
            This is a test document containing specific information.
            The document discusses important facts:
            1. The sky is blue
            2. Water boils at 100 degrees Celsius
            3. The Earth orbits around the Sun
            
            This information should be retrievable by the assistant.
            """
        
        # Create a proper temporary file with content
        temp_dir = tempfile.mkdtemp()  # Create a temporary directory
        file_path = os.path.join(temp_dir, 'test_document.txt')  # Create a path with explicit filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(test_data_content)

        # Upload file using the explicit file path
        print("\nUploading file...")
        file_upload = provider.upload_file(
            pc,
            assistant_name="test-assistant",
            file_path=file_path
        )
        print(f"File upload: {file_upload}")
        
        # Wait for file processing (check status until ready)
        print("\nWaiting for file processing...")
        max_retries = 10
        for _ in range(max_retries):
            file_status = provider.describe_file(
                pc,
                assistant_name="test-assistant",
                file_id=file_upload["id"]
            )
            if file_status.get("status") == "Available":
                break
            print("File still processing, waiting...")
            time.sleep(2)
        
        # Test chat with OpenAI-compatible interface
        print("\nTesting chat completions...")
        chat_completion = provider.chat_completions(
            pc,
            assistant_name="test-assistant",
            messages=[
                {"role": "user", "content": "What facts are mentioned in the uploaded file about nature and science?"}
            ]
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
        os.remove(file_path)  # Remove the temporary file
        os.rmdir(temp_dir)    # Remove the temporary directory
        # Delete assistant
        provider.delete_assistant(pc, "test-assistant")
        print("Assistant deleted")

    except Exception as e:
        print(f"Error during testing: {e}")
        agentops.end_session(end_state="Fail")
        return
    
    agentops.end_session(end_state="Success")
    print("\nAssistant tests completed successfully!")

if __name__ == "__main__":
    agentops.init(default_tags=["pinecone-assistant-test"])
    test_assistant_operations()
