"""
Exception Handling Example

This example demonstrates how the AgentOps context manager handles
different types of exceptions while ensuring proper cleanup.
"""

import os

import agentops
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")


# Define agent class inline for standalone example
@agentops.agent
class ExampleAgent:
    """A simple example agent for demonstrating AgentOps functionality."""

    def __init__(self, name: str):
        self.name = name
        print(f"🤖 Created agent: {self.name}")

    @agentops.task
    def process_data(self, data: str) -> str:
        """Process some data with the agent."""
        print(f"📊 {self.name} processing: {data}")
        result = f"Processed: {data}"

        # Use a tool as part of processing
        tool_result = self.use_tool(result)
        return tool_result

    @agentops.tool
    def use_tool(self, input_data: str) -> str:
        """Use a tool to transform data."""
        print(f"🔧 {self.name} using tool on: {input_data}")
        return f"Tool output: {input_data.upper()}"

    @agentops.task
    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text."""
        print(f"💭 {self.name} analyzing sentiment: {text}")
        # Simple mock sentiment analysis
        if "good" in text.lower() or "great" in text.lower():
            return "positive"
        elif "bad" in text.lower() or "terrible" in text.lower():
            return "negative"
        else:
            return "neutral"

    @agentops.tool
    def fetch_data(self, source: str) -> str:
        """Simulate fetching data from a source."""
        print(f"📡 {self.name} fetching data from: {source}")
        return f"Data from {source}: [mock data]"


def span_recording_error_example():
    """Example of handling span recording errors."""
    print("🧪 Scenario 1: Span Recording Error")
    print("-" * 40)

    try:
        with agentops.init(
            api_key=AGENTOPS_API_KEY,
            trace_name="span_error_test",
            auto_start_session=False,
            default_tags=["error-test", "span"],
        ):
            print("✅ Context manager entered")

            # Create agent and do some work
            agent = ExampleAgent("ErrorTestAgent")
            result = agent.process_data("test data")
            print(f"📊 Processing completed: {result}")

            # Simulate a span recording error (this would be internal to AgentOps)
            # In real scenarios, this might be a network error, API failure, etc.
            print("⚠️  Simulating span recording error...")
            raise ConnectionError("Failed to record span to AgentOps API")

    except ConnectionError as e:
        print(f"❌ Caught span error: {e}")
        print("✅ Context manager properly cleaned up trace")

    print("✅ Scenario 1 completed\n")


def agent_error_example():
    """Example of handling agent-related errors."""
    print("🧪 Scenario 2: Agent Error (LLM API Failure)")
    print("-" * 45)

    try:
        with agentops.init(
            api_key=AGENTOPS_API_KEY,
            trace_name="agent_error_test",
            auto_start_session=False,
            default_tags=["error-test", "agent"],
        ):
            print("✅ Context manager entered")

            # Create agent
            agent = ExampleAgent("LLMAgent")

            # Simulate successful operations first
            result1 = agent.process_data("initial data")
            print(f"📊 First operation: {result1}")

            # Simulate LLM API failure
            print("⚠️  Simulating LLM API failure...")
            raise ConnectionError("OpenAI API is temporarily unavailable")

    except ConnectionError as e:
        print(f"❌ Caught agent error: {e}")
        print("✅ Context manager properly cleaned up trace")
        print("💡 All successful operations before error are preserved")

    print("✅ Scenario 2 completed\n")


def unrelated_error_example():
    """Example of handling unrelated application errors."""
    print("🧪 Scenario 3: Unrelated Application Error")
    print("-" * 45)

    try:
        with agentops.init(
            api_key=AGENTOPS_API_KEY,
            trace_name="app_error_test",
            auto_start_session=False,
            default_tags=["error-test", "application"],
        ):
            print("✅ Context manager entered")

            # Create agent and do successful work
            agent = ExampleAgent("AppAgent")
            result1 = agent.process_data("business data")
            sentiment = agent.analyze_sentiment("This is working great!")

            print(f"📊 Processing: {result1}")
            print(f"💭 Sentiment: {sentiment}")

            # Simulate unrelated application error
            print("⚠️  Simulating unrelated application error...")
            result = 10 / 0  # ZeroDivisionError    # noqa: F841

    except ZeroDivisionError as e:
        print(f"❌ Caught application error: {e}")
        print("✅ Context manager properly cleaned up trace")
        print("💡 All AgentOps data recorded before error is preserved")

    print("✅ Scenario 3 completed\n")


def nested_exception_example():
    """Example of nested operations with exceptions."""
    print("🧪 Scenario 4: Nested Operations with Exception")
    print("-" * 50)

    try:
        with agentops.init(
            api_key=AGENTOPS_API_KEY,
            trace_name="nested_error_test",
            auto_start_session=False,
            default_tags=["error-test", "nested"],
        ):
            print("✅ Outer context started")

            agent = ExampleAgent("NestedAgent")

            # First level of operations
            result1 = agent.process_data("level 1 data")
            print(f"📊 Level 1: {result1}")

            # Nested operation that fails
            try:
                print("🔄 Starting nested operation...")
                agent.fetch_data("unreliable_source")

                # This nested operation fails
                raise TimeoutError("Data source timeout")

            except TimeoutError as nested_error:
                print(f"⚠️  Nested operation failed: {nested_error}")
                print("🔄 Continuing with fallback...")

                # Fallback operation
                fallback_data = agent.fetch_data("backup_source")
                print(f"📡 Fallback successful: {fallback_data}")

            # Continue with main flow
            final_result = agent.analyze_sentiment("Overall this worked well")
            print(f"💭 Final analysis: {final_result}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print("✅ Scenario 4 completed - nested errors handled gracefully\n")


def exception_propagation_example():
    """Example showing that exceptions are properly propagated."""
    print("🧪 Scenario 5: Exception Propagation Test")
    print("-" * 45)

    exception_was_caught = False

    try:
        with agentops.init(
            api_key=AGENTOPS_API_KEY,
            trace_name="propagation_test",
            auto_start_session=False,
            default_tags=["error-test", "propagation"],
        ):
            print("✅ Context manager entered")

            agent = ExampleAgent("PropagationAgent")
            agent.process_data("test data")

            # Raise an exception that should propagate
            raise ValueError("This exception should NOT be suppressed")

    except ValueError as e:
        exception_was_caught = True
        print(f"✅ Exception properly propagated: {e}")

    if exception_was_caught:
        print("✅ Context manager does NOT suppress exceptions")
    else:
        print("❌ Context manager incorrectly suppressed exception")

    print("✅ Scenario 5 completed\n")


if __name__ == "__main__":
    print("🚀 AgentOps Exception Handling Examples")
    print("=" * 50)

    try:
        # Test different exception scenarios
        span_recording_error_example()
        agent_error_example()
        unrelated_error_example()
        nested_exception_example()
        exception_propagation_example()

        print("=" * 50)
        print("✅ All exception handling examples completed!")
        print("\n🔒 Key Guarantees:")
        print("  • Traces are ALWAYS cleaned up, even with exceptions")
        print("  • Exceptions are NEVER suppressed")
        print("  • Error state is properly recorded for debugging")
        print("  • All data recorded before errors is preserved")
        print("  • Nested error handling works correctly")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()
