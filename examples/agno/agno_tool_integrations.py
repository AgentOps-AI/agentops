"""
Tool Integration with RAG (Retrieval-Augmented Generation) in Agno

This example demonstrates how to create intelligent agents with:
- Knowledge bases from external sources (URLs, documents)
- Vector databases for efficient semantic search
- Embeddings and reranking for accurate information retrieval
- Reasoning tools for enhanced problem-solving capabilities

RAG enables agents to access and reason over large knowledge bases,
providing accurate, source-backed responses instead of relying solely on training data.
"""

import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
import asyncio
import agentops
from dotenv import load_dotenv

# Knowledge and RAG components
from agno.knowledge.url import UrlKnowledge  # For loading knowledge from URLs
from agno.vectordb.lancedb import LanceDb  # Vector database for storing embeddings
from agno.vectordb.search import SearchType  # Search strategies (hybrid, semantic, etc.)
from agno.embedder.cohere import CohereEmbedder  # For creating text embeddings
from agno.reranker.cohere import CohereReranker  # For improving search results
from agno.tools.reasoning import ReasoningTools  # Advanced reasoning capabilities

# Load environment variables
load_dotenv()

# Initialize AgentOps for monitoring
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# API keys and configuration
cohere_api_key = os.getenv("COHERE_API_KEY")  # Required for embeddings and reranking
MODEL_ID = "gpt-4o-mini"  # Default model for agents


def check_environment():
    """
    Verify that all required API keys are properly configured.

    This demo requires:
    - AGENTOPS_API_KEY: For monitoring agent behavior
    - OPENAI_API_KEY: For the AI model
    - COHERE_API_KEY: For embeddings and reranking

    Returns:
        bool: True if all required environment variables are set
    """
    required_vars = ["AGENTOPS_API_KEY", "OPENAI_API_KEY", "COHERE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file or environment")
        print("\nExample .env file:")
        print("AGENTOPS_API_KEY=your_agentops_key")
        print("OPENAI_API_KEY=your_openai_key")
        print("COHERE_API_KEY=your_cohere_key")
        return False

    print("✓ Environment variables checked successfully")
    return True


def demonstrate_tool_integration():
    """
    Demonstrate advanced tool integration with RAG and knowledge bases.

    This function shows how to:
    1. Create a knowledge base from external sources
    2. Set up a vector database with embeddings
    3. Configure an agent with RAG capabilities
    4. Enable reasoning tools for complex problem-solving
    """
    print("\n" + "=" * 60)
    print("TOOL INTEGRATION WITH RAG (Retrieval-Augmented Generation)")
    print("=" * 60)

    try:
        print("\n1. Setting up knowledge base and vector database...")

        # Create knowledge base from documentation URLs
        # This loads content from the specified URLs and prepares it for RAG
        knowledge_base = UrlKnowledge(
            urls=["https://docs.agno.com/introduction/agents.md"],  # Documentation to learn from
            # Configure vector database for efficient semantic search
            vector_db=LanceDb(
                uri="tmp/lancedb",  # Local storage path for the database
                table_name="agno_docs",  # Table to store document embeddings
                search_type=SearchType.hybrid,  # Combines keyword and semantic search
                # Embedder converts text to numerical vectors for similarity search
                embedder=CohereEmbedder(
                    id="embed-v4.0",  # Cohere's embedding model
                    api_key=cohere_api_key,
                ),
                # Reranker improves search results by re-scoring them
                reranker=CohereReranker(
                    model="rerank-v3.5",  # Cohere's reranking model
                    api_key=cohere_api_key,
                ),
            ),
        )
        print("   ✓ Knowledge base created from documentation")
        print("   ✓ Vector database configured with hybrid search")

        # Create an intelligent agent with RAG capabilities
        print("\n2. Creating RAG-enabled agent...")
        agent = Agent(
            model=OpenAIChat(id=MODEL_ID),
            # Agentic RAG is automatically enabled when knowledge is provided
            knowledge=knowledge_base,
            # Allow the agent to search its knowledge base on demand
            search_knowledge=True,
            # Add reasoning tools for step-by-step problem solving
            tools=[ReasoningTools(add_instructions=True)],
            # Custom instructions for how the agent should behave
            instructions=[
                "Include sources in your response.",  # Cite where information comes from
                "Always search your knowledge before answering the question.",  # Use RAG first
                "Only include the output in your response. No other text.",  # Clean responses
            ],
            markdown=True,  # Format responses in markdown
        )
        print("   ✓ Agent created with:")
        print("     - Knowledge base access")
        print("     - On-demand search capability")
        print("     - Reasoning tools")
        print("     - Source citation requirements")

        # Test the RAG agent with a question about its knowledge base
        print("\n3. Testing RAG agent with knowledge query...")
        print("   Question: 'What are Agents?'")
        print("\n" + "-" * 60)

        # Print response with full reasoning process visible
        agent.print_response(
            "What are Agents?",
            show_full_reasoning=True,  # Shows how the agent searches and reasons
        )

        print("\n" + "-" * 60)
        print("✓ RAG demonstration completed")
        print("\nNotice how the agent:")
        print("- Searched the knowledge base for relevant information")
        print("- Used reasoning tools to formulate the answer")
        print("- Included sources from the documentation")

    except Exception as e:
        print(f"\nError during tool integration: {e}")
        print("This might be due to:")
        print("- Missing API keys (especially COHERE_API_KEY)")
        print("- Network issues accessing documentation URLs")
        print("- Vector database initialization problems")


async def main():
    """
    Main function that orchestrates the tool integration demonstration.

    This async function handles:
    - Environment validation
    - Running the RAG and tool integration demo
    - Error handling and user feedback
    """
    print("Welcome to Agno Tool Integration Demo")
    print("This demo showcases RAG (Retrieval-Augmented Generation)")
    print("and advanced tool integration capabilities.")
    print()

    # Validate environment setup
    if not check_environment():
        print("\nCannot proceed without proper API configuration")
        print("Please obtain a Cohere API key from: https://cohere.com")
        return

    # Run demonstration
    print("\nStarting tool integration demonstration...")

    try:
        demonstrate_tool_integration()
        print("\n\n✓ Tool integration demo completed successfully!")
        print("\nKey Takeaways:")
        print("- RAG enables agents to access external knowledge bases")
        print("- Vector databases provide efficient semantic search")
        print("- Embeddings and reranking improve information retrieval")
        print("- Reasoning tools enhance problem-solving capabilities")
        print("- AgentOps tracks all tool usage and knowledge searches")

    except Exception as e:
        print(f"Demo failed: {e}")
        print("Please check your API keys and network connection")


if __name__ == "__main__":
    """
    Entry point for the script.
    
    Uses asyncio to run the main function, maintaining consistency
    with other examples and preparing for async operations.
    """
    asyncio.run(main())
