"""
Backward Compatibility Example

This example demonstrates that existing AgentOps code continues to work
unchanged with the new context manager implementation.
"""

import os

import agentops
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")


# Define agent class inline for standalone example
@agentops.agent
class BackwardCompatibilityAgent:
    """Example agent for backward compatibility demonstration."""

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


def legacy_session_management():
    """Example of legacy session management - still works!"""
    print("🔄 Legacy Session Management:")
    print("-" * 35)

    # Traditional initialization - exactly as before
    session = agentops.init(
        api_key=AGENTOPS_API_KEY, auto_start_session=True, default_tags=["legacy", "backward-compatibility"]
    )

    if session:
        print("✅ Session started using legacy approach")

        # Create and use agent - exactly as before
        agent = BackwardCompatibilityAgent("LegacyAgent")
        result = agent.process_data("legacy data")
        print(f"📤 Result: {result}")

        # Manually end session - exactly as before
        agentops.end_session()
        print("✅ Session ended using legacy approach")
    else:
        print("❌ Failed to start session")


def legacy_start_session_api():
    """Example using the legacy start_session API."""
    print("\n🔄 Legacy start_session API:")
    print("-" * 35)

    # Using the old start_session function
    session = agentops.start_session(api_key=AGENTOPS_API_KEY, tags=["legacy-api", "start-session"])

    if session:
        print("✅ Session started using start_session()")

        agent = BackwardCompatibilityAgent("StartSessionAgent")
        result = agent.analyze_sentiment("This legacy API still works great!")
        print(f"💭 Sentiment: {result}")

        # End using legacy API
        agentops.end_session()
        print("✅ Session ended using end_session()")
    else:
        print("❌ Failed to start session with start_session()")


def mixed_usage_example():
    """Example showing mixed usage of old and new approaches."""
    print("\n🔄 Mixed Usage Example:")
    print("-" * 30)

    # Start with legacy approach
    session = agentops.init(api_key=AGENTOPS_API_KEY, auto_start_session=True, default_tags=["mixed", "legacy-start"])

    if session:
        print("✅ Started with legacy init()")

        agent = BackwardCompatibilityAgent("MixedAgent")
        result1 = agent.process_data("initial data")
        print(f"📊 Legacy result: {result1}")

        # End legacy session
        agentops.end_session()
        print("✅ Ended legacy session")

        # Now use new context manager approach
        print("\n🆕 Switching to context manager:")
        with agentops.init(
            api_key=AGENTOPS_API_KEY,
            trace_name="mixed_context",
            auto_start_session=False,
            default_tags=["mixed", "context-manager"],
        ):
            print("✅ Started with context manager")

            agent2 = BackwardCompatibilityAgent("ContextAgent")
            result2 = agent2.analyze_sentiment("Context managers are awesome!")
            print(f"💭 Context result: {result2}")

        print("✅ Context manager session ended automatically")


def legacy_decorators_example():
    """Example showing legacy decorator usage still works."""
    print("\n🔄 Legacy Decorators Example:")
    print("-" * 35)

    # Define functions with legacy decorators
    @agentops.session
    def legacy_session_function():
        """Function decorated with @session - still works!"""
        print("✅ Inside @session decorated function")

        agent = BackwardCompatibilityAgent("SessionDecoratorAgent")
        return agent.process_data("session decorator data")

    @agentops.trace
    def legacy_trace_function():
        """Function decorated with @trace - still works!"""
        print("✅ Inside @trace decorated function")

        agent = BackwardCompatibilityAgent("TraceDecoratorAgent")
        return agent.analyze_sentiment("Trace decorators work perfectly!")

    # Initialize AgentOps first
    agentops.init(api_key=AGENTOPS_API_KEY)

    # Use legacy decorators
    result1 = legacy_session_function()
    print(f"📊 Session decorator result: {result1}")

    result2 = legacy_trace_function()
    print(f"💭 Trace decorator result: {result2}")


def legacy_manual_trace_management():
    """Example of manual trace management - advanced legacy usage."""
    print("\n🔄 Legacy Manual Trace Management:")
    print("-" * 40)

    # Initialize without auto-start
    agentops.init(api_key=AGENTOPS_API_KEY, auto_start_session=False)

    # Manually start trace
    trace_context = agentops.start_trace(trace_name="manual_legacy_trace", tags=["manual", "legacy", "advanced"])

    if trace_context:
        print("✅ Manually started trace")

        agent = BackwardCompatibilityAgent("ManualAgent")
        result = agent.process_data("manual trace data")
        print(f"📊 Manual trace result: {result}")

        # Manually end trace
        agentops.end_trace(trace_context, "Success")
        print("✅ Manually ended trace")
    else:
        print("❌ Failed to start manual trace")


if __name__ == "__main__":
    print("🚀 AgentOps Backward Compatibility Examples")
    print("=" * 55)
    print("This demonstrates that ALL existing code continues to work!")
    print("=" * 55)

    try:
        # Show various legacy approaches still work
        legacy_session_management()
        legacy_start_session_api()
        mixed_usage_example()
        legacy_decorators_example()
        legacy_manual_trace_management()

        print("\n" + "=" * 55)
        print("✅ All backward compatibility examples completed!")
        print("\n🔒 Compatibility Guarantees:")
        print("  • All existing init() calls work unchanged")
        print("  • Legacy start_session()/end_session() APIs work")
        print("  • All decorators (@session, @trace, @agent, etc.) work")
        print("  • Manual trace management APIs work")
        print("  • Mixed usage patterns are supported")
        print("  • Zero breaking changes for existing code")

        print("\n💡 Migration Benefits:")
        print("  • Adopt context managers gradually")
        print("  • Mix old and new patterns as needed")
        print("  • No pressure to refactor existing code")
        print("  • Get automatic cleanup benefits immediately")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()
