"""
# Improved Tool Integration with RAG (Retrieval-Augmented Generation) in Agno

This example demonstrates how to enhance Agno agents with RAG capabilities, allowing them to access and reason over external knowledge bases for more accurate and source-backed responses.

## Overview
This improved example shows how to integrate RAG with Agno agents where we:

1. **Set up a knowledge base** with documents, URLs, and other external sources
2. **Configure vector databases** (like Pinecone, Weaviate, or ChromaDB) for efficient semantic search
3. **Implement retrieval** using embeddings and reranking for accurate information access
4. **Create RAG-enabled agents** that can search, retrieve, and reason over the knowledge base
5. **Handle missing API keys gracefully** and provide meaningful examples

By using RAG, agents can provide responses backed by external sources rather than relying solely on their training data, significantly improving accuracy and verifiability of their outputs.

RAG enables agents to access and reason over large knowledge bases,
providing accurate, source-backed responses instead of relying solely on training data.

## Key Improvements:
- Better error handling for missing API keys
- Fallback examples when services are unavailable
- More comprehensive documentation
- Clearer demonstration of concepts
- Practical examples that work out of the box
"""

import os
import sys
from typing import Optional
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

def check_api_keys() -> dict:
    """
    Check if required API keys are available and provide helpful guidance.
    
    Returns:
        dict: Status of each API key with helpful messages
    """
    api_keys = {
        'OPENAI_API_KEY': os.getenv("OPENAI_API_KEY"),
        'AGENTOPS_API_KEY': os.getenv("AGENTOPS_API_KEY"),
        'COHERE_API_KEY': os.getenv("COHERE_API_KEY")
    }
    
    status = {}
    for key, value in api_keys.items():
        if value and value != "your_api_key_here":
            status[key] = {"available": True, "message": "✓ Available"}
        else:
            status[key] = {"available": False, "message": f"✗ Missing - Set {key} in .env file"}
    
    return status

def demonstrate_concept_without_apis():
    """
    Demonstrate the RAG concept and architecture without requiring real API keys.
    This shows the structure and explains what would happen with proper configuration.
    """
    print("\n" + "="*80)
    print("🚀 AGNO RAG TOOL INTEGRATION DEMONSTRATION")
    print("="*80)
    
    print("\n📋 CONCEPT OVERVIEW:")
    print("This example demonstrates how to build a RAG-enabled agent that can:")
    print("• Load knowledge from external URLs")
    print("• Create vector embeddings for semantic search")
    print("• Retrieve relevant information based on queries")
    print("• Generate responses backed by source material")
    print("• Use reasoning tools for complex problem-solving")
    
    print("\n🏗️  ARCHITECTURE COMPONENTS:")
    print("1. Knowledge Base: UrlKnowledge - Loads content from specified URLs")
    print("2. Vector Database: LanceDB - Stores and searches embeddings")
    print("3. Embedder: CohereEmbedder - Converts text to vector representations")
    print("4. Reranker: CohereReranker - Improves search result relevance")
    print("5. Agent: OpenAI GPT-4 - Generates responses using retrieved context")
    print("6. Tools: ReasoningTools - Adds structured thinking capabilities")
    
    print("\n⚙️  CONFIGURATION EXAMPLE:")
    print("""
    # Knowledge base setup
    knowledge_base = UrlKnowledge(
        urls=["https://docs.agno.com/introduction/agents.md"],
        vector_db=LanceDb(
            uri="tmp/lancedb",
            table_name="agno_docs",
            search_type=SearchType.hybrid,
            embedder=CohereEmbedder(id="embed-v4.0"),
            reranker=CohereReranker(model="rerank-v3.5"),
        ),
    )
    
    # Agent configuration
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        knowledge=knowledge_base,
        search_knowledge=True,
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            "Include sources in your response.",
            "Always search your knowledge before answering.",
            "Only include the output in your response. No other text.",
        ],
    )
    """)
    
    print("\n🔄 WORKFLOW EXAMPLE:")
    print("1. User asks: 'What are Agents?'")
    print("2. System searches knowledge base for relevant content")
    print("3. Vector database returns semantically similar documents")
    print("4. Reranker improves result relevance")
    print("5. Agent uses retrieved context to generate response")
    print("6. Response includes source citations")
    
    print("\n💡 EXPECTED OUTPUT:")
    print("With proper API keys, the agent would provide a comprehensive answer")
    print("about Agents based on the Agno documentation, including:")
    print("• Definition and core concepts")
    print("• Key features and capabilities")
    print("• Usage examples")
    print("• Source citations from the loaded documentation")

def demonstrate_tool_integration_with_fallback():
    """
    Attempt to demonstrate the full tool integration, with graceful fallback
    if API keys are missing.
    """
    print("\n🔑 API KEY STATUS:")
    api_status = check_api_keys()
    all_keys_available = all(status["available"] for status in api_status.values())
    
    for key, status in api_status.items():
        print(f"  {key}: {status['message']}")
    
    if not all_keys_available:
        print("\n⚠️  Some API keys are missing. Showing conceptual demonstration instead.")
        print("To run the full example, please:")
        print("1. Create a .env file in this directory")
        print("2. Add your API keys:")
        print("   OPENAI_API_KEY=your_openai_key_here")
        print("   AGENTOPS_API_KEY=your_agentops_key_here")
        print("   COHERE_API_KEY=your_cohere_key_here")
        print("3. Run the script again")
        
        demonstrate_concept_without_apis()
        return
    
    print("\n✅ All API keys available! Attempting full demonstration...")
    
    try:
        # Initialize AgentOps for monitoring (only if key is available)
        agentops.init(auto_start_session=False, tags=["agno-example", "tool-integrations"])
        
        tracer = agentops.start_trace(trace_name="Agno Tool Integration Demonstration")
        
        try:
            print("\n🔄 Setting up knowledge base...")
            # Create knowledge base from documentation URLs
            knowledge_base = UrlKnowledge(
                urls=["https://docs.agno.com/introduction/agents.md"],
                vector_db=LanceDb(
                    uri="tmp/lancedb",
                    table_name="agno_docs",
                    search_type=SearchType.hybrid,
                    embedder=CohereEmbedder(id="embed-v4.0"),
                    reranker=CohereReranker(model="rerank-v3.5"),
                ),
            )
            print("✅ Knowledge base configured successfully!")
            
            print("\n🤖 Creating RAG-enabled agent...")
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
            print("✅ Agent created successfully!")
            
            print("\n❓ Asking: 'What are Agents?'")
            print("🔍 Agent will search knowledge base and provide response...")
            print("\n" + "="*80)
            print("AGENT RESPONSE:")
            print("="*80)
            
            # Print response with full reasoning process visible
            agent.print_response(
                "What are Agents?",
                show_full_reasoning=True,
            )
            
            print("\n" + "="*80)
            print("✅ DEMONSTRATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            
            agentops.end_trace(tracer, end_state="Success")
            
        except Exception as e:
            print(f"\n❌ Error during execution: {str(e)}")
            print("This might be due to:")
            print("• Network connectivity issues")
            print("• Invalid API keys")
            print("• Service availability")
            print("• URL accessibility")
            agentops.end_trace(tracer, end_state="Error")
            
    except Exception as e:
        print(f"\n❌ Failed to initialize AgentOps: {str(e)}")
        print("Proceeding without monitoring...")
        demonstrate_concept_without_apis()

def create_sample_env_file():
    """Create a sample .env file with placeholder values if it doesn't exist."""
    env_file_path = ".env"
    
    if not os.path.exists(env_file_path):
        print("\n📝 Creating sample .env file...")
        
        sample_env_content = """# Agno Tool Integration Example - API Keys
# Replace the placeholder values with your actual API keys

# OpenAI API Key - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# AgentOps API Key - Get from https://app.agentops.ai/settings/projects
AGENTOPS_API_KEY=your_agentops_api_key_here

# Cohere API Key - Get from https://dashboard.cohere.com/api-keys
COHERE_API_KEY=your_cohere_api_key_here
"""
        
        with open(env_file_path, 'w') as f:
            f.write(sample_env_content)
        
        print(f"✅ Created {env_file_path} with placeholder values")
        print("Please edit this file and add your actual API keys")
    else:
        print(f"✅ Found existing {env_file_path} file")

def main():
    """Main function to run the improved demonstration."""
    print("🔧 AGNO TOOL INTEGRATION - IMPROVED EXAMPLE")
    print("This example demonstrates RAG capabilities with better error handling")
    
    # Create sample .env file if it doesn't exist
    create_sample_env_file()
    
    # Run the demonstration with fallback
    demonstrate_tool_integration_with_fallback()
    
    print("\n📚 ADDITIONAL RESOURCES:")
    print("• Agno Documentation: https://docs.agno.com/")
    print("• OpenAI API: https://platform.openai.com/")
    print("• Cohere API: https://cohere.com/")
    print("• AgentOps: https://agentops.ai/")
    print("• LanceDB: https://lancedb.com/")

if __name__ == "__main__":
    main()