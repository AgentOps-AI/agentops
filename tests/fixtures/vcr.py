import pytest
from pathlib import Path


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

    return {
        # Basic VCR configuration
        "serializer": "yaml",
        "cassette_library_dir": str(vcr_cassettes),
        "match_on": ["uri", "method", "body"],
        "record_mode": "once",
        "ignore_localhost": True,
        "ignore_hosts": [
            "pypi.org",
            # Add OTEL endpoints to ignore list
            "localhost:4317",  # Default OTLP gRPC endpoint
            "localhost:4318",  # Default OTLP HTTP endpoint
            "127.0.0.1:4317",
            "127.0.0.1:4318",
        ],
        # Header filtering for requests and responses
        "filter_headers": sensitive_headers,
        "before_record_response": filter_response_headers,
        # Add these new options
        "decode_compressed_response": True,
        "record_on_exception": False,
        "allow_playback_repeats": True,
    }
