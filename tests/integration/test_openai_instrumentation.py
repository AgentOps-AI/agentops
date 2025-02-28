import pytest
import agentops
import vcr
import json
import openai

@vcr.use_cassette('tests/integration/cassettes/test_openai_instrumentation.yaml')
def test_openai_instrumentation(snapshot, exporter):
    """Test that OpenAI API calls are tracked in spans"""
    
    session = agentops.start_session()
    
    try:
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
        snapshot.assert_match(spans_json, 'openai_spans.json')
        
    finally:
        session.end("SUCCEEDED")