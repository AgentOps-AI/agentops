import pytest
from pathlib import Path
import json


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
        ("gemini-api-key", "REDACTED"),
        ("x-gemini-api-key", "REDACTED"),
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
        # Add JWT-related headers
        ("x-railway-request-id", "REDACTED"),
        ("x-request-id", "REDACTED"),
        ("x-ratelimit-remaining-tokens", "REDACTED"),
        ("x-ratelimit-reset-requests", "REDACTED"),
        ("x-ratelimit-reset-tokens", "REDACTED"),
        ("x-debug-trace-id", "REDACTED"),
    ]

    def redact_jwt_recursive(obj):
        """Recursively redact JWT tokens from dict/list structures."""
        if obj is None:
            return obj

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and ("jwt" in key.lower()):
                    obj[key] = "REDACTED"
                elif isinstance(value, str) and "eyJ" in value:  # JWT tokens start with 'eyJ'
                    obj[key] = "REDACTED_JWT"
                else:
                    redact_jwt_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                redact_jwt_recursive(item)
        return obj

    def filter_response_headers(response):
        """Filter sensitive headers and body content from response."""
        if not isinstance(response, dict):
            raise ValueError("Response must be a dictionary")

        # Filter headers
        headers = response.get("headers", {})
        if headers:
            headers_lower = {k.lower(): k for k in headers}

            for header, replacement in sensitive_headers:
                header_lower = header.lower()
                if header_lower in headers_lower:
                    headers[headers_lower[header_lower]] = [replacement]

        # Filter response body
        if "body" in response and isinstance(response["body"], dict):
            body_content = response["body"].get("string")
            if body_content is not None:
                try:
                    # Handle JSON response bodies
                    if isinstance(body_content, bytes):
                        body_str = body_content.decode("utf-8")
                    else:
                        body_str = str(body_content)

                    try:
                        body = json.loads(body_str)
                        body = redact_jwt_recursive(body)
                        response["body"]["string"] = json.dumps(body).encode("utf-8")
                    except json.JSONDecodeError:
                        # If not JSON, handle as plain text
                        import re

                        jwt_pattern = r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"
                        body_str = re.sub(jwt_pattern, "REDACTED_JWT", body_str)
                        response["body"]["string"] = body_str.encode("utf-8")
                except (AttributeError, UnicodeDecodeError) as e:
                    raise ValueError(f"Failed to process response body: {str(e)}")

        return response

    def scrub_request_body(request):
        """Scrub sensitive and dynamic data from request body."""
        if not request or not hasattr(request, "body"):
            raise ValueError("Invalid request object")

        if request.body:
            try:
                body_dict = json.loads(request.body)
                if not isinstance(body_dict, dict):
                    raise ValueError("Request body must be a JSON object")

                body_dict = redact_jwt_recursive(body_dict)

                # Handle session creation/update requests
                if request.uri and (
                    request.uri.endswith("/v2/create_session") or request.uri.endswith("/v2/update_session")
                ):
                    session = body_dict.get("session")
                    if session and isinstance(session, dict):
                        # Standardize all dynamic fields
                        for key in session:
                            if key.startswith("_"):  # Internal fields
                                session[key] = ""
                            elif isinstance(session[key], str):  # String fields that might be dynamic
                                if key not in ["end_state", "OS"]:  # Preserve specific fields
                                    session[key] = ""

                        # Standardize known fields
                        session["session_id"] = "SESSION_ID"
                        session["init_timestamp"] = "TIMESTAMP"
                        session["end_timestamp"] = "TIMESTAMP"
                        session["jwt"] = "JWT_TOKEN"
                        session["token_cost"] = ""
                        session["_session_url"] = ""

                        # Standardize host environment
                        if "host_env" in session:
                            session["host_env"] = {
                                "SDK": {"AgentOps SDK Version": None},
                                "OS": {"OS": session.get("host_env", {}).get("OS", {}).get("OS", "Darwin")},
                            }

                        # Reset all counters and states
                        session["event_counts"] = {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
                        session["is_running"] = False

                        # Clear any dynamic lists
                        session["tags"] = []
                        session["video"] = None
                        session["end_state_reason"] = None

                # Handle agent creation requests
                if request.uri and request.uri.endswith("/v2/create_agent"):
                    if "id" in body_dict:
                        body_dict["id"] = "AGENT_ID"

                request.body = json.dumps(body_dict).encode()
            except (json.JSONDecodeError, AttributeError, UnicodeDecodeError) as e:
                raise ValueError(f"Failed to process request body: {str(e)}")

        return request

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
            "huggingface.co",
        ],
        # Header filtering for requests and responses
        "filter_headers": sensitive_headers,
        "before_record_response": filter_response_headers,
        # Add these new options
        "decode_compressed_response": True,
        "record_on_exception": False,
        "allow_playback_repeats": True,
        "before_record_request": scrub_request_body,
    }
