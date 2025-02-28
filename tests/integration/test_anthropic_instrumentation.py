import pytest
import agentops
import vcr
import json
import anthropic

@vcr.use_cassette('tests/integration/cassettes/test_anthropic_instrumentation.yaml')
def test_anthropic_instrumentation(snapshot, exporter):
    """Test that Anthropic API calls are tracked in spans"""
    
    session = agentops.start_session()
    
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=100,
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
        snapshot.assert_match(spans_json, 'anthropic_spans.json')
        
    finally:
        session.end("SUCCEEDED")