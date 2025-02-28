import pytest
from haystack.components.generators import OpenAIGenerator
import agentops

def test_haystack_instrumentation(exporter):
    """Test that haystack is instrumented"""
    
    # Create a session for tracking
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
        
        # Verify the response from OpenAI
        assert response is not None
        assert isinstance(response, dict)
        assert "replies" in response
        assert len(response["replies"]) > 0
        assert response["replies"][0] is not None
        
    finally:
        session.end("SUCCEEDED")