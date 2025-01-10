import pytest
from pathlib import Path

@pytest.fixture(scope="module")
def vcr_config():
    """Configure VCR.py for recording HTTP interactions.
    
    This fixture sets up VCR.py with:
    - YAML serialization
    - Cassette storage in fixtures/recordings
    - Comprehensive header filtering for API keys and sensitive data
    - Request matching on URI, method, and body
    """
    # Define cassette storage location
    vcr_cassettes = Path(__file__).parent / "fixtures" / "recordings"
    vcr_cassettes.mkdir(parents=True, exist_ok=True)

    # Define sensitive headers to filter
    sensitive_headers = [
        # Generic API authentication
        ("authorization", "REDACTED"),
        ("x-api-key", "REDACTED"),
        ("api-key", "REDACTED"),
        ("bearer", "REDACTED"),
        
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
    ]

    return {
        # Basic VCR configuration
        "serializer": "yaml",
        "cassette_library_dir": str(vcr_cassettes),
        "match_on": ["uri", "method", "body"],
        "record_mode": "once",
        
        # Header filtering
        "filter_headers": sensitive_headers,
    }
