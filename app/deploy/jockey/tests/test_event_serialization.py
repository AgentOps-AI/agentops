"""Unit tests for event serialization and deserialization."""

import pytest
from jockey.backend.event import EventStatus, deserialize_event, _registry
from jockey.backend.models.deployment import DeploymentEvent
from jockey.backend.models.image import BuildEvent
from jockey.backend.models.pod import PodEvent
from jockey.backend.models.repository import RepositoryEvent, RepositoryEventStep


class TestEventSerialization:
    """Test serialization and deserialization of all event types."""

    def test_deployment_event_serialization(self):
        """Test DeploymentEvent serialization and deserialization."""
        # Create a deployment event with all fields
        original_event = DeploymentEvent(
            EventStatus.PROGRESS,
            available_replicas=2,
            ready_replicas=1,
            desired_replicas=3,
            phase="Progressing",
            payload={"test_data": "deployment_test"},
        )

        # Serialize the event
        serialized = original_event.serialize()

        # Verify serialized structure
        assert serialized["event_type"] == "deployment"
        assert serialized["status"] == "progress"
        assert serialized["payload"]["test_data"] == "deployment_test"
        assert serialized["kwargs"]["available_replicas"] == 2
        assert serialized["kwargs"]["ready_replicas"] == 1
        assert serialized["kwargs"]["desired_replicas"] == 3
        assert serialized["kwargs"]["phase"] == "Progressing"

        # Deserialize the event
        deserialized_event = deserialize_event(serialized)

        # Verify deserialized event
        assert deserialized_event is not None
        assert isinstance(deserialized_event, DeploymentEvent)
        assert deserialized_event.status == EventStatus.PROGRESS
        assert deserialized_event.available_replicas == 2
        assert deserialized_event.ready_replicas == 1
        assert deserialized_event.desired_replicas == 3
        assert deserialized_event.phase == "Progressing"
        assert deserialized_event.payload["test_data"] == "deployment_test"

    def test_build_event_serialization(self):
        """Test BuildEvent serialization and deserialization."""
        original_event = BuildEvent(
            EventStatus.PROGRESS, stream="Building layer 1/5", payload={"build_id": "abc123"}
        )

        # Serialize the event
        serialized = original_event.serialize()

        # Verify serialized structure
        assert serialized["event_type"] == "build"
        assert serialized["status"] == "progress"
        assert serialized["payload"]["build_id"] == "abc123"
        assert serialized["kwargs"]["stream"] == "Building layer 1/5"

        # Deserialize the event
        deserialized_event = deserialize_event(serialized)

        # Verify deserialized event
        assert deserialized_event is not None
        assert isinstance(deserialized_event, BuildEvent)
        assert deserialized_event.status == EventStatus.PROGRESS
        assert deserialized_event.stream == "Building layer 1/5"
        assert deserialized_event.payload["build_id"] == "abc123"

    def test_pod_event_serialization(self):
        """Test PodEvent serialization and deserialization."""
        original_event = PodEvent(
            EventStatus.PROGRESS,
            phase="MODIFIED",
            container_name="test-container",
            container_state=None,
            payload={"pod_name": "test-pod"},
        )

        # Serialize the event
        serialized = original_event.serialize()

        # Verify serialized structure
        assert serialized["event_type"] == "pod"
        assert serialized["status"] == "progress"
        assert serialized["payload"]["pod_name"] == "test-pod"
        assert serialized["kwargs"]["phase"] == "MODIFIED"
        assert serialized["kwargs"]["container_name"] == "test-container"
        assert serialized["kwargs"]["container_state"] is None

        # Deserialize the event
        deserialized_event = deserialize_event(serialized)

        # Verify deserialized event
        assert deserialized_event is not None
        assert isinstance(deserialized_event, PodEvent)
        assert deserialized_event.status == EventStatus.PROGRESS
        assert deserialized_event.phase == "MODIFIED"
        assert deserialized_event.container_name == "test-container"
        assert deserialized_event.container_state is None
        assert deserialized_event.payload["pod_name"] == "test-pod"

    def test_repository_event_serialization(self):
        """Test RepositoryEvent serialization and deserialization."""
        original_event = RepositoryEvent(
            EventStatus.PROGRESS,
            step=RepositoryEventStep.CLONING,
            payload={"repo_url": "https://github.com/test/repo"},
        )

        # Serialize the event
        serialized = original_event.serialize()

        # Verify serialized structure
        assert serialized["event_type"] == "repository"
        assert serialized["status"] == "progress"
        assert serialized["payload"]["repo_url"] == "https://github.com/test/repo"
        assert serialized["kwargs"]["step"] == "cloning"  # Enum gets converted to string

        # Deserialize the event
        deserialized_event = deserialize_event(serialized)

        # Verify deserialized event
        assert deserialized_event is not None
        assert isinstance(deserialized_event, RepositoryEvent)
        assert deserialized_event.status == EventStatus.PROGRESS
        assert deserialized_event.step == "cloning"  # Will be a string after deserialization
        assert deserialized_event.payload["repo_url"] == "https://github.com/test/repo"

    def test_all_registered_event_types(self):
        """Test that all expected event types are registered."""
        expected_types = {"deployment", "build", "pod", "repository"}

        # Get all registered event types
        registered_types = set(_registry.keys())

        # Verify all expected types are registered
        assert expected_types.issubset(registered_types)

        # Verify each registered type has a valid class
        for event_type, event_class in _registry.items():
            assert hasattr(event_class, 'event_type')
            assert event_class.event_type == event_type

    def test_unknown_event_type_deserialization(self):
        """Test that unknown event types raise ValueError."""
        fake_serialized = {
            "event_type": "unknown_type",
            "status": "progress",
            "message": "Test message",
            "payload": {},
            "kwargs": {},
        }

        # Should raise ValueError for unknown type
        with pytest.raises(ValueError):
            deserialize_event(fake_serialized)

    def test_message_preservation(self):
        """Test that messages are preserved through serialization/deserialization."""
        # Create an event with an exception (fresh event should use format_message)
        original_event = DeploymentEvent(
            EventStatus.ERROR,
            available_replicas=0,
            ready_replicas=0,
            desired_replicas=1,
            exception=ValueError("Connection timeout"),
            payload={"error_context": "test"},
        )

        # Get the dynamic message (should include exception info)
        original_message = original_event.message
        assert "Connection timeout" in original_message

        # Serialize the event
        serialized = original_event.serialize()

        # Verify the computed message is stored in serialized data
        assert serialized["message"] == original_message

        # Deserialize the event
        deserialized_event = deserialize_event(serialized)

        # Verify deserialized event has the exact same message
        assert deserialized_event is not None
        assert deserialized_event.message == original_message
        assert "Connection timeout" in deserialized_event.message

        # The deserialized event should use the stored message, not format_message
        assert deserialized_event._message == original_message
