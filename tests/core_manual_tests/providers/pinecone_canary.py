import asyncio
import agentops
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import numpy as np
import os
import time
from agentops.event import ActionEvent

load_dotenv()
agentops.init(default_tags=["pinecone-provider-test"])

# Initialize Pinecone with new client pattern
pc = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY")
)

# Create test index
dimension = 8
index_name = "test-index"

try:
    if index_name not in pc.list_indexes():
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
except Exception as e:
    print(f"Index creation error: {e}")

try:
    index = pc.Index(index_name)
    vector = np.random.rand(dimension).tolist()
    vectors = [
        ("id1", vector, {"metadata": "test1"}),
        ("id2", vector, {"metadata": "test2"})
    ]

    # Record vector operations using ActionEvent
    agentops.record(ActionEvent(
        action_type="vector_upsert"
    ))
    upsert_response = index.upsert(
        vectors=vectors,
        namespace="test-namespace"
    )
    print("Upsert response:", upsert_response)

    agentops.record(ActionEvent(
        action_type="vector_query"
    ))
    query_response = index.query(
        vector=vector,
        top_k=2,
        namespace="test-namespace",
        include_metadata=True
    )
    print("Query response:", query_response)

except Exception as e:
    print(f"Operation error: {e}")

agentops.stop_instrumenting()

# Clean up
try:
    pc.delete_index(index_name)
except Exception as e:
    print(f"Error deleting index: {e}")

agentops.end_session(end_state="Success")

###
#  Used to verify that one session is created with vector operation events
###