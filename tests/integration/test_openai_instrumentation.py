import pytest
import vcr
import json
import openai
from inline_snapshot import snapshot

@pytest.mark.vcr(cassette_name="test_openai_instrumentation.yaml")
def test_openai_instrumentation(mock_env_keys, agentops_session, exporter, clear_exporter):
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
    assert spans_json == snapshot("""\
[
  {
    "name": "openai.chat",
    "attributes": {
      "llm.request.type": "chat",
      "gen_ai.system": "OpenAI",
      "gen_ai.request.model": "gpt-3.5-turbo",
      "llm.headers": "None",
      "llm.is_streaming": false,
      "gen_ai.openai.api_base": "https://api.openai.com/v1/",
      "gen_ai.prompt.0.role": "user",
      "gen_ai.prompt.0.content": "Write a one-line joke",
      "gen_ai.response.model": "gpt-3.5-turbo-0125",
      "gen_ai.response.id": "chatcmpl-B6lZmK9o76760aFRdvILIQlFOgAzM",
      "llm.usage.total_tokens": 29,
      "gen_ai.usage.completion_tokens": 17,
      "gen_ai.usage.prompt_tokens": 12,
      "gen_ai.completion.0.finish_reason": "stop",
      "gen_ai.completion.0.role": "assistant",
      "gen_ai.completion.0.content": "I told my wife she should embrace her mistakes - she gave me a hug!"
    },
    "status": true
  }
]\
""")