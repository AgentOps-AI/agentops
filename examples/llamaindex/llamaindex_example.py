#
#

import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.instrumentation.agentops import AgentOpsHandler
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.huggingface import HuggingFaceLLM

handler = AgentOpsHandler()
handler.init()

load_dotenv()

os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_agentops_api_key_here")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = HuggingFaceLLM(model_name="microsoft/DialoGPT-medium")
print("Using local HuggingFace embeddings and LLM")

print("🚀 Starting LlamaIndex AgentOps Integration Example")
print("=" * 50)

documents = [
    Document(text="LlamaIndex is a framework for building context-augmented generative AI applications with LLMs."),
    Document(
        text="AgentOps provides observability into your AI applications, tracking LLM calls, performance metrics, and more."
    ),
    Document(
        text="The integration between LlamaIndex and AgentOps allows you to monitor your RAG applications seamlessly."
    ),
    Document(
        text="Vector databases are used to store and retrieve embeddings for similarity search in RAG applications."
    ),
    Document(
        text="Context-augmented generation combines retrieval and generation to provide more accurate and relevant responses."
    ),
]

print("📚 Creating vector index from sample documents...")

index = VectorStoreIndex.from_documents(documents)

print("✅ Vector index created successfully")

query_engine = index.as_query_engine()

print("🔍 Performing queries...")

queries = [
    "What is LlamaIndex?",
    "How does AgentOps help with AI applications?",
    "What are the benefits of using vector databases in RAG?",
]

for i, query in enumerate(queries, 1):
    print(f"\n📝 Query {i}: {query}")
    response = query_engine.query(query)
    print(f"💬 Response: {response}")

print("\n" + "=" * 50)
print("🎉 Example completed successfully!")
print("📊 Check your AgentOps dashboard to see the recorded session with LLM calls and operations.")
print("🔗 The session link should be printed above by AgentOps.")
