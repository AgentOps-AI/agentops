"""Unit tests for the queue module."""

import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC

from jockey.worker.queue import (
    queue_task,
    claim_next_task,
    get_task_data,
    get_queue_length,
    get_queued_tasks,
    _get_task_key,
    _get_queue_key,
    _get_event_key,
    TASKS_HASH_NAME,
    REDIS_KEY_PREFIX,
)
from jockey.config import DeploymentConfig, TaskType


class TestQueueOperations:
    """Test the core queue operations."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        with patch('jockey.worker.queue._get_redis_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def sample_config(self):
        """Sample deployment configuration for testing."""
        return DeploymentConfig(
            project_id="test-project-id",
            namespace="test-namespace",
            ports=[8080, 9090],
            replicas=2,
        )

    def test_queue_task_creates_job_data_and_queues_id(self, mock_redis, sample_config):
        """Test that queue_task creates job data and adds job ID to queue."""
        # Setup
        mock_redis.hset.return_value = True
        mock_redis.rpush.return_value = 1

        # Execute
        job_id = queue_task(TaskType.SERVE, sample_config, "project-456")

        # Verify job ID format (full UUID)
        assert len(job_id) == 36  # Full UUID string
        assert job_id.count('-') == 4  # UUID format

        # Verify job data was stored in composite hash
        assert mock_redis.hset.call_count == 1
        hash_call = mock_redis.hset.call_args
        hash_name = hash_call[0][0]
        composite_key = hash_call[0][1]
        job_data_json = hash_call[0][2]

        assert hash_name == TASKS_HASH_NAME
        assert composite_key == f"test-namespace:project-456:{job_id}"

        # Parse and verify job data
        job_data = json.loads(job_data_json)
        assert job_data["job_id"] == job_id
        assert job_data["project_id"] == "project-456"
        assert job_data["namespace"] == "test-namespace"
        assert "queued_at" in job_data
        assert "config" in job_data

        # Verify config was serialized
        config_data = job_data["config"]
        assert config_data["project_id"] == "test-project-id"
        assert config_data["namespace"] == "test-namespace"
        assert config_data["ports"] == [8080, 9090]
        assert config_data["replicas"] == 2

        # Verify job ID was added to queue
        assert mock_redis.rpush.call_count == 1
        queue_call = mock_redis.rpush.call_args
        assert queue_call[0][0] == _get_queue_key()
        assert queue_call[0][1] == job_id

    def test_claim_next_task_returns_job_data(self, mock_redis, sample_config):
        """Test that claim_next_task returns job data for next job."""
        # Setup
        test_job_id = "abcd1234"
        mock_job_data = {
            "job_id": test_job_id,
            "project_id": "project-456",
            "namespace": "test-namespace",
            "queued_at": datetime.now(UTC).isoformat(),
            "config": sample_config.serialize(),
        }

        mock_redis.lpop.return_value = test_job_id
        # Mock hscan to return the job data - hscan returns (cursor, fields_dict)
        mock_redis.hscan.return_value = (0, {f"test-namespace:project-456:{test_job_id}": json.dumps(mock_job_data)})

        # Execute
        job_data = claim_next_task()

        # Verify
        assert job_data is not None
        assert job_data["job_id"] == test_job_id
        # deployment_id field has been removed, only project_id remains
        assert job_data["project_id"] == "project-456"
        assert job_data["namespace"] == "test-namespace"

        # Verify Redis calls
        mock_redis.lpop.assert_called_once_with(_get_queue_key())
        mock_redis.hscan.assert_called_once_with(TASKS_HASH_NAME, 0, match=f"*:*:{test_job_id}")

    def test_claim_next_task_returns_none_when_queue_empty(self, mock_redis):
        """Test that claim_next_task returns None when queue is empty."""
        # Setup
        mock_redis.lpop.return_value = None

        # Execute
        job_data = claim_next_task()

        # Verify
        assert job_data is None
        mock_redis.lpop.assert_called_once_with(_get_queue_key())
        mock_redis.hget.assert_not_called()

    def test_claim_next_task_logs_error_when_job_data_missing(self, mock_redis):
        """Test that claim_next_task logs error when job data is missing."""
        # Setup
        test_job_id = "abcd1234"
        mock_redis.lpop.return_value = test_job_id
        # Mock hscan to return no job data - hscan returns (cursor, fields_dict)
        mock_redis.hscan.return_value = (0, {})

        # Execute
        with patch('jockey.worker.queue.logger') as mock_logger:
            job_data = claim_next_task()

        # Verify
        assert job_data is None
        mock_logger.error.assert_called_once_with(
            f"Task {test_job_id} was in queue but task data not found in hash"
        )

    def test_get_task_data_returns_job_data(self, mock_redis, sample_config):
        """Test that get_task_data returns job data for a given job ID."""
        # Setup
        test_job_id = "abcd1234"
        mock_job_data = {
            "job_id": test_job_id,
            "project_id": "project-456",
            "namespace": "test-namespace",
            "queued_at": datetime.now(UTC).isoformat(),
            "config": sample_config.serialize(),
        }

        # Mock hscan to return the job data - hscan returns (cursor, fields_dict)
        mock_redis.hscan.return_value = (0, {f"test-namespace:project-456:{test_job_id}": json.dumps(mock_job_data)})

        # Execute
        job_data = get_task_data(test_job_id)

        # Verify
        assert job_data is not None
        assert job_data["job_id"] == test_job_id
        assert job_data["namespace"] == "test-namespace"

        mock_redis.hscan.assert_called_once_with(TASKS_HASH_NAME, 0, match=f"*:*:{test_job_id}")

    def test_get_task_data_returns_none_when_not_found(self, mock_redis):
        """Test that get_task_data returns None when job data not found."""
        # Setup
        test_job_id = "abcd1234"
        # Mock hscan to return no job data - hscan returns (cursor, fields_dict)
        mock_redis.hscan.return_value = (0, {})

        # Execute
        job_data = get_task_data(test_job_id)

        # Verify
        assert job_data is None
        mock_redis.hscan.assert_called_once_with(TASKS_HASH_NAME, 0, match=f"*:*:{test_job_id}")

    def test_get_queue_length_returns_queue_length(self, mock_redis):
        """Test that get_queue_length returns the number of jobs in queue."""
        # Setup
        mock_redis.llen.return_value = 5

        # Execute
        length = get_queue_length()

        # Verify
        assert length == 5
        mock_redis.llen.assert_called_once_with(_get_queue_key())

    def test_get_queued_tasks_returns_job_ids(self, mock_redis):
        """Test that get_queued_tasks returns list of job IDs."""
        # Setup
        mock_job_ids = ["abcd1234", "efgh5678", "ijkl9012"]
        mock_redis.lrange.return_value = mock_job_ids

        # Execute
        job_ids = get_queued_tasks()

        # Verify
        assert job_ids == mock_job_ids
        mock_redis.lrange.assert_called_once_with(_get_queue_key(), 0, -1)

    def test_get_job_key_generates_correct_key(self):
        """Test that _get_job_key generates correct Redis key."""
        namespace = "test-namespace"
        project_id = "project-456"
        job_id = "abcd1234"
        key = _get_task_key(namespace, project_id, job_id)
        assert key == f"{namespace}:{project_id}:{job_id}"

    def test_job_data_includes_namespace(self, mock_redis, sample_config):
        """Test that job data includes namespace from config."""
        # Setup
        mock_redis.hset.return_value = True
        mock_redis.rpush.return_value = 1

        # Execute
        job_id = queue_task(TaskType.SERVE, sample_config, "project-456")

        # Verify namespace is included
        hash_call = mock_redis.hset.call_args
        job_data_json = hash_call[0][2]
        job_data = json.loads(job_data_json)

        assert job_data["namespace"] == "test-namespace"

    def test_job_data_type_annotation(self, mock_redis, sample_config):
        """Test that job data structure matches JobData TypedDict."""
        # Setup
        mock_redis.hset.return_value = True
        mock_redis.rpush.return_value = 1

        # Execute
        job_id = queue_task(TaskType.SERVE, sample_config, "project-456")

        # Get the job data that was stored
        hash_call = mock_redis.hset.call_args
        job_data_json = hash_call[0][2]
        job_data = json.loads(job_data_json)

        # Verify all required JobData fields are present
        required_fields = ["job_id", "project_id", "namespace", "config", "queued_at"]
        for field in required_fields:
            assert field in job_data, f"Missing required field: {field}"

        # Verify types (as much as we can from JSON)
        assert isinstance(job_data["job_id"], str)
        assert isinstance(job_data["project_id"], str)
        assert isinstance(job_data["namespace"], str)
        assert isinstance(job_data["config"], dict)
        assert isinstance(job_data["queued_at"], str)
