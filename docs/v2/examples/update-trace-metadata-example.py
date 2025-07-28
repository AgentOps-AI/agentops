"""
Example: Using update_trace_metadata to track AI agent workflow progress
"""

import agentops
from datetime import datetime
import time
import random

# Initialize AgentOps
agentops.init(auto_start_session=False)

def simulate_llm_call(prompt, model="gpt-4"):
    """Simulate an LLM API call"""
    time.sleep(0.5)  # Simulate latency
    return f"Response to: {prompt[:50]}..."

def ai_agent_workflow(user_query):
    """
    Example AI agent workflow that demonstrates update_trace_metadata usage
    """
    # Start a new trace
    trace = agentops.start_trace(
        "ai-agent-workflow",
        tags=["example", "tutorial", "metadata-demo"]
    )
    
    try:
        # Step 1: Initialize and log initial metadata
        agentops.update_trace_metadata({
            "operation_name": "AI Agent Query Processing",
            "user_query": user_query,
            "workflow_version": "1.0.0",
            "environment": "development",
            "start_time": datetime.now().isoformat()
        })
        
        # Step 2: Query Understanding Phase
        print("🤔 Understanding query...")
        agentops.update_trace_metadata({
            "current_phase": "query_understanding",
            "status": "processing"
        })
        
        # Simulate query classification
        query_intent = "information_request" if "?" in user_query else "action_request"
        confidence = random.uniform(0.85, 0.99)
        
        agentops.update_trace_metadata({
            "query_intent": query_intent,
            "intent_confidence": round(confidence, 3),
            "tags": ["classified", query_intent]
        })
        
        # Step 3: Generate Response
        print("💭 Generating response...")
        agentops.update_trace_metadata({
            "current_phase": "response_generation",
            "llm_model": "gpt-4",
            "temperature": 0.7
        })
        
        start_gen = time.time()
        response = simulate_llm_call(user_query)
        generation_time = round((time.time() - start_gen) * 1000, 2)
        
        agentops.update_trace_metadata({
            "response_generated": True,
            "generation_time_ms": generation_time,
            "response_length": len(response),
            "tokens_used": len(response.split())  # Simplified token count
        })
        
        # Step 4: Quality Assessment
        print("✅ Assessing quality...")
        quality_score = random.uniform(0.8, 0.95)
        
        agentops.update_trace_metadata({
            "current_phase": "quality_assessment",
            "quality_score": round(quality_score, 3),
            "quality_threshold_met": quality_score > 0.85
        })
        
        # Step 5: Finalize
        total_duration = random.uniform(1000, 2000)
        
        agentops.update_trace_metadata({
            "operation_name": "AI Agent Query Completed",
            "current_phase": "completed",
            "status": "success",
            "total_duration_ms": round(total_duration, 2),
            "end_time": datetime.now().isoformat(),
            "tags": ["completed", "success", f"quality:{round(quality_score, 2)}"]
        })
        
        print(f"✨ Workflow completed successfully!")
        print(f"   Response: {response}")
        print(f"   Quality Score: {round(quality_score, 3)}")
        print(f"   Duration: {round(total_duration, 2)}ms")
        
        # End the trace successfully
        agentops.end_trace(trace, "Success")
        
        return response
        
    except Exception as e:
        # Handle errors and update metadata accordingly
        agentops.update_trace_metadata({
            "current_phase": "error",
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "tags": ["error", "failed"]
        })
        
        print(f"❌ Error occurred: {e}")
        agentops.end_trace(trace, "Error")
        raise

# Example usage
if __name__ == "__main__":
    print("🚀 Starting AI Agent Workflow Example\n")
    
    # Process a user query
    user_query = "What are the benefits of using AgentOps for monitoring AI agents?"
    result = ai_agent_workflow(user_query)
    
    print("\n✅ Example completed! Check your AgentOps dashboard to see the trace with metadata.")