from opentelemetry import trace, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
import time
import sys

# Set up basic tracing
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()
tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
tracer = trace.get_tracer("token_demo")

# ASCII art helpers for visualization
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

def print_context_state(active_span_name, context_stack=None):
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

def get_current_span_name():
    """Get the name of the current span or 'None' if no span is active"""
    current = trace.get_current_span()
    return getattr(current, "name", "None")

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
