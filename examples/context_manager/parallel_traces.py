"""
Parallel Traces Example

This example demonstrates how AgentOps context managers create independent
parallel traces rather than parent-child relationships, which is ideal for
concurrent operations and workflow management.
"""

import os
import time
import threading
import concurrent.futures
import agentops
from agentops import agent, task, tool
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")


@agent
class WorkerAgent:
    """A worker agent that can process tasks independently."""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id

    @task
    def process_task(self, task_data: str) -> str:
        """Process a task with some simulated work."""
        # Simulate some work
        time.sleep(0.1)

        result = self.analyze_data(task_data)
        return self.finalize_result(result)

    @tool
    def analyze_data(self, data: str) -> str:
        """Analyze the input data."""
        return f"Analyzed: {data}"

    @tool
    def finalize_result(self, analyzed_data: str) -> str:
        """Finalize the processing result."""
        return f"Final: {analyzed_data.upper()}"


def sequential_parallel_traces():
    """Example of sequential parallel traces - each trace is independent."""
    print("Sequential Parallel Traces")

    agentops.init(api_key=AGENTOPS_API_KEY)

    tasks = ["task_1", "task_2", "task_3"]
    results = []

    for i, task_name in enumerate(tasks):
        # Each trace is completely independent
        with agentops.start_trace(f"sequential_{task_name}", tags=["sequential", f"step-{i+1}"]):
            print(f"Started trace for {task_name}")

            worker = WorkerAgent(f"Worker{i+1}")
            result = worker.process_task(f"data_for_{task_name}")
            results.append(result)

            print(f"{task_name} result: {result}")

    print("All sequential traces completed")
    print(f"Final results: {results}")


def nested_parallel_traces():
    """Example showing that nested context managers create parallel traces."""
    print("\nNested Parallel Traces")

    agentops.init(api_key=AGENTOPS_API_KEY)

    # Outer trace for the overall workflow
    with agentops.start_trace("workflow_main", tags=["workflow", "main"]):
        print("Main workflow trace started")

        # Inner trace for data preparation (parallel, not child)
        with agentops.start_trace("data_preparation", tags=["workflow", "preparation"]):
            print("Data preparation trace started (parallel to main)")

            prep_worker = WorkerAgent("PrepWorker")
            prep_result = prep_worker.process_task("raw_data")
            print(f"Preparation result: {prep_result}")

        print("Data preparation trace ended")

        # Another inner trace for data processing (also parallel)
        with agentops.start_trace("data_processing", tags=["workflow", "processing"]):
            print("Data processing trace started (parallel to main)")

            proc_worker = WorkerAgent("ProcessWorker")
            proc_result = proc_worker.process_task("prepared_data")
            print(f"Processing result: {proc_result}")

        print("Data processing trace ended")
        print("Main workflow completed")

    print("Main workflow trace ended")
    print("All traces were independent/parallel, not parent-child relationships")


def concurrent_traces_with_threads():
    """Example of truly concurrent traces using threading."""
    print("\nConcurrent Traces with Threading")

    agentops.init(api_key=AGENTOPS_API_KEY)

    def worker_function(worker_id: int, task_data: str):
        """Function to run in a separate thread with its own trace."""
        trace_name = f"concurrent_worker_{worker_id}"

        with agentops.start_trace(trace_name, tags=["concurrent", f"worker-{worker_id}"]):
            print(f"Thread {worker_id}: Trace started")

            worker = WorkerAgent(f"ConcurrentWorker{worker_id}")
            result = worker.process_task(task_data)

            # Simulate varying work times
            time.sleep(0.05 * worker_id)

            print(f"Thread {worker_id}: Result: {result}")
            return result

    # Start multiple threads, each with their own trace
    threads = []
    results = []

    for i in range(3):
        thread = threading.Thread(target=lambda i=i: results.append(worker_function(i, f"concurrent_data_{i}")))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("All concurrent traces completed")
    print(f"Results from concurrent execution: {len(results)} completed")


def concurrent_traces_with_executor():
    """Example using ThreadPoolExecutor for concurrent traces."""
    print("\nConcurrent Traces with ThreadPoolExecutor")

    agentops.init(api_key=AGENTOPS_API_KEY)

    def process_with_trace(task_id: int, data: str) -> str:
        """Process data within its own trace context."""
        trace_name = f"executor_task_{task_id}"

        with agentops.start_trace(trace_name, tags=["executor", f"task-{task_id}"]):
            print(f"Executor task {task_id}: Trace started")

            worker = WorkerAgent(f"ExecutorWorker{task_id}")
            result = worker.process_task(data)

            print(f"Executor task {task_id}: Result: {result}")
            return result

    # Use ThreadPoolExecutor for concurrent execution
    tasks_data = [
        (1, "executor_data_1"),
        (2, "executor_data_2"),
        (3, "executor_data_3"),
        (4, "executor_data_4"),
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(process_with_trace, task_id, data): task_id for task_id, data in tasks_data}

        # Collect results as they complete
        results = []
        for future in concurrent.futures.as_completed(future_to_task):
            task_id = future_to_task[future]
            try:
                result = future.result()
                results.append((task_id, result))
                print(f"Task {task_id} completed successfully")
            except Exception as e:
                print(f"Task {task_id} failed: {e}")

    print("All executor-based traces completed")
    print(f"Completed {len(results)} tasks concurrently")


def trace_with_different_tag_types():
    """Example showing different ways to tag parallel traces."""
    print("\nTraces with Different Tag Types")

    agentops.init(api_key=AGENTOPS_API_KEY)

    # Trace with list tags
    with agentops.start_trace("list_tags_trace", tags=["list", "example", "demo"]):
        print("Trace with list tags started")
        worker1 = WorkerAgent("ListTagWorker")
        result1 = worker1.process_task("list_tag_data")
        print(f"List tags result: {result1}")

    # Trace with dictionary tags
    with agentops.start_trace(
        "dict_tags_trace", tags={"environment": "demo", "version": "1.0", "priority": "high", "team": "engineering"}
    ):
        print("Trace with dictionary tags started")
        worker2 = WorkerAgent("DictTagWorker")
        result2 = worker2.process_task("dict_tag_data")
        print(f"Dictionary tags result: {result2}")

    # Trace with no tags
    with agentops.start_trace("no_tags_trace"):
        print("Trace with no tags started")
        worker3 = WorkerAgent("NoTagWorker")
        result3 = worker3.process_task("no_tag_data")
        print(f"No tags result: {result3}")

    print("All differently tagged traces completed")


if __name__ == "__main__":
    print("AgentOps Parallel Traces Examples")
    print("=" * 40)

    # Sequential parallel traces
    sequential_parallel_traces()

    # Nested parallel traces
    nested_parallel_traces()

    # Concurrent traces with threading
    concurrent_traces_with_threads()

    # Concurrent traces with executor
    concurrent_traces_with_executor()

    # Different tag types
    trace_with_different_tag_types()

    print("\nAll parallel trace examples completed!")
