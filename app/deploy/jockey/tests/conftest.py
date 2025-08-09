"""
Pytest configuration and fixtures for the API tests.

This module provides fixtures for managing Redis containers during testing.
"""

import pytest
import docker
import time
import redis
import socket
from contextlib import closing


def find_free_port():
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def wait_for_redis(host='localhost', port=6379, timeout=30):
    """Wait for Redis to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            client = redis.Redis(host=host, port=port, socket_timeout=1)
            client.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            print('.', end='', flush=True)
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def docker_client():
    """Create a Docker client for container management."""
    try:
        client = docker.from_env()
        # Test Docker connection
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture(scope="session")
def redis_container(docker_client):
    """Start a Redis container for testing."""
    print("Starting Redis Docker container for tests...")

    # Find a free port
    redis_port = find_free_port()
    print(f"Using Redis port: {redis_port}")

    # Build the Redis image from our Dockerfile
    print("Building Redis Docker image...")
    import os

    tests_dir = os.path.dirname(os.path.abspath(__file__))
    image, build_logs = docker_client.images.build(
        path=tests_dir, dockerfile="Dockerfile.redis", tag="test-redis:latest", rm=True
    )

    # Start the Redis container
    print("Starting Redis container...")
    container = docker_client.containers.run(
        "test-redis:latest",
        ports={'6379/tcp': redis_port},
        detach=True,
        remove=True,
        name=f"test-redis-{redis_port}",
    )

    # Wait for Redis to be ready
    print(f"Waiting for Redis to be ready at localhost:{redis_port}...")
    if not wait_for_redis('localhost', redis_port):
        container.stop()
        pytest.fail("Redis container failed to start")

    print("Redis is ready!")

    try:
        yield {'host': 'localhost', 'port': redis_port, 'container': container}
    finally:
        # Cleanup: stop and remove container
        print("Stopping Redis Docker container...")
        try:
            container.stop(timeout=5)
            print("Redis container stopped successfully")
        except Exception:
            print("Redis container was already stopped")  # Container might already be stopped


@pytest.fixture(scope="function")
def redis_client_with_container(redis_container, monkeypatch):
    """Create a Redis client connected to the test container."""
    from jockey.worker import queue

    # Patch Redis settings in the queue module's imported variables
    monkeypatch.setattr('jockey.worker.queue.REDIS_HOST', redis_container['host'])  # This references the actual env var import
    monkeypatch.setattr('jockey.worker.queue.REDIS_PORT', redis_container['port'])  # This references the actual env var import
    monkeypatch.setattr('jockey.worker.queue.REDIS_DB', 0)  # This references the actual env var import

    # Reset the module-level Redis client so it picks up new env vars
    queue._redis_client = None

    # Create a direct Redis client with test container settings
    client = queue._get_redis_client()

    # Ensure clean state
    client.flushdb()

    yield client

    # Cleanup after test
    try:
        client.flushdb()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture(scope="function")
def clean_redis(redis_client_with_container):
    """Provide a clean Redis client and track keys for cleanup."""
    from jockey.worker import queue
    
    tracked_keys = []

    # Helper function to track keys
    def track_key(key):
        tracked_keys.append(key)
        return key

    redis_client_with_container.track_key = track_key
    
    # Add queue functions as methods
    redis_client_with_container.store_event = queue.store_event
    redis_client_with_container.get_task_status = queue.get_task_status
    redis_client_with_container.get_task_events = queue.get_task_events

    yield redis_client_with_container

    # Cleanup tracked keys
    if tracked_keys:
        try:
            redis_client_with_container.delete(*tracked_keys)
        except Exception:
            pass


@pytest.fixture
def mock_configmap_data():
    """Mock ConfigMap data for testing."""
    from unittest.mock import Mock
    from kubernetes import client as k8s

    mock_configmap = Mock(spec=k8s.V1ConfigMap)
    mock_configmap.metadata = Mock()
    mock_configmap.metadata.name = "test-configmap"
    mock_configmap.metadata.namespace = "test-namespace"
    mock_configmap.metadata.labels = {"app": "test-app"}
    mock_configmap.data = {"key1": "value1", "key2": "value2"}
    mock_configmap.binary_data = None

    return mock_configmap


@pytest.fixture
def mock_secret_data():
    """Mock Secret data for testing."""
    from unittest.mock import Mock
    from kubernetes import client as k8s

    mock_secret = Mock(spec=k8s.V1Secret)
    mock_secret.metadata = Mock()
    mock_secret.metadata.name = "test-secret"
    mock_secret.metadata.namespace = "test-namespace"
    mock_secret.metadata.labels = {"app": "test-app"}
    mock_secret.data = {"username": "dGVzdA==", "password": "cGFzcw=="}  # base64 encoded
    mock_secret.type = "Opaque"

    return mock_secret
