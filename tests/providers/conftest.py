from typing import TYPE_CHECKING
import vcr
from vcr.record_mode import RecordMode
import pytest
import os
from collections import defaultdict

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# INFO: When we are ready, we could move this to global `tests/conftest.py`

# Store VCR stats across the session
vcr_session_stats = defaultdict(lambda: {"total": 0, "played": 0, "new": 0})

# Configure VCR
vcr_config = vcr.VCR(
    record_mode=RecordMode.ONCE,
    match_on=["method", "scheme", "host", "port", "path", "query"],
    filter_headers=[
        "authorization",
        "x-api-key",
        "api-key",
        "bearer",
        "openai-api-key",
        "anthropic-api-key",
        # Additional common API authentication headers
        "x-api-token",
        "api-token",
        "x-auth-token",
        "x-session-token",
        # LLM specific headers
        "cohere-api-key",
        "x-cohere-api-key",
        "ai21-api-key",
        "x-ai21-api-key",
        "replicate-api-token",
        "huggingface-api-key",
        "x-huggingface-api-key",
        "claude-api-key",
        "x-claude-api-key",
        # OpenAI specific headers
        "openai-organization",
        "x-request-id",
        "__cf_bm",
        "_cfuvid",
        "cf-ray",
        # Rate limit headers that may expose account details
        "x-ratelimit-limit-requests",
        "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-requests",
        "x-ratelimit-reset-tokens",
    ],
    # Filter out any api keys from query parameters
    filter_query_parameters=["api_key", "api-key", "token"],
    # Ignore requests to internal/package management APIs
    ignore_hosts=["api.agentops.ai", "pypi.org", "files.pythonhosted.org", "upload.pypi.org", "test.pypi.org"],
)


def pytest_sessionfinish(session):
    """Print VCR stats at the end of the session"""
    if vcr_session_stats:
        print("\n=== VCR Session Stats ===")
        for test_dir, stats in vcr_session_stats.items():
            if stats["new"] > 0:  # Only show directories with new recordings
                print(f"\n📁 {os.path.basename(test_dir)}")
                print(f"   ├─ Total Requests: {stats['total']}")
                print(f"   ├─ Played: {stats['played']}")
                print(f"   └─ New: {stats['new']}")
        print("=======================\n")


# Store VCR stats across the session
vcr_session_stats = defaultdict(lambda: {"total": 0, "played": 0, "new": 0})


@pytest.fixture
def vcr_cassette(request):
    """Provides VCR cassette with standard LLM API filtering"""
    # Get the directory of the test file
    test_dir = os.path.dirname(request.module.__file__)
    cassette_dir = os.path.join(test_dir, ".cassettes")
    os.makedirs(cassette_dir, exist_ok=True)

    cassette_path = os.path.join(cassette_dir, f"{request.node.name}.yaml")

    # Override the cassette dir for this specific cassette
    with vcr.use_cassette(
        cassette_path,
        record_mode=vcr_config.record_mode,
        match_on=vcr_config.match_on,
        filter_headers=vcr_config.filter_headers,
        filter_query_parameters=vcr_config.filter_query_parameters,
        ignore_hosts=vcr_config.ignore_hosts,
    ) as cassette:
        yield cassette

        if len(cassette.requests) > 0:
            new_recordings = len(cassette.responses) - cassette.play_count
            if new_recordings > 0:
                # Update session stats
                vcr_session_stats[test_dir]["total"] += len(cassette.requests)
                vcr_session_stats[test_dir]["played"] += cassette.play_count
                vcr_session_stats[test_dir]["new"] += new_recordings
