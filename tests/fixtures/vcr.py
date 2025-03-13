import pytest
from pathlib import Path
import os
from vcr.record_mode import RecordMode


@pytest.fixture(scope="session")
def vcr_config():
    """Configure VCR.py for recording HTTP interactions.

    This fixture sets up VCR.py with:
    - YAML serialization
    - Cassette storage in fixtures/recordings
    - Comprehensive header filtering for API keys and sensitive data
    - Request matching on URI, method, and body
    """
    # Define cassette storage location
    vcr_cassettes = Path(__file__).parent / "recordings"
    vcr_cassettes.mkdir(parents=True, exist_ok=True)

    # Define sensitive headers to filter
    sensitive_headers = [
        # Generic API authentication
        ("authorization", "REDACTED"),
        ("x-api-key", "REDACTED"),
        ("api-key", "REDACTED"),
        ("bearer", "REDACTED"),
        # AgentOps API keys
        ("x-agentops-api-key", "REDACTED"),
        # LLM service API keys
        ("openai-api-key", "REDACTED"),
        ("anthropic-api-key", "REDACTED"),
        ("cohere-api-key", "REDACTED"),
        ("x-cohere-api-key", "REDACTED"),
        ("ai21-api-key", "REDACTED"),
        ("x-ai21-api-key", "REDACTED"),
        ("replicate-api-token", "REDACTED"),
        ("huggingface-api-key", "REDACTED"),
        ("x-huggingface-api-key", "REDACTED"),
        ("claude-api-key", "REDACTED"),
        ("x-claude-api-key", "REDACTED"),
        ("x-railway-request-id", "REDACTED"),
        ("X-Railway-Request-Id", "REDACTED"),
        # Authentication tokens
        ("x-api-token", "REDACTED"),
        ("api-token", "REDACTED"),
        ("x-auth-token", "REDACTED"),
        ("x-session-token", "REDACTED"),
        # OpenAI specific headers
        ("openai-organization", "REDACTED"),
        ("x-request-id", "REDACTED"),
        ("__cf_bm", "REDACTED"),
        ("_cfuvid", "REDACTED"),
        ("cf-ray", "REDACTED"),
        # Rate limit headers
        ("x-ratelimit-limit-requests", "REDACTED"),
        ("x-ratelimit-limit-tokens", "REDACTED"),
        ("x-ratelimit-remaining-requests", "REDACTED"),
        ("x-ratelimit-remaining-tokens", "REDACTED"),
        ("x-ratelimit-reset-requests", "REDACTED"),
        ("x-ratelimit-reset-tokens", "REDACTED"),
        # Mistral headers
        ("x-mistral-api-key", "REDACTED"),
        # Groq headers
        ("x-groq-api-key", "REDACTED"),
        # LiteLLM headers
        ("x-litellm-api-key", "REDACTED"),
        # Ollama headers
        ("x-ollama-api-key", "REDACTED"),
        # TaskWeaver headers
        ("x-taskweaver-api-key", "REDACTED"),
        # Additional provider version headers
        ("anthropic-version", "REDACTED"),
        ("cohere-version", "REDACTED"),
        ("x-stainless-lang", "REDACTED"),
        ("x-stainless-arch", "REDACTED"),
        ("x-stainless-os", "REDACTED"),
        ("x-stainless-async", "REDACTED"),
        ("x-stainless-runtime", "REDACTED"),
        ("x-stainless-runtime-version", "REDACTED"),
    ]

    def filter_response_headers(response):
        """Filter sensitive headers from response."""
        headers = response["headers"]
        headers_lower = {k.lower(): k for k in headers}  # Map of lowercase -> original header names

        for header, replacement in sensitive_headers:
            header_lower = header.lower()
            if header_lower in headers_lower:
                # Replace using the original header name from the response
                original_header = headers_lower[header_lower]
                headers[original_header] = replacement
        return response

    vcr_config = {
        "filter_headers": [
            "authorization",
            "Authorization",
            "X-OpenAI-Client-User-Agent",
        ],
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "record_mode": RecordMode.ONCE if os.getenv("CI") else RecordMode.NEW_EPISODES,
        "path_transformer": lambda path: path.replace("\\", "/"),
        "record_on_exception": False,
    }

    return vcr_config
