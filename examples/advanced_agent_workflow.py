"""
Advanced Agent Workflow Example

This example demonstrates a complete agent workflow using various decorators
to instrument different parts of the process.
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional, AsyncGenerator

from agentops.sdk.decorators.agentops import (
    session,
    agent,
    agent_thinking,
    agent_decision,
    llm_call,
    llm_stream,
    tool,
    workflow_step,
    workflow_task,
    agent_class,
    tool_class
)


class Memory:
    """Simple memory store for the agent."""
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.knowledge: Dict[str, Any] = {}
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
    
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the full conversation history for a session."""
        return self.conversations.get(session_id, [])
    
    def store_knowledge(self, key: str, value: Any):
        """Store knowledge for later use."""
        self.knowledge[key] = value
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """Retrieve stored knowledge."""
        return self.knowledge.get(key)


@tool_class(method_name="search", name="web_search_tool")
class SearchTool:
    """Web search tool implementation."""
    
    def __init__(self):
        self.api_calls = 0
    
    def search(self, query: str) -> Dict[str, Any]:
        """Search the web for information."""
        print(f"Searching web for: {query}")
        self.api_calls += 1
        time.sleep(0.3)  # Simulate API call
        
        # Simulate search results
        results = [
            {"title": f"Result {i} for {query}", "snippet": f"Information about {query} #{i}"} 
            for i in range(3)
        ]
        
        return {
            "query": query,
            "results": results,
            "timestamp": time.time()
        }


@tool()
def calculator(expression: str) -> Dict[str, Any]:
    """Calculator tool for mathematical operations."""
    print(f"Calculating: {expression}")
    try:
        # Safely evaluate the expression
        result = eval(expression, {"__builtins__": {}}, {"sum": sum, "max": max, "min": min})
        return {
            "expression": expression,
            "result": result,
            "success": True
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False
        }


@llm_call()
async def generate_text(prompt: str, model: str = "gpt-4") -> str:
    """Generate text using an LLM."""
    print(f"Generating text with {model}: {prompt[:50]}...")
    await asyncio.sleep(0.5)  # Simulate API call
    return f"Generated response for: {prompt[:20]}..."


@llm_stream()
async def stream_text(prompt: str, model: str = "gpt-4") -> AsyncGenerator[str, None]:
    """Stream text from an LLM."""
    print(f"Streaming text with {model}: {prompt[:50]}...")
    for i in range(5):
        await asyncio.sleep(0.1)  # Simulate streaming chunks
        chunk = f"Chunk {i} for {prompt[:10]}..."
        yield chunk


@agent_thinking()
async def analyze_query(query: str, memory: Memory, session_id: str) -> Dict[str, Any]:
    """Analyze the user query to determine the best approach."""
    print(f"Analyzing query: {query}")
    
    # Get relevant conversation history
    history = memory.get_conversation(session_id)
    
    # Generate analysis (usually this would be an LLM call)
    await asyncio.sleep(0.2)  # Simulate thinking
    
    # Store the analysis in memory
    analysis = {
        "type": "information" if "?" in query else "task",
        "complexity": "high" if len(query) > 50 else "low",
        "requires_tools": any(kw in query.lower() for kw in ["calculate", "search", "find"]),
        "context_needed": len(history) > 0
    }
    
    memory.store_knowledge(f"{session_id}_analysis", analysis)
    return analysis


@agent_decision()
async def plan_approach(analysis: Dict[str, Any], memory: Memory, session_id: str) -> List[Dict[str, Any]]:
    """Plan the approach based on query analysis."""
    print(f"Planning approach based on analysis: {json.dumps(analysis, indent=2)}")
    
    # Create a plan with steps
    steps = []
    
    if analysis["context_needed"]:
        steps.append({"type": "retrieve_context", "description": "Retrieve relevant context"})
    
    if analysis["requires_tools"]:
        if "calculate" in analysis.get("query", "").lower():
            steps.append({"type": "use_calculator", "description": "Use calculator tool"})
        if any(kw in analysis.get("query", "").lower() for kw in ["search", "find"]):
            steps.append({"type": "web_search", "description": "Search for information"})
    
    steps.append({"type": "generate_response", "description": "Generate final response"})
    
    memory.store_knowledge(f"{session_id}_plan", steps)
    return steps


@workflow_step(name="execute_plan_step")
async def execute_step(step: Dict[str, Any], query: str, memory: Memory, session_id: str) -> Dict[str, Any]:
    """Execute a single step in the plan."""
    print(f"Executing step: {step['type']} - {step['description']}")
    
    result = {"step_type": step["type"], "success": False}
    
    if step["type"] == "retrieve_context":
        # Retrieve context from memory
        history = memory.get_conversation(session_id)
        result["context"] = history
        result["success"] = True
    
    elif step["type"] == "use_calculator":
        # Extract expression from query - simplified for example
        expression = query.replace("calculate", "").replace("?", "").strip()
        calc_result = calculator(expression)
        result["calculator_result"] = calc_result
        result["success"] = calc_result.get("success", False)
    
    elif step["type"] == "web_search":
        # Perform web search
        search_tool = SearchTool()
        search_result = search_tool.search(query)
        result["search_result"] = search_result
        result["success"] = True
    
    elif step["type"] == "generate_response":
        # Generate final response
        prompt = f"Generate a response for the query: {query}"
        response = await generate_text(prompt)
        result["response"] = response
        result["success"] = bool(response)
    
    return result


@workflow_task(name="execute_plan")
async def execute_plan(plan: List[Dict[str, Any]], query: str, memory: Memory, session_id: str) -> Dict[str, Any]:
    """Execute the full plan of steps."""
    print(f"Executing plan with {len(plan)} steps")
    
    results = []
    for step in plan:
        step_result = await execute_step(step, query, memory, session_id)
        results.append(step_result)
        
        # Break if a step fails
        if not step_result["success"]:
            break
    
    return {
        "query": query,
        "steps_executed": len(results),
        "steps_succeeded": sum(1 for r in results if r["success"]),
        "results": results
    }


@agent()
async def process_query(query: str, session_id: str, memory: Memory) -> Dict[str, Any]:
    """Process a user query through the full agent workflow."""
    print(f"Processing query in session {session_id}: {query}")
    
    # Store user query in memory
    memory.add_message(session_id, "user", query)
    
    # Analyze the query
    analysis = await analyze_query(query, memory, session_id)
    analysis["query"] = query  # Add query to analysis for planning
    
    # Plan the approach
    plan = await plan_approach(analysis, memory, session_id)
    
    # Execute the plan
    execution_results = await execute_plan(plan, query, memory, session_id)
    
    # Extract final response if available
    final_response = None
    for result in execution_results["results"]:
        if result["step_type"] == "generate_response" and result["success"]:
            final_response = result["response"]
    
    if final_response:
        # Store agent response in memory
        memory.add_message(session_id, "agent", final_response)
    
    return {
        "query": query,
        "analysis": analysis,
        "plan": plan,
        "execution": execution_results,
        "response": final_response
    }


@session(name="agent_session")
async def handle_session(user_id: str, query: str) -> Dict[str, Any]:
    """Handle a complete agent session."""
    print(f"Starting session for user {user_id}")
    
    # Create session
    session_id = f"session_{user_id}_{int(time.time())}"
    memory = Memory()
    
    # Process query
    result = await process_query(query, session_id, memory)
    
    # Return session results
    return {
        "session_id": session_id,
        "user_id": user_id,
        "query": query,
        "response": result.get("response"),
        "conversation": memory.get_conversation(session_id)
    }


async def main():
    """Run the example agent workflow."""
    # User query
    user_id = "user123"
    query = "Can you search for information about quantum computing and calculate 23 * 45?"
    
    # Process the query in a session
    session_result = await handle_session(user_id, query)
    
    # Print the final result
    print("\n" + "="*50)
    print("SESSION RESULT:")
    print(f"User: {session_result['user_id']}")
    print(f"Query: {session_result['query']}")
    print(f"Response: {session_result['response']}")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main()) 