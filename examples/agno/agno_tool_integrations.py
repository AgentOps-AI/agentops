"""
# Tool Integration with RAG (Retrieval-Augmented Generation) in Agno

This example demonstrates how to enhance Agno agents with RAG capabilities, allowing them to access and reason over external knowledge bases for more accurate and source-backed responses.

## Overview
This example shows how to integrate RAG with Agno agents where we:

1. **Set up a knowledge base** with documents, URLs, and other external sources
2. **Configure vector databases** (like Pinecone, Weaviate, or ChromaDB) for efficient semantic search
3. **Implement retrieval** using embeddings and reranking for accurate information access
4. **Create RAG-enabled agents** that can search, retrieve, and reason over the knowledge base

By using RAG, agents can provide responses backed by external sources rather than relying solely on their training data, significantly improving accuracy and verifiability of their outputs.

RAG enables agents to access and reason over large knowledge bases,
providing accurate, source-backed responses instead of relying solely on training data.
"""

import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
import agentops
from dotenv import load_dotenv

# Knowledge and RAG components
from agno.knowledge.url import UrlKnowledge
from agno.vectordb.lancedb import LanceDb
from agno.vectordb.search import SearchType
from agno.embedder.cohere import CohereEmbedder
from agno.reranker.cohere import CohereReranker
from agno.tools.reasoning import ReasoningTools

# Load environment variables
load_dotenv()

# Initialize AgentOps for monitoring
agentops.init(auto_start_session=False, tags=["agno-example", "tool-integrations"])

# API keys and configuration
os.environ["COHERE_API_KEY"] = os.getenv("COHERE_API_KEY")


def demonstrate_tool_integration():
    """
    Demonstrate advanced tool integration with RAG and knowledge bases.

    This function shows how to:
    1. Create a knowledge base from external sources
    2. Set up a vector database with embeddings
    3. Configure an agent with RAG capabilities
    4. Enable reasoning tools for complex problem-solving
    """
    tracer = agentops.start_trace(trace_name="Agno Tool Integration Demonstration")
    try:
        # Create knowledge base from documentation URLs
        # This loads content from the specified URLs and prepares it for RAG
        knowledge_base = UrlKnowledge(
            urls=["https://docs.agno.com/introduction/agents.md"],
            vector_db=LanceDb(
                uri="tmp/lancedb",
                table_name="agno_docs",
                search_type=SearchType.hybrid,
                embedder=CohereEmbedder(
                    id="embed-v4.0",
                ),
                reranker=CohereReranker(
                    model="rerank-v3.5",
                ),
            ),
        )

        # Create an intelligent agent with RAG capabilities
        agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            knowledge=knowledge_base,
            search_knowledge=True,
            tools=[ReasoningTools(add_instructions=True)],
            instructions=[
                "Include sources in your response.",
                "Always search your knowledge before answering the question.",
                "Only include the output in your response. No other text.",
            ],
        )

        # Print response with full reasoning process visible
        agent.print_response(
            "What are Agents?",
            show_full_reasoning=True,
        )
        agentops.end_trace(tracer, end_state="Success")
    except Exception:
        agentops.end_trace(tracer, end_state="Error")


demonstrate_tool_integration()
