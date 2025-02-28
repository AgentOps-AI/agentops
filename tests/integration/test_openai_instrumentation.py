import pytest
import openai
import agentops

def test_openai_instrumentation(exporter):
    """Test that OpenAI API calls are tracked in spans"""
    
    # Create a session for tracking
    session = agentops.start_session()
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Write a one-line joke"}]
        )
        
        finished_spans = exporter.get_finished_spans()
        
        # Assert that spans were created
        assert len(finished_spans) > 0, "No spans were recorded"
        
        # Optionally, you can check for specific attributes in the spans
        for span in finished_spans:
            assert "openai" in span.name, "Expected span name not found"
            assert span.status.is_ok, "Span status should be OK"
        
        # Verify the response from OpenAI
        assert response.choices[0].message.content is not None
        
    finally:
        session.end("SUCCEEDED")