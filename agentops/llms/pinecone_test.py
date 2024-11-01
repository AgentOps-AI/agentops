import pytest
from unittest.mock import Mock, patch
import pinecone
from agentops import AgentOps

@pytest.fixture
def setup():
    ao = AgentOps(api_key="d907f545-c7cb-4352-add5-97bf774f3956")
    pc = pinecone.Pinecone(api_key="pcsk_3jKXv1_T4ymogWwJEQffj6MPBxsyFkGdUXdM1LaurKdnK6CK6dPAZ1aYumPPiqX9URmWU9")
    return ao, pc

def test_vector_operations(setup):
    ao, pc = setup
    
    # Test vector operations
    index = pc.Index("test-index")
    
    # Test upsert
    vectors = [
        {"id": "1", "values": [1.0, 2.0], "metadata": {"text": "test"}}
    ]
    response = index.upsert(vectors=vectors)
    
    # Verify event was recorded
    assert len(ao.events) == 1
    assert ao.events[0].event_type == "vector"
    assert ao.events[0].operation_type == "upsert"
    assert ao.events[0].vector_count == 1

def test_assistant_operations(setup):
    ao, pc = setup
    
    # Test assistant creation
    assistant = pc.assistant.create_assistant(
        assistant_name="test-assistant",
        instructions="Test instructions"
    )
    
    # Verify assistant creation event
    assert len(ao.events) == 1
    assert ao.events[0].event_type == "assistant"
    assert ao.events[0].operation_type == "create_assistant"
    
    # Test chat completion
    response = assistant.chat_completions(
        messages=[{"role": "user", "content": "Hello"}]
    )
    
    # Verify chat event
    assert len(ao.events) == 2
    assert ao.events[1].event_type == "assistant"
    assert ao.events[1].operation_type == "chat_completion_assistant"