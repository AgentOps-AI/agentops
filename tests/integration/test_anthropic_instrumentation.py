import json

import anthropic
import pytest
import vcr
from inline_snapshot import snapshot

import agentops
from tests.fixtures.vcr import _filter_request, _filter_response, vcr_config


@pytest.mark.vcr(cassette_name="test_anthropic_instrumentation.yaml")
def test_anthropic_instrumentation(agentops_session, exporter, clear_exporter):
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

    assert json.dumps(spans_data, indent=2) == snapshot()
