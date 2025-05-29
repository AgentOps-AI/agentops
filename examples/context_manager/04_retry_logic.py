"""
Retry Logic Example

This example demonstrates how to implement retry patterns using
AgentOps context manager, with individual traces for each attempt.
"""

import os
import random
import time

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


def simple_retry_example():
    """Simple retry logic with context manager."""
    print("🔄 Simple Retry Logic Example")
    print("-" * 35)

    max_retries = 3

    for attempt in range(max_retries):
        try:
            with agentops.init(
                api_key=AGENTOPS_API_KEY,
                trace_name=f"retry_attempt_{attempt + 1}",
                auto_start_session=False,
                default_tags=["retry", f"attempt-{attempt + 1}", "simple"],
            ):
                print(f"🎯 Attempt {attempt + 1}/{max_retries}")

                agent = ExampleAgent(f"RetryAgent_Attempt{attempt + 1}")

                # Simulate operation that might fail
                if attempt < 2:  # Fail first two attempts
                    print("⚠️  Simulating failure...")
                    raise ConnectionError(f"Simulated failure on attempt {attempt + 1}")

                # Success on third attempt
                result = agent.process_data("retry operation data")
                print(f"✅ Success! Result: {result}")
                break

        except ConnectionError as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("💥 All retry attempts exhausted")
                raise
            print("🔄 Retrying...")
            time.sleep(0.5)  # Brief delay between retries

    print("✅ Simple retry completed\n")


def exponential_backoff_retry():
    """Retry with exponential backoff."""
    print("📈 Exponential Backoff Retry Example")
    print("-" * 40)

    max_retries = 4
    base_delay = 0.1

    for attempt in range(max_retries):
        delay = base_delay * (2**attempt)  # Exponential backoff

        try:
            with agentops.init(
                api_key=AGENTOPS_API_KEY,
                trace_name=f"backoff_retry_{attempt + 1}",
                auto_start_session=False,
                default_tags=["retry", "exponential-backoff", f"attempt-{attempt + 1}"],
            ):
                print(f"🎯 Attempt {attempt + 1}/{max_retries} (delay: {delay:.1f}s)")

                agent = ExampleAgent(f"BackoffAgent_Attempt{attempt + 1}")

                # Simulate random failure (70% chance of failure)
                if random.random() < 0.7:
                    print("⚠️  Random failure occurred...")
                    raise TimeoutError(f"Random timeout on attempt {attempt + 1}")

                # Success
                result = agent.process_data("backoff operation data")
                print(f"✅ Success! Result: {result}")
                break

        except TimeoutError as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("💥 All retry attempts exhausted")
                raise
            print(f"⏳ Waiting {delay:.1f}s before retry...")
            time.sleep(delay)

    print("✅ Exponential backoff retry completed\n")


def conditional_retry_example():
    """Retry with different strategies based on error type."""
    print("🎛️  Conditional Retry Example")
    print("-" * 35)

    max_retries = 3

    for attempt in range(max_retries):
        try:
            with agentops.init(
                api_key=AGENTOPS_API_KEY,
                trace_name=f"conditional_retry_{attempt + 1}",
                auto_start_session=False,
                default_tags=["retry", "conditional", f"attempt-{attempt + 1}"],
            ):
                print(f"🎯 Attempt {attempt + 1}/{max_retries}")

                agent = ExampleAgent(f"ConditionalAgent_Attempt{attempt + 1}")

                # Simulate different types of errors
                error_type = random.choice(["network", "auth", "rate_limit", "success"])

                if error_type == "network":
                    print("🌐 Network error occurred")
                    raise ConnectionError("Network connection failed")
                elif error_type == "auth":
                    print("🔐 Authentication error occurred")
                    raise PermissionError("Authentication failed")
                elif error_type == "rate_limit":
                    print("⏱️  Rate limit error occurred")
                    raise Exception("Rate limit exceeded")
                else:
                    # Success
                    result = agent.process_data("conditional operation data")
                    print(f"✅ Success! Result: {result}")
                    break

        except ConnectionError as e:
            print(f"❌ Network error: {e}")
            if attempt < max_retries - 1:
                print("🔄 Network errors are retryable, trying again...")
                time.sleep(0.5)
            else:
                print("💥 Max network retries reached")
                raise

        except PermissionError as e:
            print(f"❌ Auth error: {e}")
            print("🚫 Authentication errors are not retryable")
            raise

        except Exception as e:
            print(f"❌ Rate limit error: {e}")
            if attempt < max_retries - 1:
                delay = 1.0 * (attempt + 1)  # Longer delay for rate limits
                print(f"⏳ Rate limit hit, waiting {delay}s...")
                time.sleep(delay)
            else:
                print("💥 Max rate limit retries reached")
                raise

    print("✅ Conditional retry completed\n")


def batch_retry_example():
    """Retry individual items in a batch operation."""
    print("📦 Batch Retry Example")
    print("-" * 25)

    items = ["item1", "item2", "item3", "item4", "item5"]
    results = {}
    max_retries = 2

    for item in items:
        print(f"\n🎯 Processing {item}")

        for attempt in range(max_retries):
            try:
                with agentops.init(
                    api_key=AGENTOPS_API_KEY,
                    trace_name=f"batch_{item}_attempt_{attempt + 1}",
                    auto_start_session=False,
                    default_tags=["batch", "retry", item, f"attempt-{attempt + 1}"],
                ):
                    print(f"  📊 Attempt {attempt + 1}/{max_retries} for {item}")

                    agent = ExampleAgent(f"BatchAgent_{item}")

                    # Simulate random failures (40% chance)
                    if random.random() < 0.4:
                        print(f"  ⚠️  Processing {item} failed")
                        raise RuntimeError(f"Failed to process {item}")

                    # Success
                    result = agent.process_data(f"batch data for {item}")
                    results[item] = result
                    print(f"  ✅ {item} processed successfully")
                    break

            except RuntimeError as e:
                print(f"  ❌ {item} attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    print(f"  💥 {item} failed after all retries")
                    results[item] = f"FAILED: {e}"
                else:
                    print(f"  🔄 Retrying {item}...")
                    time.sleep(0.2)

    print("\n📋 Batch Results:")
    for item, result in results.items():
        status = "✅" if not result.startswith("FAILED") else "❌"
        print(f"  {status} {item}: {result}")

    print("✅ Batch retry completed\n")


if __name__ == "__main__":
    print("🚀 AgentOps Retry Logic Examples")
    print("=" * 40)

    try:
        # Set random seed for reproducible examples
        random.seed(42)

        # Run different retry examples
        simple_retry_example()
        exponential_backoff_retry()
        conditional_retry_example()
        batch_retry_example()

        print("=" * 40)
        print("✅ All retry logic examples completed!")
        print("\n💡 Key Benefits:")
        print("  • Each retry attempt gets its own trace")
        print("  • Easy to debug which attempt succeeded/failed")
        print("  • Clear visibility into retry patterns")
        print("  • Automatic cleanup even if all retries fail")
        print("  • Supports different retry strategies")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()
