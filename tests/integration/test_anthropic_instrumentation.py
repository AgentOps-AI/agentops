import pytest
import agentops
import vcr
import json
import anthropic
from inline_snapshot import snapshot
from tests.fixtures.vcr import vcr_config, _filter_request, _filter_response

@pytest.mark.vcr(cassette_name="test_anthropic_instrumentation.yaml")
def test_anthropic_instrumentation(mock_env_keys, agentops_session, exporter, clear_exporter):
    """Test that Anthropic API calls are tracked in spans using inline snapshots"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=100,
        messages=[{"role": "user", "content": "Write a one-line joke"}]
    )

    finished_spans = exporter.get_finished_spans()

    assert finished_spans, "No spans were recorded"

    spans_data = [
        {
            "name": span.name,
            "attributes": dict(span.attributes),
            "status": span.status.is_ok
        }
        for span in finished_spans
    ]

    assert json.dumps(spans_data, indent=2) == snapshot("""\
[
  {
    "name": "anthropic.chat",
    "attributes": {
      "gen_ai.system": "Anthropic",
      "llm.request.type": "completion",
      "gen_ai.request.model": "claude-3-5-sonnet-20240620",
      "gen_ai.prompt.0.content": "Write a one-line joke",
      "gen_ai.prompt.0.role": "user",
      "gen_ai.response.model": "claude-3-5-sonnet-20240620",
      "gen_ai.response.id": "msg_019H42Yhpf2dnfj68Y1AdK1T",
      "gen_ai.completion.0.finish_reason": "end_turn",
      "gen_ai.completion.0.role": "assistant",
      "gen_ai.completion.0.content": "Why don't scientists trust atoms? Because they make up everything!",
      "gen_ai.usage.prompt_tokens": 13,
      "gen_ai.usage.completion_tokens": 16,
      "llm.usage.total_tokens": 29,
      "gen_ai.usage.cache_read_input_tokens": 0,
      "gen_ai.usage.cache_creation_input_tokens": 0
    },
    "status": true
  }
]\
""")