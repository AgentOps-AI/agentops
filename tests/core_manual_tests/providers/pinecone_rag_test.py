import agentops
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import numpy as np
import os
import time
from openai import OpenAI
import tiktoken

load_dotenv()

# Initialize clients
openai_client = OpenAI()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Test dataset - State of the Union paragraphs
SAMPLE_TEXTS = [
    "The state of our Union is strong because our people are strong. Over the last year, we've made progress. Created jobs. Reduced deficit. Lowered prescription drug costs.",
    "We are the only country that has emerged from every crisis stronger than when we entered it. That is what we are doing again.",
    "We have more to do, but here is the good news: Our country is stronger today than we were a year ago.",
    "As I stand here tonight, we have created a record 12 million new jobs – more jobs created in two years than any president has ever created in four years.",
    "For decades, the middle class was hollowed out. Too many good-paying manufacturing jobs moved overseas. Factories closed down.",
]

def get_embedding(text, model="text-embedding-3-small"):
    """Get OpenAI embedding for text"""
    response = openai_client.embeddings.create(
        model=model,
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

def create_index(index_name, dimension):
    """Create Pinecone index"""
    print(f"\nCreating index {index_name}...")
    
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)
    
    return pc.Index(index_name)

def index_documents(index, texts):
    """Index documents with their embeddings"""
    print("\nIndexing documents...")
    vectors = []
    
    for i, text in enumerate(texts):
        embedding = get_embedding(text)
        vectors.append((f"doc{i}", embedding, {"text": text}))
    
    upsert_response = index.upsert(
        vectors=vectors,
        namespace="test-namespace"
    )
    print(f"Indexed {len(vectors)} documents")
    return upsert_response

def query_similar(index, query, top_k=2):
    """Query similar documents"""
    print(f"\nQuerying: {query}")
    query_embedding = get_embedding(query)
    
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace="test-namespace",
        include_metadata=True
    )
    
    # Add debug information
    print(f"Found {len(results.matches)} matches")
    for match in results.matches:
        print(f"Score: {match.score:.4f}, Text: {match.metadata['text'][:100]}...")
    
    return results

def generate_answer(query, context):
    """Generate answer using OpenAI"""
    prompt = f"""Based on the following context, answer the question. 
    If the answer cannot be found in the context, say "I cannot answer this based on the provided context."

    Context:
    {context}

    Question: {query}
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def test_rag_pipeline():
    """Test complete RAG pipeline"""
    index_name = "test-index-rag"
    dimension = 1536  # Dimension for text-embedding-3-small
    
    try:
        # List existing indexes
        print("\nListing indexes...")
        indexes = pc.list_indexes()
        print(f"Current indexes: {indexes}")
        
        # Create new index if needed
        if index_name not in indexes:
            index = create_index(index_name, dimension)
        else:
            # Delete existing index to start fresh
            pc.delete_index(index_name)
            time.sleep(2)  # Wait for deletion
            index = create_index(index_name, dimension)
        
        # Index sample documents
        print("\nWaiting for index to be ready...")
        time.sleep(5)  # Add delay to ensure index is ready
        
        index_documents(index, SAMPLE_TEXTS)
        print("Waiting for documents to be indexed...")
        time.sleep(5)  # Add delay to ensure documents are indexed
        
        # Test queries
        test_queries = [
            "How many new jobs were created according to the speech?",
            "What happened to manufacturing jobs and the middle class?",
            "What is the current state of the Union?",
            "What about education?" # This should get "cannot answer" response
        ]
        
        for query in test_queries:
            # Get similar documents
            results = query_similar(index, query)
            
            # Extract context from results
            context = "\n".join([match.metadata["text"] for match in results.matches])
            
            # Generate answer
            answer = generate_answer(query, context)
            print(f"\nQ: {query}")
            print(f"A: {answer}")
            print(f"Context used: {context}\n")
            print("-" * 50)
            time.sleep(1)  # Rate limiting
        
        # Clean up
        print("\nCleaning up...")
        pc.delete_index(index_name)
        print(f"Index {index_name} deleted")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        agentops.end_session(end_state="Fail")
        return
    
    agentops.end_session(end_state="Success")
    print("\nTest completed successfully!")

if __name__ == "__main__":
    agentops.init(default_tags=["pinecone-rag-test"])
    test_rag_pipeline()