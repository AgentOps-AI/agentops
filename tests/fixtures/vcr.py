import pytest
from pathlib import Path
import os
from vcr.record_mode import RecordMode
import json

# Define sensitive headers once to avoid duplication
SENSITIVE_HEADERS = [
    # Generic API authentication
    'authorization',
    'x-api-key',
    'api-key',
    'bearer',
    # AgentOps API keys
    'x-agentops-api-key',
    # LLM service API keys
    'openai-api-key',
    'anthropic-api-key',
    'cohere-api-key',
    'x-cohere-api-key',
    'ai21-api-key',
    'x-ai21-api-key',
    'replicate-api-token',
    'huggingface-api-key',
    'x-huggingface-api-key',
    'claude-api-key',
    'x-claude-api-key',
    'x-railway-request-id',
    'X-Railway-Request-Id',
    # Authentication tokens
    'x-api-token',
    'api-token',
    'x-auth-token',
    'x-session-token',
    # OpenAI specific headers
    'openai-organization',
    'x-request-id',
    '__cf_bm',
    '_cfuvid',
    'cf-ray',
    # Rate limit headers
    'x-ratelimit-limit-requests',
    'x-ratelimit-limit-tokens',
    'x-ratelimit-remaining-requests',
    'x-ratelimit-remaining-tokens',
    'x-ratelimit-reset-requests',
    'x-ratelimit-reset-tokens',
    # Mistral headers
    'x-mistral-api-key',
    # Groq headers
    'x-groq-api-key',
    # LiteLLM headers
    'x-litellm-api-key',
    # Ollama headers
    'x-ollama-api-key',
    # TaskWeaver headers
    'x-taskweaver-api-key',
    # Additional provider version headers
    'anthropic-version',
    'cohere-version',
    'x-stainless-lang',
    'x-stainless-arch',
    'x-stainless-os',
    'x-stainless-async',
    'x-stainless-runtime',
    'x-stainless-runtime-version',
    # Additional headers
    'anthropic-organization-id',
    'request-id',
    'x-session-id',
    'x-railway-edge'
]

@pytest.fixture(scope="session")
def vcr_config():
    """Configure VCR.py for recording HTTP interactions."""
    return {
        "filter_headers": SENSITIVE_HEADERS,
        "filter_post_data_parameters": [
            ('api_key', '[REDACTED]'),
            ('session_id', '[REDACTED]'),
            ('jwt', '[REDACTED]')
        ],
        "before_record_response": lambda response: _filter_response(response),
        "before_record_request": lambda request: _filter_request(request),
        "path_transformer": lambda path: path.replace("\\", "/"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "record_mode": RecordMode.ONCE if os.getenv("CI") else RecordMode.NEW_EPISODES,
        "cassette_library_dir": "tests/integration/cassettes",
        "serializer": "yaml"
    }

def _filter_response(response):
    """Filter sensitive data from response"""
    if 'headers' in response:
        headers_to_check = list(response['headers'].keys())
        for header in headers_to_check:
            if any(header.lower() == h.lower() for h in SENSITIVE_HEADERS) or \
               any(sensitive in header.lower() for sensitive in ['key', 'auth', 'jwt', 'token', 'secret']):
                response['headers'][header] = ['[REDACTED]']
    
    if 'body' in response and 'string' in response['body']:
        try:
            is_bytes = isinstance(response['body']['string'], bytes)
            
            if is_bytes:
                body_str = response['body']['string'].decode('utf-8')
            else:
                body_str = response['body']['string']
            
            try:
                body = json.loads(body_str)
                
                if 'jwt' in body:
                    body['jwt'] = '[REDACTED_JWT]'
                if 'session_url' in body:
                    body['session_url'] = '[REDACTED_SESSION_URL]'
                if 'session' in body:
                    if isinstance(body['session'], dict):
                        if 'session_id' in body['session']:
                            body['session']['session_id'] = '[REDACTED_SESSION_ID]'
                        if 'config' in body['session']:
                            if 'api_key' in body['session']['config']:
                                body['session']['config']['api_key'] = '[REDACTED_API_KEY]'
                        if 'host_env' in body['session']:
                            body['session']['host_env'] = '[REDACTED_ENV_DATA]'
                
                filtered_body = json.dumps(body)
                
                if is_bytes:
                    response['body']['string'] = filtered_body.encode('utf-8')
                else:
                    response['body']['string'] = filtered_body
                    
            except json.JSONDecodeError:
                # Not JSON, leave as is
                pass
                
        except Exception as e:
            print(f"Failed to filter response: {e}")
            
    return response

def _filter_request(request):
    """Filter sensitive data from request"""
    headers_to_check = list(request.headers.keys())
    
    for header in headers_to_check:
        # Check if header contains any sensitive terms
        if any(sensitive in header.lower() for sensitive in ['key', 'auth', 'jwt', 'token', 'secret']):
            request.headers[header] = '[REDACTED]'
        # Check against explicit list (case-insensitive)
        elif any(header.lower() == h.lower() for h in SENSITIVE_HEADERS):
            request.headers[header] = '[REDACTED]'
    
    # Filter request body if it exists
    if request.body:
        try:
            # Handle both string and bytes body
            if isinstance(request.body, bytes):
                body = json.loads(request.body.decode('utf-8'))
            else:
                body = json.loads(request.body)
                
            # Recursively filter sensitive data in body
            body = _filter_sensitive_data(body)
            
            # Convert back to string
            filtered_body = json.dumps(body)
            
            # Convert back to bytes if original was bytes
            if isinstance(request.body, bytes):
                request.body = filtered_body.encode('utf-8')
            else:
                request.body = filtered_body
        except:
            pass
    
    return request

def _filter_sensitive_data(data):
    """Recursively filter sensitive data in dictionaries"""
    if isinstance(data, dict):
        for key in data:
            if any(sensitive in key.lower() for sensitive in ['key', 'auth', 'jwt', 'secret', 'session']):
                data[key] = '[REDACTED]'
            else:
                data[key] = _filter_sensitive_data(data[key])
    elif isinstance(data, list):
        data = [_filter_sensitive_data(item) for item in data]
    return data
