import pytest
import os
os.environ["OPENAI_API_KEY"] = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
os.environ["ANTHROPIC_API_KEY"] = "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
os.environ["AGENTOPS_API_KEY"] = "00000000-0000-0000-0000-000000000000"
import agentops
import vcr
import json
import openai
from inline_snapshot import snapshot

@vcr.use_cassette('tests/integration/cassettes/test_openai_instrumentation.yaml')
def test_openai_instrumentation(exporter):
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
      "gen_ai.response.id": "chatcmpl-B62oRQ6xvkVtALnBvWP7xaqu9EeB8",
      "llm.usage.total_tokens": 28,
      "gen_ai.usage.completion_tokens": 16,
      "gen_ai.usage.prompt_tokens": 12,
      "gen_ai.completion.0.finish_reason": "stop",
      "gen_ai.completion.0.role": "assistant",
      "gen_ai.completion.0.content": "I used to play piano by ear, but now I use my hands."
    },
    "status": true
  },
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
      "gen_ai.response.id": "chatcmpl-B62oRQ6xvkVtALnBvWP7xaqu9EeB8",
      "llm.usage.total_tokens": 28,
      "gen_ai.usage.completion_tokens": 16,
      "gen_ai.usage.prompt_tokens": 12,
      "gen_ai.completion.0.finish_reason": "stop",
      "gen_ai.completion.0.role": "assistant",
      "gen_ai.completion.0.content": "I used to play piano by ear, but now I use my hands."
    },
    "status": true
  }
]\
""")
        
    finally:
        session.end("SUCCEEDED")