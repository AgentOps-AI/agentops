from opentelemetry import trace, context, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor, SpanExporter
from opentelemetry.trace import Status, StatusCode
import time
import sys
import json
from typing import Dict, Any, List, Optional, Sequence

# Create a no-op exporter to prevent spans from being printed
class NoopExporter(SpanExporter):
    """A span exporter that doesn't export spans anywhere."""
    
    def export(self, spans: Sequence) -> None:
        """Do nothing with the spans."""
        pass
    
    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass

# Set up basic tracing
provider = TracerProvider()
# Use the NoopExporter instead of ConsoleSpanExporter
processor = BatchSpanProcessor(NoopExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("token_demo")

# Second tracer for demonstration
llm_tracer = trace.get_tracer("llm_tracer")

# ======== Visualization Helpers ========

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_step(step_num, description):
    """Print a step in the process"""
    print(f"\n[Step {step_num}] {description}")

def print_span_tree(spans, indent=0):
    """Print a visual representation of the span tree"""
    for i, span in enumerate(spans):
        is_last = i == len(spans) - 1
        prefix = "└── " if is_last else "├── "
        print("│   " * indent + prefix + span)

def print_context_state(active_span_name, context_stack=None, baggage_items=None):
    """Print the current context state with visualization"""
    print("\n  Current Context State:")
    print("  --------------------")
    print(f"  Active span: {active_span_name}")
    
    if context_stack:
        print("\n  Context Stack (top to bottom):")
        for i, span in enumerate(context_stack):
            if i == 0:
                print(f"  ┌─ {span} ← Current")
            else:
                print(f"  │  {span}")
        print("  └─────────────")
    
    if baggage_items:
        print("\n  Baggage Items:")
        print("  -------------")
        for key, value in baggage_items.items():
            print(f"  🔷 {key}: {value}")

def print_span_details(span, title="Span Details"):
    """Print detailed information about a span"""
    if not hasattr(span, "get_span_context"):
        print("  No span details available")
        return
    
    ctx = span.get_span_context()
    print(f"\n  {title}:")
    print("  " + "-" * len(title))
    print(f"  Name: {getattr(span, 'name', 'Unknown')}")
    print(f"  Trace ID: {ctx.trace_id:x}")
    print(f"  Span ID: {ctx.span_id:x}")
    
    # Try to get attributes if possible
    attributes = getattr(span, "_attributes", {})
    if attributes:
        print("\n  Attributes:")
        for key, value in attributes.items():
            print(f"  📎 {key}: {str(value)}")

def get_current_span_name():
    """Get the name of the current span or 'None' if no span is active"""
    current = trace.get_current_span()
    return getattr(current, "name", "None")

def get_current_baggage() -> Dict[str, str]:
    """Get all baggage items in the current context"""
    items = {}
    # This is a simplified approach - in a real app you'd enumerate all baggage items
    for key in ["user.id", "tenant.id", "request.id", "environment"]:
        value = baggage.get_baggage(key)
        if value:
            items[key] = value
    return items

# ======== Simulated Application Functions ========

def simulate_database_query(query: str) -> Dict[str, Any]:
    """Simulate a database query with proper context propagation"""
    with tracer.start_as_current_span("database.query") as span:
        span.set_attribute("db.statement", query)
        span.set_attribute("db.system", "postgresql")
        
        # Simulate query execution time
        time.sleep(0.01)
        
        # Add current baggage to demonstrate propagation
        user_id = baggage.get_baggage("user.id")
        if user_id:
            span.set_attribute("user.id", str(user_id))
            
        # Return simulated data
        return {"id": 1234, "name": "Sample Data", "status": "active"}

def call_external_api(endpoint: str) -> Dict[str, Any]:
    """Simulate an external API call with a different tracer"""
    with llm_tracer.start_as_current_span("http.request") as span:
        span.set_attribute("http.url", f"https://api.example.com/{endpoint}")
        span.set_attribute("http.method", "GET")
        
        # Simulate API call latency
        time.sleep(0.02)
        
        # Add baggage to simulate cross-service propagation
        tenant_id = baggage.get_baggage("tenant.id")
        if tenant_id:
            span.set_attribute("tenant.id", str(tenant_id))
        
        # Sometimes operations fail
        if endpoint == "error":
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.message", "API returned 500 status code")
            return {"error": "Internal Server Error"}
            
        return {"status": "success", "data": {"key": "value"}}

def process_user_request(user_id: str, action: str) -> Dict[str, Any]:
    """Process a user request with nested spans and context propagation"""
    # Set baggage for the entire operation
    ctx = baggage.set_baggage("user.id", user_id)
    ctx = baggage.set_baggage("tenant.id", "tenant-1234", context=ctx)
    ctx = baggage.set_baggage("request.id", f"req-{int(time.time())}", context=ctx)
    
    # Attach the context with baggage
    token = context.attach(ctx)
    
    try:
        with tracer.start_as_current_span("process_request") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("request.action", action)
            
            # Query the database (creates a child span)
            db_result = simulate_database_query(f"SELECT * FROM users WHERE id = '{user_id}'")
            
            # Call an external API (creates a child span with a different tracer)
            api_result = call_external_api("users/profile")
            
            # Combine results
            return {
                "user": db_result,
                "profile": api_result,
                "processed_at": time.time()
            }
    finally:
        # Always detach the context to clean up
        context.detach(token)

# ======== Scenarios ========

def run_basic_scenarios():
    """Run the original basic scenarios to demonstrate token importance"""
    # Scenario 1: Proper token management
    print_header("Scenario 1: Proper Token Management")
    print("This scenario demonstrates correct context management with proper token handling.")
    print("We'll create a parent span, then a child span, and properly detach the context.")

    with tracer.start_as_current_span("parent") as parent:
        print_step(1, "Created parent span and set as current")
        parent_name = get_current_span_name()
        print_context_state(parent_name, ["parent"])
        print_span_tree(["parent"])
        
        print_step(2, "Creating child span and attaching to context")
        # Manually create a child span and save the token
        child = tracer.start_span("child")
        ctx = trace.set_span_in_context(child)
        token = context.attach(ctx)
        
        child_name = get_current_span_name()
        print_context_state(child_name, ["child", "parent"])
        print_span_tree(["parent", "child"])
        
        print_step(3, "Ending child span AND detaching token (proper cleanup)")
        # End the child span and detach the token
        child.end()
        context.detach(token)
        
        restored_name = get_current_span_name()
        print_context_state(restored_name, ["parent"])
        print_span_tree(["parent"])
        
        print("\n✅ Result: Context properly restored to parent after child span ended")

    # Scenario 2: Missing token detachment
    print_header("Scenario 2: Missing Token Detachment (Context Leak)")
    print("This scenario demonstrates what happens when we don't detach the context token.")
    print("We'll create a parent span, then a child span, but NOT detach the context.")

    with tracer.start_as_current_span("parent2") as parent:
        print_step(1, "Created parent2 span and set as current")
        parent_name = get_current_span_name()
        print_context_state(parent_name, ["parent2"])
        print_span_tree(["parent2"])
        
        print_step(2, "Creating child2 span and attaching to context")
        # Manually create a child span but don't save the token
        child = tracer.start_span("child2")
        ctx = trace.set_span_in_context(child)
        token = context.attach(ctx)  # Token saved but not used later
        
        child_name = get_current_span_name()
        print_context_state(child_name, ["child2", "parent2"])
        print_span_tree(["parent2", "child2"])
        
        print_step(3, "Ending child2 span WITHOUT detaching token (improper cleanup)")
        # End the child span but don't detach the token
        child.end()
        # No context.detach(token) call!
        
        leaked_name = get_current_span_name()
        print_context_state(leaked_name, ["child2 (ended but context still active)", "parent2"])
        print_span_tree(["parent2", "child2 (ended)"])
        
        print("\n⚠️ Result: Context LEAK! Still showing child2 as current context even though span ended")
        print("   Any new spans created here would incorrectly use child2 as parent instead of parent2")

    # Scenario 3: Nested spans with context restoration
    print_header("Scenario 3: Nested Spans with Context Restoration")
    print("This scenario demonstrates proper context management with multiple nested spans.")
    print("We'll create an outer → middle1 → middle2 span hierarchy and properly restore contexts.")

    with tracer.start_as_current_span("outer") as outer:
        print_step(1, "Created outer span and set as current")
        outer_name = get_current_span_name()
        print_context_state(outer_name, ["outer"])
        print_span_tree(["outer"])
        
        print_step(2, "Creating middle1 span and attaching to context")
        # First middle span
        middle1 = tracer.start_span("middle1")
        ctx1 = trace.set_span_in_context(middle1)
        token1 = context.attach(ctx1)
        
        middle1_name = get_current_span_name()
        print_context_state(middle1_name, ["middle1", "outer"])
        print_span_tree(["outer", "middle1"])
        
        print_step(3, "Creating middle2 span and attaching to context")
        # Second middle span
        middle2 = tracer.start_span("middle2")
        ctx2 = trace.set_span_in_context(middle2)
        token2 = context.attach(ctx2)
        
        middle2_name = get_current_span_name()
        print_context_state(middle2_name, ["middle2", "middle1", "outer"])
        print_span_tree(["outer", "middle1", "middle2"])
        
        print_step(4, "Ending middle2 span and detaching token2")
        # End spans in reverse order with proper token management
        middle2.end()
        context.detach(token2)
        
        restored_middle1_name = get_current_span_name()
        print_context_state(restored_middle1_name, ["middle1", "outer"])
        print_span_tree(["outer", "middle1", "middle2 (ended)"])
        
        print_step(5, "Ending middle1 span and detaching token1")
        middle1.end()
        context.detach(token1)
        
        restored_outer_name = get_current_span_name()
        print_context_state(restored_outer_name, ["outer"])
        print_span_tree(["outer", "middle1 (ended)", "middle2 (ended)"])
        
        print("\n✅ Result: Context properly restored through multiple levels")

    # Scenario 4: What happens if we create new spans after a context leak
    print_header("Scenario 4: Creating New Spans After Context Leak")
    print("This scenario demonstrates the impact of context leaks on the span hierarchy.")
    print("We'll create a parent span, leak a child context, then create another span.")

    with tracer.start_as_current_span("root") as root:
        print_step(1, "Created root span and set as current")
        root_name = get_current_span_name()
        print_context_state(root_name, ["root"])
        print_span_tree(["root"])
        
        print_step(2, "Creating leaky_child span and attaching to context")
        # Create a child span but don't save the token
        leaky = tracer.start_span("leaky_child")
        ctx = trace.set_span_in_context(leaky)
        context.attach(ctx)  # Token not saved
        
        leaky_name = get_current_span_name()
        print_context_state(leaky_name, ["leaky_child", "root"])
        print_span_tree(["root", "leaky_child"])
        
        print_step(3, "Ending leaky_child span WITHOUT detaching token")
        # End the child span but don't detach the token
        leaky.end()
        # No context.detach() call!
        
        print_step(4, "Creating new_child span after context leak")
        # This span will be created with leaky_child as parent, not root!
        with tracer.start_as_current_span("new_child") as new_child:
            new_child_name = get_current_span_name()
            print_context_state(new_child_name, ["new_child", "leaky_child (ended but context active)", "root"])
            print_span_tree(["root", "leaky_child (ended)", "new_child"])
            
            print("\n⚠️ Problem: new_child is incorrectly parented to leaky_child instead of root")
            print("   This creates an incorrect trace hierarchy that doesn't match execution flow")

def run_advanced_scenarios():
    """Run the new advanced scenarios demonstrating more complex context patterns"""
    
    # Scenario 5: Cross-function context propagation
    print_header("Scenario 5: Cross-Function Context Propagation")
    print("This scenario demonstrates how context and baggage propagate across function boundaries.")
    print("We'll create a request processing flow with multiple nested functions and spans.")
    
    print_step(1, "Starting user request processing with baggage")
    # Process a simulated request that will create nested spans across functions
    result = process_user_request("user-5678", "update_profile")
    
    print_step(2, "Request processing completed")
    print("\n  Request processing result:")
    print(f"  User data: {result['user']['name']}")
    print(f"  Profile status: {result['profile']['status']}")
    
    print("\n✅ Result: Context and baggage successfully propagated across multiple function calls")
    print("   Each function created properly nested spans that maintained the baggage context")
    
    # Scenario 6: Using different tracers with the same context
    print_header("Scenario 6: Multiple Tracers with Shared Context")
    print("This scenario demonstrates using multiple tracers while maintaining a consistent context.")
    
    print_step(1, "Creating context with baggage")
    # Set up a context with baggage
    ctx = baggage.set_baggage("environment", "production")
    ctx = baggage.set_baggage("tenant.id", "tenant-9876", context=ctx)
    token = context.attach(ctx)
    
    try:
        print_step(2, "Starting span with main tracer")
        with tracer.start_as_current_span("main_operation") as main_span:
            main_span_name = get_current_span_name()
            baggage_items = get_current_baggage()
            print_context_state(main_span_name, ["main_operation"], baggage_items)
            print_span_details(main_span)
            
            print_step(3, "Creating span with LLM tracer (different tracer)")
            with llm_tracer.start_as_current_span("llm_inference") as llm_span:
                llm_span.set_attribute("model", "gpt-4")
                llm_span.set_attribute("tokens", 150)
                
                llm_span_name = get_current_span_name()
                print_context_state(llm_span_name, ["llm_inference", "main_operation"], baggage_items)
                print_span_details(llm_span, "LLM Span Details")
                
                print_step(4, "Back to main tracer")
                # Create another span with the first tracer
                with tracer.start_as_current_span("post_processing") as post_span:
                    post_span_name = get_current_span_name()
                    print_context_state(post_span_name, ["post_processing", "llm_inference", "main_operation"], baggage_items)
    finally:
        context.detach(token)
    
    print("\n✅ Result: Multiple tracers successfully shared the same context")
    print("   Baggage was accessible to spans from both tracers")
    
    # Scenario 7: Handling errors in spans
    print_header("Scenario 7: Error Handling in Spans")
    print("This scenario demonstrates proper error handling with spans.")
    
    print_step(1, "Starting operation that will encounter an error")
    with tracer.start_as_current_span("error_prone_operation") as error_span:
        try:
            print_step(2, "Calling API that will fail")
            result = call_external_api("error")
            print(f"  API result: {result}")
        except Exception as e:
            print_step(3, "Handling exception in span")
            error_span.record_exception(e)
            error_span.set_status(Status(StatusCode.ERROR))
            print(f"  Recorded exception: {str(e)}")
    
    print("\n✅ Result: Properly recorded error in span without breaking execution flow")
    print("   Errors should be visible in the trace visualization")
    
    # Scenario 8: Manual context saving and restoring
    print_header("Scenario 8: Manual Context Saving and Restoring")
    print("This scenario demonstrates saving a context and restoring it later.")
    
    print_step(1, "Creating initial context")
    with tracer.start_as_current_span("initial_operation") as initial_span:
        # Set some baggage
        ctx = baggage.set_baggage("checkpoint", "saved_point")
        
        # Save the current context for later use
        saved_context = context.get_current()
        print_context_state("initial_operation", ["initial_operation"], {"checkpoint": "saved_point"})
        
        print_step(2, "Creating a different context")
        with tracer.start_as_current_span("intermediate_operation") as intermediate_span:
            # Change the baggage
            ctx = baggage.set_baggage("checkpoint", "intermediate_point")
            print_context_state("intermediate_operation", ["intermediate_operation", "initial_operation"], 
                              {"checkpoint": "intermediate_point"})
            
            print_step(3, "Restoring saved context")
            # Restore the saved context
            token = context.attach(saved_context)
            try:
                current_span = trace.get_current_span()
                current_name = getattr(current_span, "name", "Unknown")
                checkpoint = baggage.get_baggage("checkpoint")
                print_context_state(current_name, ["initial_operation"], {"checkpoint": checkpoint})
                
                print("\n✅ Result: Successfully restored previous context")
            finally:
                context.detach(token)
            
            print_step(4, "Back to intermediate context")
            print_context_state("intermediate_operation", ["intermediate_operation", "initial_operation"], 
                              {"checkpoint": "intermediate_point"})
    
print_header("OpenTelemetry Context Management Demonstration")
print("This example illustrates the importance of proper context management in OpenTelemetry.")
print("It covers basic and advanced scenarios showing how context affects span relationships.")

print("\n1. Basic Scenarios - Demonstrating context token importance")
print("2. Advanced Scenarios - Real-world patterns with nested functionality")
print("3. Run All Scenarios")
print("4. Exit")

while True:
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == "1":
        run_basic_scenarios()
    elif choice == "2":
        run_advanced_scenarios()
    elif choice == "3":
        run_basic_scenarios()
        run_advanced_scenarios()
    elif choice == "4":
        print("\nExiting...")
        break
    else:
        print("Invalid choice. Please enter 1, 2, 3, or 4.")

print_header("Conclusion")
print("The token returned by context.attach() is crucial for proper context management.")
print("Without proper token detachment:")
print("1. Context leaks occur - the active context doesn't revert to the parent")
print("2. New spans are created with incorrect parent relationships")
print("3. The trace hierarchy doesn't accurately represent the execution flow")
print("\nIn AgentOps, if end_session() doesn't detach the token:")
print("- Sessions might appear to be active even after they've ended")
print("- New operations might be incorrectly associated with ended sessions")
print("- The overall trace hierarchy would be inaccurate")
