from typing import Optional, TypedDict
import threading
from datetime import datetime, UTC
import uuid
import json
import redis

from jockey.backend.event import BaseEvent, SerializedEvent, deserialize_event
from jockey.config import DeploymentConfig, SerializedDeploymentConfig, TaskType
from jockey.log import logger
from jockey.environment import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_USER, REDIS_PASSWORD


# Redis key constants
REDIS_KEY_PREFIX: str = "deployment"
TASKS_HASH_NAME: str = f"{REDIS_KEY_PREFIX}:metadata"


class JobData(TypedDict):
    """Type definition for stored job data structure."""

    job_id: str
    project_id: str  # Links to upstream app/project
    namespace: str  # Kubernetes namespace for deployment
    config: SerializedDeploymentConfig
    queued_at: str
    job_type: str  # JobType enum value
    inputs: Optional[dict]
    callback_url: Optional[str]


class EventData(TypedDict):
    """Type definition for stored event data structure."""

    project_id: str
    namespace: str
    event: SerializedEvent
    timestamp: str  # ISO timestamp when event was stored


# Thread-safe lazy initialization for Redis client
_redis_client: Optional[redis.Redis] = None
_redis_lock = threading.Lock()


def _get_redis_client() -> redis.Redis:
    """Get Redis client instance with thread-safe lazy initialization.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                _redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    username=REDIS_USER,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                )

    return _redis_client


def _get_queue_key() -> str:
    """Generate Redis key for the task queue.

    Returns:
        Redis key for the task queue
    """
    return f"{REDIS_KEY_PREFIX}:queue"


def _get_task_key(namespace: str, project_id: str, task_id: str) -> str:
    """Generate Redis composite key for a task.

    Args:
        namespace: Kubernetes namespace
        project_id: Project identifier
        task_id: Task identifier

    Returns:
        Redis composite key for task data
    """
    return f"{namespace}:{project_id}:{task_id}"


def _get_event_key(task_id: str) -> str:
    """Generate Redis key for task events list.

    Args:
        task_id: Task identifier

    Returns:
        Redis key for events
    """
    return f"{REDIS_KEY_PREFIX}:events:{task_id}"


def queue_task(
    task_type: TaskType,
    config: DeploymentConfig,
    project_id: str | uuid.UUID,
    inputs: Optional[dict] = None,
    callback_url: Optional[str] = None,
) -> str:
    """Queue a task for background processing.

    Args:
        task_type: Type of task to execute (build, serve, or run)
        config: Task configuration snapshot
        project_id: Project identifier
        inputs: Optional input data for run tasks

    Returns:
        Task ID for tracking
    """
    task_id = str(uuid.uuid4())

    # Create task data with queue-specific fields
    task_data: JobData = {
        "job_id": task_id,
        "project_id": str(project_id),
        "namespace": config.namespace,
        "queued_at": datetime.now(UTC).isoformat(),
        "config": config.serialize(),
        "job_type": task_type.value,
        "inputs": inputs,
        "callback_url": callback_url,
    }

    # Store task data in composite hash
    composite_key = _get_task_key(config.namespace, str(project_id), task_id)
    redis_client = _get_redis_client()
    redis_client.hset(TASKS_HASH_NAME, composite_key, json.dumps(task_data))

    # Add task ID to queue for processing order
    redis_client.rpush(_get_queue_key(), task_id)

    logger.info(f"Queued {task_type.value} task {task_id} for project {project_id}")
    return task_id


def claim_next_task() -> Optional[JobData]:
    """Claim the next task from the queue.

    This operation is atomic because Redis LPOP removes and returns the leftmost
    element in a single operation. Multiple workers can safely call this function
    concurrently without risk of claiming the same task, as Redis processes one
    command at a time and LPOP guarantees only one worker will receive each task ID.

    Returns:
        Task data dictionary or None if queue is empty
    """
    if not (task_id := _get_redis_client().lpop(_get_queue_key())):
        return None

    if task_data := get_task_data(task_id):
        return task_data

    logger.error(f"Task {task_id} was in queue but task data not found in hash")
    return None


def get_tasks(
    namespace: str,
    project_id: str,
) -> list[JobData]:
    """Get all tasks for a specific project.

    Args:
        namespace: Kubernetes namespace
        project_id: Project identifier

    Returns:
        List of task data dictionaries ordered by newest first
    """
    tasks, cursor = [], 0
    while True:
        cursor, fields = _get_redis_client().hscan(
            TASKS_HASH_NAME,
            cursor,
            match=f"{namespace}:{project_id}:*",
        )

        for _, task_data in fields.items():
            try:
                tasks.append(JobData(**json.loads(task_data)))
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.error("Invalid task data")
                continue

        if cursor == 0:
            break

    return tasks


def get_task_data(task_id: str) -> Optional[JobData]:
    """Get task data by task ID.

    Args:
        task_id: Task identifier

    Returns:
        Task data dictionary or None if not found
    """
    cursor = 0

    while True:
        cursor, fields = _get_redis_client().hscan(
            TASKS_HASH_NAME,
            cursor,
            match=f"*:*:{task_id}",
        )

        for _, task_data in fields.items():
            try:
                return JobData(**json.loads(task_data))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        if cursor == 0:
            break

    return None


def get_queue_length() -> int:
    """Get the number of tasks waiting in the queue.

    Returns:
        Number of tasks in queue
    """
    return _get_redis_client().llen(_get_queue_key())  # type: ignore


def get_queued_tasks() -> list[str]:
    """Get all task IDs currently in the queue.

    Returns:
        List of task IDs waiting to be processed
    """
    return _get_redis_client().lrange(_get_queue_key(), 0, -1)  # type: ignore


def get_processing_count() -> int:
    """Get the number of tasks currently being processed.

    Returns:
        Number of tasks being processed (tasks that exist but are not in queue)
    """
    # Get all task keys and queued task IDs
    all_task_keys = len(_get_redis_client().keys(f"{REDIS_KEY_PREFIX}:*"))  # type: ignore
    queued_count = get_queue_length()

    # Processing tasks = total tasks - queued tasks
    return max(0, all_task_keys - queued_count)


def store_event(task_id: str, event: BaseEvent) -> None:
    """Store a task event in Redis using sorted sets for timestamp-based queries.

    Args:
        task_id: Task identifier
        event: Event to store
    """
    # Get task data to find namespace and project_id
    task_data = get_task_data(task_id)
    if not task_data:
        logger.error(f"Cannot store event for task {task_id}: task not found")
        return

    timestamp = datetime.now(UTC)
    data: EventData = {
        "namespace": task_data["namespace"],
        "project_id": task_data["project_id"],
        "timestamp": timestamp.isoformat(),
        "event": event.serialize(),
    }

    _get_redis_client().zadd(
        _get_event_key(task_id),
        {json.dumps(data): timestamp.timestamp()},
    )


def get_task_status(task_id: str) -> Optional[BaseEvent]:
    """Get the latest task status by getting the most recent event.

    Args:
        task_id: Task identifier

    Returns:
        EventStatus enum value from the most recent event or None
    """
    # Get the highest scored (most recent) event from sorted set
    latest_events = _get_redis_client().zrevrange(_get_event_key(task_id), 0, 0)

    try:
        event_data = json.loads(latest_events[0])  # type: ignore
        return deserialize_event(event_data["event"])
    except (IndexError, json.JSONDecodeError, KeyError, ValueError):
        return None


def get_task_events(
    task_id: str,
    start_time: Optional[datetime] = None,
) -> list[BaseEvent]:
    """Get task events history, optionally filtered by start time using Redis native operations.

    Args:
        task_id: Task identifier
        start_time: Optional datetime object - return events after this time

    Returns:
        List of BaseEvent instances, newest first
    """
    key = _get_event_key(task_id)

    if start_time:
        # Use Redis native range query: get events with timestamp > start_timestamp
        # zrevrangebyscore returns in descending order (newest first)
        # First arg is max, second is min. Add small epsilon to exclude exact timestamp
        min_score = start_time.timestamp() + 1e-9  # Use smallest possible increment
        events_json = _get_redis_client().zrevrangebyscore(key, '+inf', min_score)
    else:
        # Get all events in descending order (newest first)
        events_json = _get_redis_client().zrevrange(key, 0, -1)

    events = []
    for event_json in events_json:
        try:
            event_data = json.loads(event_json)
            event = deserialize_event(event_data["event"])
            if event is not None:
                events.append(event)
        except (json.JSONDecodeError, KeyError):
            pass  # TODO log this

    return events


def health_check() -> bool:
    """Check if Redis connection is healthy.

    Returns:
        True if Redis is accessible, False otherwise
    """
    try:
        _get_redis_client().ping()
        return True
    except Exception:
        return False
