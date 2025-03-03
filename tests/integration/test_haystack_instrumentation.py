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
    assert spans_json == snapshot("""\
[
  {
    "name": "openai.chat",
    "attributes": {
      "llm.request.type": "chat",
      "gen_ai.system": "OpenAI",
      "gen_ai.request.model": "o3-mini",
      "llm.headers": "None",
      "llm.is_streaming": false,
      "gen_ai.openai.api_base": "https://api.openai.com/v1/",
      "gen_ai.prompt.0.role": "user",
      "gen_ai.prompt.0.content": "What's Natural Language Processing? Be brief.",
      "gen_ai.response.model": "o3-mini-2025-01-31",
      "gen_ai.response.id": "chatcmpl-B6lblB79zMADeHyPBRKEMMOmiAMfF",
      "gen_ai.openai.system_fingerprint": "fp_42bfad963b",
      "llm.usage.total_tokens": 181,
      "gen_ai.usage.completion_tokens": 167,
      "gen_ai.usage.prompt_tokens": 14,
      "gen_ai.completion.0.finish_reason": "stop",
      "gen_ai.completion.0.role": "assistant",
      "gen_ai.completion.0.content": "Natural Language Processing (NLP) is a branch of artificial intelligence that focuses on enabling computers to understand, interpret, and generate human language."
    },
    "status": true
  },
  {
    "name": "haystack.openai.completion",
    "attributes": {
      "gen_ai.system": "OpenAI",
      "llm.request.type": "completion",
      "gen_ai.completion.0.content": "replies",
      "gen_ai.completion.1.content": "meta"
    },
    "status": true
  }
]\
""")