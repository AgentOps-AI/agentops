"""
Error Handling with Context Managers

This example demonstrates error handling patterns with AgentOps context managers,
showing how traces automatically handle different types of exceptions.
"""

import os
import time
import agentops
from agentops import agent, task, tool
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")


@agent
class ErrorProneAgent:
    """An agent that can encounter various types of errors."""

    def __init__(self, name: str):
        self.name = name

    @task
    def risky_operation(self, operation_type: str) -> str:
        """Perform a risky operation that might fail."""
        if operation_type == "value_error":
            raise ValueError("Invalid value provided")
        elif operation_type == "type_error":
            raise TypeError("Wrong type provided")
        elif operation_type == "runtime_error":
            raise RuntimeError("Runtime error occurred")
        elif operation_type == "custom_error":
            raise CustomError("Custom error occurred")
        else:
            return f"Success: {operation_type}"

    @tool
    def validate_input(self, data: str) -> str:
        """Validate input data."""
        if not data or data == "invalid":
            raise ValueError("Invalid input data")
        return f"Validated: {data}"

    @task
    def multi_step_operation(self, steps: list) -> str:
        """Perform multiple steps, any of which might fail."""
        results = []
        for i, step in enumerate(steps):
            if step == "fail":
                raise RuntimeError(f"Step {i+1} failed")
            results.append(f"Step{i+1}:{step}")
        return " -> ".join(results)


class CustomError(Exception):
    """Custom exception for demonstration."""

    pass


def basic_exception_handling():
    """Basic example of exception handling with context managers."""
    print("Basic Exception Handling")

    agentops.init(api_key=AGENTOPS_API_KEY)

    error_types = ["value_error", "type_error", "runtime_error", "success"]

    for error_type in error_types:
        try:
            with agentops.start_trace(f"basic_{error_type}", tags=["basic", "error-handling"]):
                print(f"Started trace for {error_type}")

                agent = ErrorProneAgent(f"BasicAgent_{error_type}")
                result = agent.risky_operation(error_type)
                print(f"Success result: {result}")

        except ValueError as e:
            print(f"Caught ValueError: {e}")
        except TypeError as e:
            print(f"Caught TypeError: {e}")
        except RuntimeError as e:
            print(f"Caught RuntimeError: {e}")

    print("Basic exception handling completed")


def nested_exception_handling():
    """Example of exception handling in nested traces."""
    print("\nNested Exception Handling")

    agentops.init(api_key=AGENTOPS_API_KEY)

    try:
        with agentops.start_trace("outer_operation", tags=["nested", "outer"]):
            print("Outer trace started")

            # outer_agent = ErrorProneAgent("OuterAgent")  # Not used in this example

            try:
                with agentops.start_trace("inner_operation", tags=["nested", "inner"]):
                    print("Inner trace started")

                    inner_agent = ErrorProneAgent("InnerAgent")
                    # This will cause an error in the inner trace
                    inner_agent.risky_operation("value_error")

            except ValueError as e:
                print(f"Inner trace caught ValueError: {e}")
                # Re-raise to affect outer trace
                raise RuntimeError("Inner operation failed") from e

    except RuntimeError as e:
        print(f"Outer trace caught RuntimeError: {e}")

    print("Nested exception handling completed")


def retry_pattern():
    """Example of retry pattern with context managers."""
    print("\nRetry Pattern")

    agentops.init(api_key=AGENTOPS_API_KEY)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with agentops.start_trace(f"retry_attempt_{attempt+1}", tags=["retry", f"attempt-{attempt+1}"]):
                print(f"Retry attempt {attempt+1} started")

                agent = ErrorProneAgent(f"RetryAgent_Attempt{attempt+1}")

                # Simulate success on the last attempt
                if attempt < max_retries - 1:
                    result = agent.risky_operation("runtime_error")
                else:
                    result = agent.risky_operation("success")

                print(f"Retry attempt {attempt+1} succeeded: {result}")
                break

        except RuntimeError as e:
            print(f"Retry attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                print(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time * 0.01)  # Shortened for demo
            else:
                print("All retry attempts exhausted")
                raise

    print("Retry pattern completed")


def graceful_degradation():
    """Example of graceful degradation pattern."""
    print("\nGraceful Degradation")

    agentops.init(api_key=AGENTOPS_API_KEY)

    try:
        with agentops.start_trace("primary_service", tags=["degradation", "primary"]):
            print("Primary service trace started")

            agent = ErrorProneAgent("PrimaryAgent")
            result = agent.risky_operation("runtime_error")
            print(f"Primary service result: {result}")

    except RuntimeError as e:
        print(f"Primary service failed: {e}")
        print("Falling back to secondary service...")

        with agentops.start_trace("fallback_service", tags=["degradation", "fallback"]):
            print("Fallback service trace started")

            fallback_agent = ErrorProneAgent("FallbackAgent")
            result = fallback_agent.risky_operation("success")
            print(f"Fallback service result: {result}")

    print("Graceful degradation completed")


def partial_success_handling():
    """Example of partial success handling."""
    print("\nPartial Success Handling")

    agentops.init(api_key=AGENTOPS_API_KEY)

    steps = ["step1", "step2", "fail", "step4"]

    with agentops.start_trace("partial_success", tags=["partial", "multi-step"]):
        print("Partial success trace started")

        agent = ErrorProneAgent("PartialAgent")

        try:
            result = agent.multi_step_operation(steps)
            print(f"All steps completed: {result}")
        except RuntimeError as e:
            print(f"Operation partially failed: {e}")

    print("Partial success handling completed")


def custom_exception_handling():
    """Example of handling custom exceptions."""
    print("\nCustom Exception Handling")

    agentops.init(api_key=AGENTOPS_API_KEY)

    try:
        with agentops.start_trace("custom_exception", tags=["custom", "exception"]):
            print("Custom exception trace started")

            agent = ErrorProneAgent("CustomAgent")
            result = agent.risky_operation("custom_error")
            print(f"Result: {result}")

    except CustomError as e:
        print(f"Caught custom exception: {e}")
    except Exception as e:
        print(f"Caught unexpected exception: {e}")

    print("Custom exception handling completed")


def finally_blocks_example():
    """Example of exception handling with finally blocks."""
    print("\nFinally Blocks Example")

    agentops.init(api_key=AGENTOPS_API_KEY)

    cleanup_actions = []

    try:
        with agentops.start_trace("finally_example", tags=["finally", "cleanup"]):
            print("Finally example trace started")

            agent = ErrorProneAgent("FinallyAgent")

            try:
                result = agent.risky_operation("value_error")
                print(f"Result: {result}")
            finally:
                cleanup_actions.append("Inner cleanup executed")
                print("Inner finally block executed")

    except ValueError as e:
        print(f"Caught exception: {e}")
    finally:
        cleanup_actions.append("Outer cleanup executed")
        print("Outer finally block executed")

    print(f"Cleanup actions performed: {cleanup_actions}")
    print("Finally block handling completed")


def exception_chaining_example():
    """Example of exception chaining and context preservation."""
    print("\nException Chaining Example")

    agentops.init(api_key=AGENTOPS_API_KEY)

    try:
        with agentops.start_trace("exception_chaining", tags=["chaining", "context"]):
            print("Exception chaining trace started")

            agent = ErrorProneAgent("ChainingAgent")

            try:
                # First operation fails
                agent.validate_input("invalid")
            except ValueError as e:
                print(f"Validation failed: {e}")
                # Chain the exception with additional context
                raise RuntimeError("Operation failed due to validation error") from e

    except RuntimeError as e:
        print(f"Caught chained exception: {e}")
        print(f"Original cause: {e.__cause__}")

    print("Exception chaining completed")


if __name__ == "__main__":
    print("AgentOps Error Handling Examples")
    print("=" * 40)

    # Basic exception handling
    basic_exception_handling()

    # Nested exception handling
    nested_exception_handling()

    # Retry pattern
    retry_pattern()

    # Graceful degradation
    graceful_degradation()

    # Partial success handling
    partial_success_handling()

    # Custom exception handling
    custom_exception_handling()

    # Finally blocks
    finally_blocks_example()

    # Exception chaining
    exception_chaining_example()

    print("\nAll error handling examples completed!")
