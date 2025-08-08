import time
import threading
import uuid
from typing import Optional

from jockey.config import (
    DeploymentConfig,
    TaskType,
)
from jockey.exec import (
    execute_serve,
    execute_build,
    execute_run,
)
from jockey.backend.event import BaseEvent
from jockey.log import logger
from jockey.environment import WORKER_POLL_INTERVAL
from jockey.worker import queue


class Worker:
    """Background worker that processes tasks from Redis queue."""

    running: bool = False
    worker_threads: dict[str, threading.Thread]
    worker_id: str

    def __init__(self):
        """Initialize the task worker."""
        self.worker_threads = {}
        self.worker_id = str(uuid.uuid4())

    def start(self) -> None:
        """Start the worker polling loop."""
        self.running = True
        logger.info("Starting task worker")

        while self.running:
            try:
                if task_data := self._get_next_task():
                    self._process_task(task_data)

                self._cleanup_threads()
                time.sleep(WORKER_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(WORKER_POLL_INTERVAL)

    def stop(self) -> None:
        """Stop the worker and wait for active tasks to complete."""
        logger.info("Stopping task worker")
        self.running = False

        # Wait for active tasks to complete
        for thread in self.worker_threads.values():
            if thread.is_alive():
                thread.join(timeout=30)  # 30 second timeout

    def _get_next_task(self) -> Optional[queue.JobData]:
        """Get the next task from the queue using atomic dequeue.

        Returns:
            Task data dictionary or None if queue is empty
        """
        task_data = queue.claim_next_task()
        if task_data:
            return task_data
        return None

    def _process_task(self, task_data: queue.JobData) -> None:
        """Process a task by starting it in a background thread.

        Args:
            task_data: Task data containing configuration
        """
        task_id = task_data["job_id"]
        project_id = task_data["project_id"]

        # Don't start duplicate tasks
        if task_id in self.worker_threads and self.worker_threads[task_id].is_alive():
            logger.warning(f"Task {task_id} already running")
            return

        logger.info(f"Starting task {task_id} for project {project_id}")
        thread = threading.Thread(
            target=self._run_task,
            args=(task_data,),
            daemon=True,
            name=f"task-{task_id}",
        )
        thread.start()
        self.worker_threads[task_id] = thread

    def _run_task(self, task_data: queue.JobData) -> None:
        """Run a task and store events in Redis.

        Args:
            task_data: Task data containing configuration
        """
        task_id = task_data["job_id"]
        project_id = task_data["project_id"]

        try:
            config = DeploymentConfig.from_serialized(task_data["config"])
            task_type = TaskType(task_data["job_type"])  # Deserialize string back to enum
            logger.info(f"Processing {task_type.value} task for {config.tag} in {config.namespace}")

            match task_type:
                case TaskType.SERVE:
                    for event in execute_serve(config, job_id=task_id):
                        if isinstance(event, BaseEvent):
                            queue.store_event(task_id=task_id, event=event)
                case TaskType.BUILD:
                    for event in execute_build(config, job_id=task_id):
                        if isinstance(event, BaseEvent):
                            queue.store_event(task_id=task_id, event=event)
                case TaskType.RUN:
                    for event in execute_run(config, task_data.get("inputs"), job_id=task_id):
                        if isinstance(event, BaseEvent):
                            queue.store_event(task_id=task_id, event=event)
                case _:
                    logger.error(f"Unknown task type: {task_type}")
                    raise ValueError(f"Unknown task type: {task_type}")

        except Exception:
            logger.error(f"Task {task_id} failed", exc_info=True)
            # note this will not store an event in redis; revisit this if we want to track failures
        finally:
            self._cleanup_task(task_id)

    def _cleanup_task(self, task_id: str) -> None:
        """Clean up task state after completion.

        Args:
            task_id: Task identifier
        """
        try:
            if task_id in self.worker_threads:
                del self.worker_threads[task_id]
                logger.debug(f"Cleaned up task {task_id}")
        except Exception as e:
            logger.error(f"Error cleaning up task {task_id}: {e}")

    def _cleanup_threads(self) -> None:
        """Clean up completed task threads."""
        for task_id in self.get_running_tasks():
            logger.debug(f"Removing completed task {task_id} thread")
            del self.worker_threads[task_id]

    def get_running_tasks(self) -> list[str]:
        """Get currently active tasks.

        Returns:
            List of task IDs that are currently running
        """
        return [task_id for task_id, thread in self.worker_threads.items() if thread.is_alive()]


if __name__ == "__main__":
    """Run the task worker as a standalone process."""
    import signal
    import sys

    worker = Worker()

    def signal_handler(signum, frame):
        print("\nReceived shutdown signal, stopping worker...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
