from opentelemetry import trace, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

# Set up tracing
provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("demo")

def get_current_span_name():
    return getattr(trace.get_current_span(), "name", "None")

print("\n=== Scenario: Multiple contexts with the same span ===")
print("This demonstrates why coupling spans and tokens can be problematic")

# Create a span that we'll use in multiple contexts
shared_span = tracer.start_span("shared_span")
print(f"Created shared_span (not in any context yet): {shared_span.name}")

# Create context A with the shared span
ctx_a = trace.set_span_in_context(shared_span)
token_a = context.attach(ctx_a)
print(f"Current span after attaching context A: {get_current_span_name()}")

# Save context A state
first_context_span = trace.get_current_span()

# Create context B with the same shared span
# If span and token were coupled, this would detach context A!
ctx_b = trace.set_span_in_context(shared_span)
token_b = context.attach(ctx_b)
print(f"Current span after attaching context B: {get_current_span_name()}")

# Now detach context B
context.detach(token_b)
print(f"Current span after detaching context B: {get_current_span_name()}")

# Detach context A
context.detach(token_a)
print(f"Current span after detaching context A: {get_current_span_name()}")

# End the shared span once - if we did this twice with coupled tokens, it would error
shared_span.end()
print("Ended shared_span once")

print("\nIf spans and tokens were coupled:")
print("1. Creating context B would have implicitly detached context A")
print("2. We couldn't use the same span in two different trace contexts")
print("3. Ending the span would have also detached all contexts using it")
