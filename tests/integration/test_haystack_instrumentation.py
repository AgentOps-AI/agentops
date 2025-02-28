import pytest
import agentops
import json
import vcr
from haystack.components.generators import OpenAIGenerator

@vcr.use_cassette('tests/integration/cassettes/test_haystack_instrumentation.yaml')
def test_haystack_instrumentation(exporter, snapshot):
    """Test that haystack is instrumented"""
    
    session = agentops.start_session()
    
    try:
        client = OpenAIGenerator(model="o3-mini")
        response = client.run("What's Natural Language Processing? Be brief.")
        
        finished_spans = exporter.get_finished_spans()
        
        # Assert that spans were created
        assert len(finished_spans) > 0, "No spans were recorded"
        
        # Check that at least one span has "haystack" in its name
        haystack_spans = [span for span in finished_spans if "haystack" in span.name]
        assert len(haystack_spans) > 0, "No haystack spans were found"
        
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
        snapshot.assert_match(spans_json, 'haystack_spans.json')
        
    finally:
        session.end("SUCCEEDED")