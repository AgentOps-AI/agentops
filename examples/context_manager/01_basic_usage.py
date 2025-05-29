"""
Basic Context Manager Usage Example

This example demonstrates the fundamental usage of AgentOps context manager
and compares it with the traditional approach.
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


def traditional_approach():
    """Example of traditional AgentOps usage."""
    print("🔄 Traditional Approach:")
    print("-" * 30)

    # Traditional initialization
    agentops.init(api_key=AGENTOPS_API_KEY, auto_start_session=True, default_tags=["traditional", "example"])

    if AGENTOPS_API_KEY:
        print("✅ Session started manually")

        # Create and use agent
        agent = ExampleAgent("TraditionalAgent")
        result = agent.process_data("traditional data")
        print(f"📤 Result: {result}")

        # Manually end session
        agentops.end_session()
        print("✅ Session ended manually")
    else:
        print("❌ Failed to start session")


def context_manager_approach():
    """Example of context manager usage."""
    print("\n🆕 Context Manager Approach:")
    print("-" * 35)

    # Context manager automatically handles session lifecycle
    with agentops.init(
        api_key=AGENTOPS_API_KEY,
        auto_start_session=False,  # Let context manager handle it
        trace_name="basic_example",
        default_tags=["context-manager", "example"],
    ):
        print("✅ Session started automatically")

        # Create and use agent
        agent = ExampleAgent("ContextAgent")
        result = agent.process_data("context manager data")
        print(f"📤 Result: {result}")

        # Session will be ended automatically when exiting the 'with' block

    print("✅ Session ended automatically")


def multiple_operations_example():
    """Example showing multiple operations within a single context."""
    print("\n🔄 Multiple Operations in One Context:")
    print("-" * 40)

    with agentops.init(
        api_key=AGENTOPS_API_KEY,
        trace_name="multi_operations",
        auto_start_session=False,
        default_tags=["multi-ops", "example"],
    ):
        print("✅ Context started")

        # Create agent
        agent = ExampleAgent("MultiOpAgent")

        # Perform multiple operations
        print("\n📊 Operation 1: Data Processing")
        result1 = agent.process_data("first dataset")

        print("\n💭 Operation 2: Sentiment Analysis")
        sentiment = agent.analyze_sentiment("This is a great example!")

        print("\n📡 Operation 3: Data Fetching")
        data = agent.fetch_data("external_api")

        print("\n📋 Summary:")
        print(f"  - Processing result: {result1}")
        print(f"  - Sentiment: {sentiment}")
        print(f"  - Fetched data: {data}")

    print("✅ All operations completed, context ended")


if __name__ == "__main__":
    print("🚀 AgentOps Basic Context Manager Usage")
    print("=" * 50)

    try:
        # Show traditional approach
        traditional_approach()

        # Show context manager approach
        context_manager_approach()

        # Show multiple operations
        multiple_operations_example()

        print("\n" + "=" * 50)
        print("✅ Basic usage examples completed!")
        print("\n💡 Key Takeaways:")
        print("  • Context manager automatically handles session lifecycle")
        print("  • No need to manually call end_session()")
        print("  • Clear scope definition for operations")
        print("  • Same functionality as traditional approach")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()
