import asyncio
import agentops
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import numpy as np
import os
import time
from agentops.event import ActionEvent
import json

load_dotenv()

def test_vector_operations(index, dimension):
    """Test basic vector operations"""
    print("\n=== Testing Vector Operations ===")
    
    # Generate test vectors - use the same base vector for similarity
    base_vector = np.random.rand(dimension)
    vectors = []
    for i in range(5):
        # Add small random noise to base vector to ensure similarity
        vector = (base_vector + np.random.normal(0, 0.1, dimension)).tolist()
        vectors.append((f"id{i}", vector, {"metadata": f"test{i}"}))
    
    # Test upsert
    print("\nTesting upsert...")
    agentops.record(ActionEvent(
        action_type="vector_upsert",
        params={"vector_count": len(vectors), "namespace": "test-namespace"}
    ))
    upsert_response = index.upsert(
        vectors=[(str(i), v[1], v[2]) for i, v in enumerate(vectors)],  # Convert IDs to strings
        namespace="test-namespace"
    )
    print(f"Upsert response: {upsert_response}")
    
    # Add small delay to ensure upsert is complete
    time.sleep(1)
    
    # Use base vector for query to ensure matches
    print("\nTesting query...")
    agentops.record(ActionEvent(
        action_type="vector_query",
        params={"top_k": 2, "namespace": "test-namespace"}
    ))
    query_response = index.query(
        vector=base_vector.tolist(),
        top_k=2,
        namespace="test-namespace",
        include_metadata=True
    )
    print(f"Query response: {query_response}")
    
    # Test fetch
    print("\nTesting fetch...")
    agentops.record(ActionEvent(
        action_type="vector_fetch",
        params={"ids": ["0", "1"], "namespace": "test-namespace"}
    ))
    fetch_response = index.fetch(
        ids=["0", "1"],
        namespace="test-namespace"
    )
    print(f"Fetch response: {fetch_response}")
    
    # Test update
    print("\nTesting update...")
    agentops.record(ActionEvent(
        action_type="vector_update",
        params={"id": "0", "namespace": "test-namespace"}
    ))
    update_response = index.update(
        id="0",
        values=np.random.rand(dimension).tolist(),
        namespace="test-namespace",
        set_metadata={"updated": True}
    )
    print(f"Update response: {update_response}")
    
    # Test delete
    print("\nTesting delete...")
    agentops.record(ActionEvent(
        action_type="vector_delete",
        params={"ids": ["0"], "namespace": "test-namespace"}
    ))
    delete_response = index.delete(
        ids=["0"],
        namespace="test-namespace"
    )
    print(f"Delete response: {delete_response}")

def test_assistant_operations(pc):
    """Test Pinecone assistant operations if available"""
    print("\n=== Testing Assistant Operations ===")
    try:
        # Create assistant
        print("\nTesting create assistant...")
        agentops.record(ActionEvent(
            action_type="create_assistant",
            params={"name": "test-assistant"}
        ))
        assistant = pc.create_assistant(
            name="test-assistant",
            instructions="This is a test assistant",
            model="gpt-4"
        )
        print(f"Assistant created: {assistant}")

        # Chat with assistant
        print("\nTesting chat with assistant...")
        agentops.record(ActionEvent(
            action_type="chat_assistant",
            params={"assistant_name": "test-assistant"}
        ))
        chat_response = assistant.chat(
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(f"Chat response: {chat_response}")

        # Delete assistant
        print("\nDeleting assistant...")
        agentops.record(ActionEvent(
            action_type="delete_assistant",
            params={"assistant_name": "test-assistant"}
        ))
        pc.delete_assistant(assistant.id)
        print("Assistant deleted")

    except Exception as e:
        print(f"Assistant operations not available: {e}")

def main():
    # Initialize AgentOps
    agentops.init(default_tags=["pinecone-comprehensive-test"])
    
    # Initialize Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Test parameters
    dimension = 8
    index_name = "test-index-comprehensive"
    
    try:
        # Test index operations
        print("\n=== Testing Index Operations ===")
        
        # List indexes
        print("\nListing indexes...")
        agentops.record(ActionEvent(
            action_type="list_indexes"
        ))
        indexes = pc.list_indexes()
        print(f"Current indexes: {indexes}")
        
        # Create index if it doesn't exist
        if index_name not in indexes:
            print(f"\nCreating index {index_name}...")
            agentops.record(ActionEvent(
                action_type="create_index",
                params={
                    "name": index_name,
                    "dimension": dimension,
                    "metric": "cosine"
                }
            ))
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            
            # Wait for index to be ready
            while not pc.describe_index(index_name).status['ready']:
                time.sleep(1)
        
        # Describe index
        print("\nDescribing index...")
        agentops.record(ActionEvent(
            action_type="describe_index",
            params={"name": index_name}
        ))
        index_description = pc.describe_index(index_name)
        print(f"Index description: {index_description}")
        
        # Get index instance
        index = pc.Index(index_name)
        
        # Test vector operations
        test_vector_operations(index, dimension)
        
        # Test assistant operations
        test_assistant_operations(pc)
        
        # Clean up - delete index
        print("\n=== Cleanup ===")
        print("\nDeleting index...")
        agentops.record(ActionEvent(
            action_type="delete_index",
            params={"name": index_name}
        ))
        pc.delete_index(index_name)
        print(f"Index {index_name} deleted")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        agentops.end_session(end_state="Fail")
        return
    
    agentops.end_session(end_state="Success")
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main() 