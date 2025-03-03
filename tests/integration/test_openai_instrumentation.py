import json

import openai
import pytest
import vcr
from inline_snapshot import snapshot


@pytest.mark.vcr(cassette_name="test_openai_instrumentation.yaml")
def test_openai_instrumentation(agentops_session, exporter, clear_exporter):
    """Test that OpenAI API calls are tracked in spans"""
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Write a one-line joke"}]
    )
    
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
