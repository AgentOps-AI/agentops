"""
Integration tests for the DeploymentRedisClient against a real Redis instance.

These tests use Docker containers to provide a clean Redis instance for testing.
Run with: pytest tests/test_integration.py -m integration
"""

import pytest
import time
from datetime import datetime, UTC

from jockey.backend.event import EventStatus, BaseEvent, register_event


class SimpleEvent(BaseEvent):
    """Simple test event for integration testing."""

    event_type = "integration_test"

    def __init__(self, status: EventStatus, event_id: str, **kwargs):
        payload = kwargs.pop('payload', {})
        payload["event_id"] = event_id
        super().__init__(status, payload=payload, **kwargs)
        self.event_id = event_id

    def format_message(self) -> str:
        return f"Test event: {self.event_id}"


# Register the test event class
register_event(SimpleEvent)


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests using containerized Redis."""

    def test_redis_connection(self, redis_client_with_container):
        """Test that we can connect to Redis container."""
        result = redis_client_with_container.ping()
        assert result is True

    def test_store_and_retrieve_events(self, clean_redis):
        """Test storing and retrieving events end-to-end."""
        from jockey.worker.queue import queue_task
        from jockey.config import DeploymentConfig, TaskType
        
        # Create a job first
        config = DeploymentConfig(
            project_id="test-project-id",
            namespace="integration_test",
        )
        job_id = queue_task(TaskType.SERVE, config, "test-project-id")

        # Store multiple events
        events = [
            SimpleEvent(EventStatus.STARTED, "event_1"),
            SimpleEvent(EventStatus.PROGRESS, "event_2"),
            SimpleEvent(EventStatus.PROGRESS, "event_3"),
            SimpleEvent(EventStatus.COMPLETED, "event_4"),
        ]

        # Store events with small delays to ensure different timestamps
        for event in events:
            clean_redis.store_event(job_id, event)
            time.sleep(0.1)  # Small delay to to timestamp ordering

        # Retrieve all events
        retrieved_events = clean_redis.get_task_events(job_id)

        # Verify all events were stored and retrieved
        assert len(retrieved_events) == 4

        # Verify newest first ordering using payload data
        assert retrieved_events[0].payload["event_id"] == "event_4"
        assert retrieved_events[-1].payload["event_id"] == "event_1"

        # Verify status retrieval
        status_event = clean_redis.get_task_status(job_id)
        assert status_event is not None
        assert status_event.status == EventStatus.COMPLETED

    def test_timestamp_filtering(self, clean_redis):
        """Test timestamp-based event filtering."""
        from jockey.worker.queue import queue_task
        from jockey.config import DeploymentConfig, TaskType
        
        # Create a job first
        config = DeploymentConfig(
            project_id="test-project-id",
            namespace="integration_test",
        )
        job_id = queue_task(TaskType.SERVE, config, "test-project-id")

        # Store events with known timestamps
        start_time = datetime.now(UTC)

        # Store initial events
        clean_redis.store_event(job_id, SimpleEvent(EventStatus.STARTED, "before_filter"))
        time.sleep(1)

        filter_time = datetime.now(UTC)
        time.sleep(1)

        # Store events after filter time
        clean_redis.store_event(job_id, SimpleEvent(EventStatus.PROGRESS, "after_filter_1"))
        clean_redis.store_event(job_id, SimpleEvent(EventStatus.COMPLETED, "after_filter_2"))

        # Get all events
        all_events = clean_redis.get_task_events(job_id)
        assert len(all_events) == 3

        # Get events after filter time
        filtered_events = clean_redis.get_task_events(job_id, filter_time)

        # Should only get the 2 events after filter_time
        assert len(filtered_events) == 2
        assert filtered_events[1].payload["event_id"] == "after_filter_1"
        assert filtered_events[0].payload["event_id"] == "after_filter_2"

    def test_event_cleanup(self, clean_redis):
        """Test that all events are kept (current implementation has no cleanup)."""
        from jockey.worker.queue import queue_task
        from jockey.config import DeploymentConfig, TaskType
        
        # Create a job first
        config = DeploymentConfig(
            project_id="test-project-id",
            namespace="integration_test",
        )
        job_id = queue_task(TaskType.SERVE, config, "test-project-id")

        # Store multiple events
        for i in range(10):  # Smaller number to keep test fast
            event = SimpleEvent(EventStatus.PROGRESS, f"cleanup_event_{i}")
            clean_redis.store_event(job_id, event)

        # Verify all events are kept (no cleanup in current implementation)
        all_events = clean_redis.get_task_events(job_id)
        assert len(all_events) == 10

        # Verify newest events first (should have high numbers)
        newest_event = all_events[0]
        assert newest_event.payload["event_id"] == "cleanup_event_9"  # Should be the last event stored

    def test_real_event_types(self, clean_redis):
        """Test with actual event types from the system."""
        from jockey.worker.queue import queue_task
        from jockey.config import DeploymentConfig, TaskType
        
        # Create a job first
        config = DeploymentConfig(
            project_id="test-project-id",
            namespace="integration_test",
        )
        job_id = queue_task(TaskType.SERVE, config, "test-project-id")

        # Store different event types
        completion_event = SimpleEvent(EventStatus.COMPLETED, "completion_test")
        error_event = SimpleEvent(EventStatus.ERROR, "error_test")

        clean_redis.store_event(job_id, completion_event)
        clean_redis.store_event(job_id, error_event)

        # Retrieve and verify
        events = clean_redis.get_task_events(job_id)
        assert len(events) == 2

        # Verify event types and data
        error_event = events[0]  # Most recent
        completion_event = events[1]

        assert error_event.event_type == "integration_test"
        assert error_event.status == EventStatus.ERROR
        assert error_event.payload["event_id"] == "error_test"

        assert completion_event.event_type == "integration_test"
        assert completion_event.status == EventStatus.COMPLETED
        assert completion_event.payload["event_id"] == "completion_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
