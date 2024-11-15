import agentops
from agentops.llms.pinecone import PineconeProvider
from dotenv import load_dotenv
from pinecone import Pinecone
import os

load_dotenv()

def test_inference_operations():
    """Test Pinecone's Inference API operations"""
    print("\nTesting Pinecone Inference API operations...")
    
    # Initialize Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Get PineconeProvider instance
    provider = PineconeProvider(pc)
    
    try:
        # Test embedding generation
        print("\nTesting embedding generation...")
        test_texts = [
            "Apple is a popular fruit known for its sweetness.",
            "Apple Inc. is a technology company that makes iPhones."
        ]
        
        embeddings = provider.embed(
            pc,  # Pass the Pinecone instance
            model="multilingual-e5-large",
            inputs=test_texts,
            parameters={
                "input_type": "passage",
                "truncate": "END"
            }
        )
        print(f"Generated {len(embeddings.data)} embeddings")
        print(f"Embedding dimension: {len(embeddings.data[0].values)}")
        
        # Test document reranking
        print("\nTesting document reranking...")
        rerank_result = provider.rerank(
            pc,  # Pass the Pinecone instance
            model="bge-reranker-v2-m3",
            query="Tell me about the tech company Apple",
            documents=[
                {"id": "vec1", "text": "Apple is a popular fruit known for its sweetness and crisp texture."},
                {"id": "vec2", "text": "Apple Inc. has revolutionized the tech industry with its iPhone."},
                {"id": "vec3", "text": "Many people enjoy eating apples as a healthy snack."},
                {"id": "vec4", "text": "Apple's MacBook laptops are popular among professionals."}
            ],
            top_n=4,
            return_documents=True
        )
        
        print("\nReranking results:")
        for result in rerank_result.data:
            print(f"Score: {result.score:.4f}")
            print(f"Document: {result.document['text'][:100]}...")
            print(f"Index: {result.index}")
            print("---")
        
        if hasattr(rerank_result, 'usage'):
            print("\nUsage information:")
            print(rerank_result.usage)
        
    except Exception as e:
        print(f"Error in inference operations: {e}")
        agentops.end_session(end_state="Fail")
        return
    
    agentops.end_session(end_state="Success")
    print("\nInference test completed successfully!")

if __name__ == "__main__":
    agentops.init(default_tags=["pinecone-inference-test"])
    test_inference_operations() 