"""
# Tool Integration Example - Self-Contained Demo

This example demonstrates tool integration concepts for AI agents without requiring
any external dependencies. It shows how to create, track, and chain tools together
for complex agent workflows.

## Overview
This example demonstrates:

1. **Creating custom tools** with input/output tracking
2. **Tool chaining** where outputs from one tool feed into another
3. **Error handling** and retry mechanisms for tools
4. **Performance monitoring** of tool execution
5. **Tool composition** for complex workflows

This is a conceptual demonstration that can be adapted to work with any agent framework.
"""

import time
import json
import random
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ToolStatus(Enum):
    """Status of a tool execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY = "retry"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    status: ToolStatus
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Registry for managing and tracking tools."""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[ToolResult] = []
        
    def register(self, name: str, func: Callable, description: str = ""):
        """Register a new tool."""
        self.tools[name] = {
            "function": func,
            "description": description,
            "call_count": 0,
            "total_time_ms": 0,
            "success_count": 0,
            "failure_count": 0
        }
        print(f"✅ Registered tool: {name}")
        
    def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool and track its performance."""
        if name not in self.tools:
            return ToolResult(
                tool_name=name,
                status=ToolStatus.FAILURE,
                output=None,
                error=f"Tool '{name}' not found"
            )
        
        tool = self.tools[name]
        tool["call_count"] += 1
        
        print(f"\n🔧 Executing tool: {name}")
        print(f"   Parameters: {kwargs}")
        
        start_time = time.time()
        try:
            result = tool["function"](**kwargs)
            execution_time_ms = (time.time() - start_time) * 1000
            
            tool["success_count"] += 1
            tool["total_time_ms"] += execution_time_ms
            
            tool_result = ToolResult(
                tool_name=name,
                status=ToolStatus.SUCCESS,
                output=result,
                execution_time_ms=execution_time_ms
            )
            
            print(f"   ✅ Success in {execution_time_ms:.2f}ms")
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            tool["failure_count"] += 1
            tool["total_time_ms"] += execution_time_ms
            
            tool_result = ToolResult(
                tool_name=name,
                status=ToolStatus.FAILURE,
                output=None,
                error=str(e),
                execution_time_ms=execution_time_ms
            )
            
            print(f"   ❌ Failed: {str(e)}")
        
        self.execution_history.append(tool_result)
        return tool_result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about tool usage."""
        stats = {
            "total_executions": len(self.execution_history),
            "tools": {}
        }
        
        for name, tool in self.tools.items():
            if tool["call_count"] > 0:
                avg_time = tool["total_time_ms"] / tool["call_count"]
                success_rate = tool["success_count"] / tool["call_count"] * 100
                
                stats["tools"][name] = {
                    "calls": tool["call_count"],
                    "success_rate": f"{success_rate:.1f}%",
                    "avg_time_ms": f"{avg_time:.2f}",
                    "total_time_ms": f"{tool['total_time_ms']:.2f}"
                }
        
        return stats


# Example Tools
def search_tool(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Simulates searching for information."""
    # Simulate search delay
    time.sleep(random.uniform(0.1, 0.3))
    
    # Mock search results
    results = []
    topics = ["AI agents", "machine learning", "tool integration", "automation", "workflows"]
    
    for i in range(min(max_results, 3)):
        results.append({
            "title": f"{random.choice(topics)} - Result {i+1}",
            "snippet": f"Information about {query}...",
            "relevance": random.uniform(0.7, 1.0),
            "source": f"https://example.com/doc{i+1}"
        })
    
    return sorted(results, key=lambda x: x["relevance"], reverse=True)


def analyze_tool(text: str, analysis_type: str = "summary") -> Dict[str, Any]:
    """Simulates text analysis."""
    # Simulate processing delay
    time.sleep(random.uniform(0.2, 0.4))
    
    word_count = len(text.split())
    
    if analysis_type == "summary":
        return {
            "type": "summary",
            "content": f"Summary of {word_count} words: {text[:100]}...",
            "key_points": ["Point 1", "Point 2", "Point 3"]
        }
    elif analysis_type == "entities":
        return {
            "type": "entities",
            "entities": [
                {"text": "AI", "type": "TECHNOLOGY"},
                {"text": "agents", "type": "CONCEPT"},
                {"text": "integration", "type": "PROCESS"}
            ],
            "word_count": word_count
        }
    else:
        return {"type": analysis_type, "word_count": word_count}


def format_tool(data: Any = None, format_type: str = "markdown", **kwargs) -> str:
    """Simulates formatting data into different formats."""
    time.sleep(0.1)
    
    # If data is not provided but kwargs are, use kwargs as data
    if data is None and kwargs:
        data = kwargs
    
    if format_type == "markdown":
        if isinstance(data, list):
            return "\n".join([f"- {item}" for item in data])
        elif isinstance(data, dict):
            return "\n".join([f"**{k}**: {v}" for k, v in data.items()])
        else:
            return f"*{str(data)}*"
    elif format_type == "json":
        return json.dumps(data, indent=2)
    else:
        return str(data)


class ToolChain:
    """Manages execution of tool chains."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.chain_results: List[ToolResult] = []
        
    def execute_chain(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a chain of tools where each output feeds into the next."""
        print(f"\n🔗 Executing tool chain with {len(steps)} steps")
        
        previous_output = None
        chain_start = time.time()
        
        for i, step in enumerate(steps):
            tool_name = step["tool"]
            params = step.get("params", {})
            
            # Use previous output if specified
            if step.get("use_previous_output") and previous_output is not None:
                if isinstance(previous_output, dict):
                    params.update(previous_output)
                else:
                    params["input"] = previous_output
            
            print(f"\n📍 Step {i+1}/{len(steps)}: {tool_name}")
            
            result = self.registry.execute(tool_name, **params)
            self.chain_results.append(result)
            
            if result.status != ToolStatus.SUCCESS:
                print(f"   ⚠️ Chain interrupted at step {i+1}")
                return {
                    "status": "failed",
                    "failed_at_step": i+1,
                    "error": result.error,
                    "completed_steps": i
                }
            
            previous_output = result.output
        
        chain_time = (time.time() - chain_start) * 1000
        
        return {
            "status": "success",
            "final_output": previous_output,
            "total_time_ms": chain_time,
            "steps_completed": len(steps)
        }


def demonstrate_tool_integration():
    """Main demonstration of tool integration concepts."""
    print("🚀 Tool Integration Demonstration")
    print("=" * 60)
    
    # Initialize tool registry
    registry = ToolRegistry()
    
    # Register tools
    registry.register("search", search_tool, "Search for information")
    registry.register("analyze", analyze_tool, "Analyze text content")
    registry.register("format", format_tool, "Format data for output")
    
    # Example 1: Individual tool execution
    print("\n📌 Example 1: Individual Tool Execution")
    search_result = registry.execute("search", query="AI agents", max_results=3)
    
    if search_result.status == ToolStatus.SUCCESS:
        print(f"   Found {len(search_result.output)} results")
        for result in search_result.output:
            print(f"   - {result['title']} (relevance: {result['relevance']:.2f})")
    
    # Example 2: Tool with error handling
    print("\n📌 Example 2: Error Handling")
    # This will fail because we're passing invalid parameters
    invalid_result = registry.execute("analyze", text=None, analysis_type="summary")
    
    # Example 3: Tool chain execution
    print("\n📌 Example 3: Tool Chain Execution")
    chain = ToolChain(registry)
    
    # Define a chain: search -> analyze -> format
    chain_steps = [
        {
            "tool": "search",
            "params": {"query": "tool integration patterns", "max_results": 2}
        },
        {
            "tool": "analyze",
            "params": {"text": "Analyzing search results", "analysis_type": "entities"},
            "use_previous_output": False  # Don't use search output directly
        },
        {
            "tool": "format",
            "params": {"format_type": "markdown"},
            "use_previous_output": True  # Use analysis output
        }
    ]
    
    chain_result = chain.execute_chain(chain_steps)
    
    if chain_result["status"] == "success":
        print(f"\n✅ Chain completed successfully!")
        print(f"   Total time: {chain_result['total_time_ms']:.2f}ms")
        print(f"   Final output:\n{chain_result['final_output']}")
    
    # Display statistics
    print("\n📊 Tool Usage Statistics")
    print("-" * 40)
    stats = registry.get_statistics()
    print(f"Total executions: {stats['total_executions']}")
    
    for tool_name, tool_stats in stats["tools"].items():
        print(f"\n{tool_name}:")
        print(f"  Calls: {tool_stats['calls']}")
        print(f"  Success rate: {tool_stats['success_rate']}")
        print(f"  Avg time: {tool_stats['avg_time_ms']}ms")
    
    # Example 4: Parallel tool execution simulation
    print("\n📌 Example 4: Parallel Tool Execution (Simulated)")
    print("   Executing multiple searches in parallel...")
    
    queries = ["AI safety", "agent architectures", "tool integration"]
    parallel_start = time.time()
    
    # In a real implementation, these would run in parallel
    parallel_results = []
    for query in queries:
        result = registry.execute("search", query=query, max_results=2)
        parallel_results.append(result)
    
    parallel_time = (time.time() - parallel_start) * 1000
    print(f"   Completed {len(queries)} searches in {parallel_time:.2f}ms")
    
    print("\n✨ Demonstration Complete!")
    print("\nKey Takeaways:")
    print("- Tools can be registered and tracked for performance")
    print("- Tool chains enable complex workflows")
    print("- Error handling ensures robustness")
    print("- Statistics help optimize tool usage")
    print("- Parallel execution improves performance")


if __name__ == "__main__":
    demonstrate_tool_integration()
