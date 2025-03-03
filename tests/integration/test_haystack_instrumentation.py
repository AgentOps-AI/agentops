import pytest
import agentops
import json
import vcr
from haystack.components.generators import OpenAIGenerator
from inline_snapshot import snapshot

@pytest.mark.vcr(cassette_name="test_haystack_instrumentation.yaml")
def test_haystack_instrumentation(mock_env_keys, agentops_session, exporter, clear_exporter):
    """Test that haystack is instrumented"""
    
    client = OpenAIGenerator(model="o3-mini")
    response = client.run("What's Natural Language Processing? Be brief.")
    
    finished_spans = exporter.get_finished_spans()
    
    # Assert that spans were created
    assert len(finished_spans) > 0, "No spans were recorded"
    
    spans_data = [
        {
            "name": span.name,
            "attributes": dict(span.attributes),
            "status": span.status.is_ok
        }
        for span in finished_spans
    ]
    
    spans_json = json.dumps(spans_data, indent=2)
    
    # Verify the spans using snapshot
    assert spans_json == snapshot()