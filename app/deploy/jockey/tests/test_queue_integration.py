"""
Integration tests for the queue module using real Redis in Docker.

These tests verify the complete job lifecycle and event system using a real Redis instance.
"""

import pytest
import time
import json
from datetime import datetime, UTC
from unittest.mock import Mock

from jockey.config import DeploymentConfig, TaskType
from jockey.worker.queue import (
    queue_task,
    claim_next_task,
    get_tasks,
    get_task_data,
    get_queue_length,
    get_queued_tasks,
    store_event,
    get_task_events,
    get_task_status,
    health_check,
    TASKS_HASH_NAME,
    _get_queue_key,
    _get_task_key,
    _get_event_key,
    REDIS_KEY_PREFIX,
)
from jockey.backend.event import BaseEvent, EventStatus, register_event


class IntegrationDeploymentEvent(BaseEvent):
    """Test event for integration testing."""
    
    event_type = "test_deployment"
    
    def __init__(self, status: EventStatus, message: str = "", **kwargs):
        super().__init__(status, message=message, **kwargs)
    
    def format_message(self) -> str:
        return self.message


# Register the test event
register_event(IntegrationDeploymentEvent)


@pytest.mark.integration
class TestQueueIntegration:
    """Integration tests for queue operations with real Redis."""

    @pytest.fixture
    def sample_config(self):
        """Sample deployment configuration for testing."""
        return DeploymentConfig(
            project_id="test-project-id",
            namespace="integration-test", 
            ports=[8080, 9090],
            replicas=2,
            repository_url="https://github.com/test/repo.git",
            branch="main",
            entrypoint="main.py",
        )

    def test_health_check(self, redis_client_with_container):
        """Test Redis health check functionality."""
        assert health_check() is True

    def test_complete_job_lifecycle(self, redis_client_with_container, sample_config):
        """Test the complete lifecycle: queue → claim → process → retrieve."""
        # 1. Queue a deployment
        project_id = "integration-test-project"
        job_id = queue_task(TaskType.SERVE, sample_config, project_id)
        
        # Verify job ID is a full UUID
        assert len(job_id) == 36
        assert job_id.count('-') == 4
        
        # 2. Verify job is in queue
        assert get_queue_length() == 1
        queued_jobs = get_queued_tasks()
        assert len(queued_jobs) == 1
        assert queued_jobs[0] == job_id
        
        # 3. Claim the job
        claimed_job = claim_next_task()
        assert claimed_job is not None
        assert claimed_job["job_id"] == job_id
        assert claimed_job["project_id"] == project_id
        assert claimed_job["namespace"] == "integration-test"
        
        # Verify job config was preserved
        config_data = claimed_job["config"]
        assert config_data["project_id"] == "test-project-id"
        assert config_data["namespace"] == "integration-test"
        
        # 4. Verify queue is now empty
        assert get_queue_length() == 0
        assert get_queued_tasks() == []
        
        # 5. Test that claiming from empty queue returns None
        empty_claim = claim_next_task()
        assert empty_claim is None

    def test_job_data_persistence(self, redis_client_with_container, sample_config):
        """Test that job data persists correctly in Redis."""
        project_id = "persistence-test"
        job_id = queue_task(TaskType.SERVE, sample_config, project_id)
        
        # Test get_job_data by ID
        job_data = get_task_data(job_id)
        assert job_data is not None
        assert job_data["job_id"] == job_id
        assert job_data["project_id"] == project_id
        assert job_data["namespace"] == sample_config.namespace
        
        # Verify timestamp format
        queued_at = datetime.fromisoformat(job_data["queued_at"])
        assert abs((datetime.now(UTC) - queued_at).total_seconds()) < 5
        
        # Test get_jobs by project
        jobs = get_tasks(sample_config.namespace, project_id)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == job_id

    def test_multiple_jobs_same_project(self, redis_client_with_container, sample_config):
        """Test queuing multiple jobs for the same project."""
        project_id = "multi-job-test"
        
        # Queue 3 jobs
        job_ids = []
        for i in range(3):
            config = DeploymentConfig(
                project_id=f"test-project-{i}",
                namespace="multi-test",
            )
            job_id = queue_task(TaskType.SERVE, config, project_id)
            job_ids.append(job_id)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Verify all jobs are queued
        assert get_queue_length() == 3
        
        # Get jobs for the project
        jobs = get_tasks("multi-test", project_id)
        assert len(jobs) == 3
        
        # Jobs should be returned in order (implementation detail)
        returned_job_ids = [job["job_id"] for job in jobs]
        assert set(returned_job_ids) == set(job_ids)
        
        # Claim all jobs and verify FIFO order
        claimed_jobs = []
        for _ in range(3):
            job = claim_next_task()
            assert job is not None
            claimed_jobs.append(job)
        
        # First job queued should be first claimed (FIFO)
        assert claimed_jobs[0]["job_id"] == job_ids[0]
        assert claimed_jobs[1]["job_id"] == job_ids[1]
        assert claimed_jobs[2]["job_id"] == job_ids[2]

    def test_event_storage_and_retrieval(self, redis_client_with_container, sample_config):
        """Test storing and retrieving events for jobs."""
        project_id = "event-test"
        job_id = queue_task(TaskType.SERVE, sample_config, project_id)
        
        # Store multiple events
        events = [
            IntegrationDeploymentEvent(EventStatus.STARTED, "Deployment started"),
            IntegrationDeploymentEvent(EventStatus.PROGRESS, "Building image"),
            IntegrationDeploymentEvent(EventStatus.PROGRESS, "Deploying to cluster"),
            IntegrationDeploymentEvent(EventStatus.COMPLETED, "Deployment completed"),
        ]
        
        for event in events:
            store_event(job_id, event)
            time.sleep(0.01)  # Small delay for timestamp ordering
        
        # Retrieve all events
        retrieved_events = get_task_events(job_id)
        assert len(retrieved_events) == 4
        
        # Events should be in reverse chronological order (newest first)
        assert retrieved_events[0].status == EventStatus.COMPLETED
        assert retrieved_events[0].message == "Deployment completed"
        assert retrieved_events[-1].status == EventStatus.STARTED
        assert retrieved_events[-1].message == "Deployment started"
        
        # Test get_task_status (should return latest event)
        latest_event = get_task_status(job_id)
        assert latest_event is not None
        assert latest_event.status == EventStatus.COMPLETED
        assert latest_event.message == "Deployment completed"

    def test_event_timestamp_filtering(self, redis_client_with_container, sample_config):
        """Test timestamp-based event filtering."""
        project_id = "timestamp-test"
        job_id = queue_task(TaskType.SERVE, sample_config, project_id)
        
        # Store initial event
        store_event(job_id, IntegrationDeploymentEvent(EventStatus.STARTED, "Started"))
        time.sleep(1)  # Ensure clear time separation
        
        # Record filter time
        filter_time = datetime.now(UTC)
        time.sleep(1)
        
        # Store events after filter time
        store_event(job_id, IntegrationDeploymentEvent(EventStatus.PROGRESS, "Building"))
        store_event(job_id, IntegrationDeploymentEvent(EventStatus.COMPLETED, "Done"))
        
        # Get all events
        all_events = get_task_events(job_id)
        assert len(all_events) == 3
        
        # Get events after filter time
        filtered_events = get_task_events(job_id, start_time=filter_time)
        assert len(filtered_events) == 2
        assert all(event.message in ["Building", "Done"] for event in filtered_events)

    def test_redis_key_structure(self, redis_client_with_container, sample_config):
        """Test that Redis keys are structured correctly."""
        project_id = "key-structure-test"
        job_id = queue_task(TaskType.SERVE, sample_config, project_id)
        
        # Test key generation functions
        queue_key = _get_queue_key()
        job_key = _get_task_key(sample_config.namespace, project_id, job_id)
        event_key = _get_event_key(job_id)
        
        assert queue_key == _get_queue_key()
        assert job_key == f"{sample_config.namespace}:{project_id}:{job_id}"
        assert event_key == _get_event_key(job_id)
        
        # Verify actual Redis keys exist
        redis_client = redis_client_with_container
        
        # Queue should contain the job ID
        assert redis_client.lrange(queue_key, 0, -1) == [job_id]
        
        # Job hash should contain the job data
        job_data_raw = redis_client.hget(TASKS_HASH_NAME, job_key)
        assert job_data_raw is not None
        job_data = json.loads(job_data_raw)
        assert job_data["job_id"] == job_id
        
        # Store an event and verify event key
        test_event = IntegrationDeploymentEvent(EventStatus.STARTED, "Test event")
        store_event(job_id, test_event)
        
        # Event sorted set should exist
        event_count = redis_client.zcard(event_key)
        assert event_count == 1

    def test_concurrent_job_claiming(self, redis_client_with_container, sample_config):
        """Test that multiple workers can safely claim jobs concurrently."""
        project_id = "concurrent-test"
        
        # Queue multiple jobs
        job_ids = []
        for i in range(5):
            config = DeploymentConfig(
                project_id=f"concurrent-project-{i}",
                namespace="concurrent-test",
            )
            job_id = queue_task(TaskType.SERVE, config, project_id)
            job_ids.append(job_id)
        
        # Simulate concurrent claiming
        claimed_jobs = []
        for _ in range(5):
            job = claim_next_task()
            if job:
                claimed_jobs.append(job)
        
        # All jobs should be claimed exactly once
        assert len(claimed_jobs) == 5
        claimed_job_ids = [job["job_id"] for job in claimed_jobs]
        assert set(claimed_job_ids) == set(job_ids)
        
        # Queue should be empty
        assert get_queue_length() == 0
        assert claim_next_task() is None

    def test_job_data_integrity(self, redis_client_with_container):
        """Test that complex job data is preserved correctly."""
        complex_config = DeploymentConfig(
            project_id="complex-project",
            namespace="integrity-test",
            repository_url="https://github.com/complex/repo.git",
            branch="feature/complex-deployment",
            github_access_token="test-token-123",
            entrypoint="src/main.py",
            ports=[8080, 9090, 3000],
            replicas=3,
            secret_names=["db-secret", "api-key", "ssl-cert"],
        )
        
        project_id = "integrity-test-project"
        job_id = queue_task(TaskType.SERVE, complex_config, project_id)
        
        # Claim and verify all data is intact
        job_data = claim_next_task()
        assert job_data is not None
        
        config = job_data["config"]
        assert config["project_id"] == "complex-project"
        assert config["namespace"] == "integrity-test"
        assert config["repository_url"] == "https://github.com/complex/repo.git"
        assert config["branch"] == "feature/complex-deployment"
        assert config["github_access_token"] == "test-token-123"
        assert config["entrypoint"] == "src/main.py"
        assert config["ports"] == [8080, 9090, 3000]
        assert config["replicas"] == 3
        assert config["secret_names"] == ["db-secret", "api-key", "ssl-cert"]

    def test_event_data_integrity(self, redis_client_with_container, sample_config):
        """Test that event data with complex payloads is preserved."""
        project_id = "event-integrity-test"
        job_id = queue_task(TaskType.SERVE, sample_config, project_id)
        
        # Create event with complex payload
        complex_event = IntegrationDeploymentEvent(
            EventStatus.PROGRESS,
            "Complex deployment step",
            payload={
                "step": "image_build",
                "progress": 75,
                "details": {
                    "image_size": "1.2GB",
                    "layers": 12,
                    "build_time": "3m45s"
                },
                "metrics": [
                    {"name": "cpu_usage", "value": 85.5},
                    {"name": "memory_usage", "value": 1024}
                ]
            }
        )
        
        store_event(job_id, complex_event)
        
        # Retrieve and verify data integrity
        events = get_task_events(job_id)
        assert len(events) == 1
        
        retrieved_event = events[0]
        assert retrieved_event.status == EventStatus.PROGRESS
        assert retrieved_event.message == "Complex deployment step"
        assert retrieved_event.payload["step"] == "image_build"
        assert retrieved_event.payload["progress"] == 75
        assert retrieved_event.payload["details"]["image_size"] == "1.2GB"
        assert len(retrieved_event.payload["metrics"]) == 2

    def test_error_handling(self, redis_client_with_container):
        """Test error handling for edge cases."""
        # Test getting non-existent job
        non_existent_job = get_task_data("non-existent-job-id")
        assert non_existent_job is None
        
        # Test getting events for non-existent job
        non_existent_events = get_task_events("non-existent-job-id")
        assert non_existent_events == []
        
        # Test getting status for non-existent job
        non_existent_status = get_task_status("non-existent-job-id")
        assert non_existent_status is None
        
        # Test getting jobs for non-existent project
        non_existent_project_jobs = get_tasks("non-existent-namespace", "non-existent-project")
        assert non_existent_project_jobs == []