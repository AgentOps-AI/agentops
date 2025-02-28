import pytest
import anthropic
import agentops

def test_anthropic_instrumentation(exporter):
    """Test that Anthropic API calls are tracked in spans"""
    
    # Create a session for tracking
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
        
        # Optionally, you can check for specific attributes in the spans
        for span in finished_spans:
            assert "anthropic" in span.name, "Expected span name not found"
            assert span.status.is_ok, "Span status should be OK"
        
        # Verify the response from Anthropic
        assert response.content[0].text is not None
        
    finally:
        session.end("SUCCEEDED")