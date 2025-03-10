 #!/usr/bin/env python
"""
Example of integrating the AgentOps SDK with an existing LLM application.

This example demonstrates how to add tracing to an existing application
that uses LLMs without significantly changing its structure.
"""

import os
import sys
import time
import random
from typing import List, Dict, Any, Optional

from agentops.config import Config
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.tool import tool


# Simulate an LLM API client
class MockLLMClient:
    """A mock LLM client that simulates responses."""
    
    def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate a response for the given prompt."""
        # Simulate LLM processing time
        time.sleep(0.7)
        
        # Simulate a response
        return {
            "choices": [
                {
                    "text": f"This is a response to: {prompt}",
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 10,
                "total_tokens": len(prompt.split()) + 10
            }
        }
    
    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a chat response for the given messages."""
        # Simulate LLM processing time
        time.sleep(0.8)
        
        # Get the last user message
        last_message = next((m for m in reversed(messages) if m["role"] == "user"), None)
        user_content = last_message["content"] if last_message else "No user message found"
        
        # Simulate a response
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"I understand you're asking about: {user_content}. Here's my response..."
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(m["content"].split()) for m in messages),
                "completion_tokens": 15,
                "total_tokens": sum(len(m["content"].split()) for m in messages) + 15
            }
        }


# Original application code (before integration)
class OriginalChatbot:
    """The original chatbot implementation before AgentOps integration."""
    
    def __init__(self):
        """Initialize the chatbot."""
        self.llm_client = MockLLMClient()
        self.conversation_history = []
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})
    
    def get_response(self, user_input: str) -> str:
        """Get a response from the chatbot."""
        # Add user message to history
        self.add_message("user", user_input)
        
        # Generate response
        response = self.llm_client.chat(self.conversation_history)
        
        # Extract and add assistant message to history
        assistant_message = response["choices"][0]["message"]["content"]
        self.add_message("assistant", assistant_message)
        
        return assistant_message
    
    def search_knowledge_base(self, query: str) -> List[str]:
        """Search the knowledge base for relevant information."""
        # Simulate knowledge base search
        time.sleep(0.4)
        return [
            f"Knowledge item 1 about {query}",
            f"Knowledge item 2 about {query}",
            f"Knowledge item 3 about {query}"
        ]
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query with search and response generation."""
        # Search knowledge base
        search_results = self.search_knowledge_base(query)
        
        # Prepare prompt with search results
        prompt = f"Query: {query}\nContext: {', '.join(search_results)}\nResponse:"
        
        # Generate response
        response = self.llm_client.generate(prompt)
        
        return {
            "query": query,
            "search_results": search_results,
            "response": response["choices"][0]["text"],
            "tokens": response["usage"]["total_tokens"]
        }


# Integrated application code (with AgentOps SDK)
@session(name="chatbot_session", tags=["example", "integration"])
class TracedChatbot:
    """The chatbot implementation with AgentOps SDK integration."""
    
    def __init__(self):
        """Initialize the chatbot."""
        self.llm_client = MockLLMClient()
        self.conversation_history = []
        self.agent = ChatbotAgent()
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})
    
    def get_response(self, user_input: str) -> str:
        """Get a response from the chatbot."""
        # Add user message to history
        self.add_message("user", user_input)
        
        # Use the agent to generate a response
        response = self.agent.generate_chat_response(self.conversation_history)
        
        # Extract and add assistant message to history
        assistant_message = response["choices"][0]["message"]["content"]
        self.add_message("assistant", assistant_message)
        
        return assistant_message
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query with search and response generation."""
        # Use the agent to process the query
        return self.agent.process_query(query)


@agent(name="chatbot_agent", agent_type="assistant")
class ChatbotAgent:
    """An agent that handles chatbot operations."""
    
    def __init__(self):
        """Initialize the chatbot agent."""
        self.llm_client = MockLLMClient()
    
    def generate_chat_response(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a chat response."""
        try:
            # Record the agent's thought process
            self._agent_span.record_thought("Generating a response based on conversation history")
        except AttributeError:
            pass
        
        # Use the chat tool to generate a response
        return self.chat_completion(conversation_history)
    
    @tool(name="chat_completion", tool_type="llm")
    def chat_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a chat completion."""
        return self.llm_client.chat(messages)
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query with search and response generation."""
        try:
            # Record the agent's thought process
            self._agent_span.record_thought(f"Processing query: {query}")
            self._agent_span.record_action("search_then_respond")
        except AttributeError:
            pass
        
        # Search knowledge base
        search_results = self.search_knowledge_base(query)
        
        # Generate response based on search results
        response_data = self.generate_response(query, search_results)
        
        return {
            "query": query,
            "search_results": search_results,
            "response": response_data["choices"][0]["text"],
            "tokens": response_data["usage"]["total_tokens"]
        }
    
    @tool(name="search_knowledge_base", tool_type="search")
    def search_knowledge_base(self, query: str) -> List[str]:
        """Search the knowledge base for relevant information."""
        # Simulate knowledge base search
        time.sleep(0.4)
        return [
            f"Knowledge item 1 about {query}",
            f"Knowledge item 2 about {query}",
            f"Knowledge item 3 about {query}"
        ]
    
    @tool(name="generate_response", tool_type="llm")
    def generate_response(self, query: str, context: List[str]) -> Dict[str, Any]:
        """Generate a response based on the query and context."""
        # Prepare prompt with search results
        prompt = f"Query: {query}\nContext: {', '.join(context)}\nResponse:"
        
        # Generate response
        return self.llm_client.generate(prompt)


def initialize_tracing():
    """Initialize the tracing core."""
    config = Config(
        api_key="test_key",  # Replace with your API key
        host="https://api.agentops.ai",  # Replace with your host
        project_id="example-project",  # Replace with your project ID
    )
    core = TracingCore.get_instance()
    core.initialize(config)
    return core


def demonstrate_original_chatbot():
    """Demonstrate the original chatbot without tracing."""
    print("\n=== Original Chatbot (No Tracing) ===")
    
    chatbot = OriginalChatbot()
    
    # Demonstrate chat
    print("\nChat example:")
    user_input = "Tell me about AgentOps"
    print(f"User: {user_input}")
    response = chatbot.get_response(user_input)
    print(f"Chatbot: {response}")
    
    # Demonstrate query processing
    print("\nQuery processing example:")
    query = "How does AgentOps SDK work?"
    result = chatbot.process_query(query)
    print(f"Query: {result['query']}")
    print(f"Search results: {result['search_results']}")
    print(f"Response: {result['response']}")
    print(f"Tokens used: {result['tokens']}")


def demonstrate_traced_chatbot():
    """Demonstrate the traced chatbot with AgentOps SDK integration."""
    print("\n=== Traced Chatbot (With AgentOps SDK) ===")
    
    # Initialize tracing
    initialize_tracing()
    
    chatbot = TracedChatbot()
    
    # Demonstrate chat
    print("\nChat example:")
    user_input = "Tell me about AgentOps"
    print(f"User: {user_input}")
    response = chatbot.get_response(user_input)
    print(f"Chatbot: {response}")
    
    # Demonstrate query processing
    print("\nQuery processing example:")
    query = "How does AgentOps SDK work?"
    result = chatbot.process_query(query)
    print(f"Query: {result['query']}")
    print(f"Search results: {result['search_results']}")
    print(f"Response: {result['response']}")
    print(f"Tokens used: {result['tokens']}")
    
    print("\nWith the traced version, all operations are now being tracked in AgentOps!")


def main():
    """Run the example."""
    print("=== AgentOps SDK Integration Example ===")
    print("This example demonstrates how to integrate the AgentOps SDK with an existing application.")
    
    # Demonstrate the original chatbot
    demonstrate_original_chatbot()
    
    # Demonstrate the traced chatbot
    demonstrate_traced_chatbot()


if __name__ == "__main__":
    main()
