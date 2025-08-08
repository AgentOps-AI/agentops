"""
Tests for the security features of the auth module.
This covers both the rate limiter and security header validations.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException

from agentops.auth.views import _validate_request, public_route
from agentops.common import rate_limit
from agentops.common.environment import APP_URL, API_DOMAIN, RATE_LIMIT_COUNT, REDIS_HOST, REDIS_PORT
from agentops.common.route_config import BaseView

# Mark to skip rate limit tests when Redis is not available
redis_required = pytest.mark.skipif(
    not (REDIS_HOST and REDIS_PORT), 
    reason="Rate limit tests require Redis (REDIS_HOST and REDIS_PORT env vars)"
)


@pytest.fixture
def mock_request():
    """Create a mock request with appropriate headers for testing."""
    mock = MagicMock(spec=Request)
    mock.headers = {
        "x-forwarded-for": "192.168.0.1",
        "x-forwarded-host": API_DOMAIN,
        "origin": APP_URL,
        "referer": f"{APP_URL}/signin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
    }
    return mock


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """
    Clear rate limit data for test IPs before and after tests.
    Note: This fixture will run even if Redis is not available,
    but the rate_limit.clear() calls will be no-ops in that case.
    """
    test_ips = [
        "192.168.0.1",  # Main test IP
        "192.168.0.2",  # Secondary test IP
    ]
    for ip in test_ips:
        rate_limit.clear(ip)
    yield
    for ip in test_ips:
        rate_limit.clear(ip)


@patch("agentops.auth.views.API_URL", "http://localhost:8000")
def test_localhost_bypass(mock_request):
    """Test that localhost requests bypass all security checks."""
    # Should not raise exceptions even with bad headers
    mock_request.headers = {
        "x-forwarded-for": "",  # This would normally trigger an error
    }
    _validate_request(mock_request)  # Should not raise exceptions


@patch("agentops.auth.views.API_URL", "https://api.agentops.ai")
def test_header_validations(mock_request):
    """Test that requests with invalid headers are rejected."""
    ip = "192.168.0.1"
    mock_request.headers["x-forwarded-for"] = ip
    rate_limit.clear(ip)  # Ensure no rate limiting interference

    # Test 2.1: Missing IP
    mock_request.headers.pop("x-forwarded-for")
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(mock_request)
    assert exc_info.value.status_code == 500

    # Test 2.2: Invalid host
    mock_request.headers["x-forwarded-for"] = ip
    mock_request.headers["x-forwarded-host"] = "evil-site.com"
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(mock_request)
    assert exc_info.value.status_code == 500

    # Test 2.3: Invalid origin
    mock_request.headers["x-forwarded-host"] = API_DOMAIN
    mock_request.headers["origin"] = "https://evil-site.com"
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(mock_request)
    assert exc_info.value.status_code == 500

    # Test 2.4: Invalid referrer
    mock_request.headers["origin"] = APP_URL
    mock_request.headers["referer"] = "https://evil-site.com/page"
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(mock_request)
    assert exc_info.value.status_code == 500

    # Test 2.5: Missing user agent
    mock_request.headers["referer"] = f"{APP_URL}/signin"
    mock_request.headers.pop("user-agent")
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(mock_request)
    assert exc_info.value.status_code == 500


@redis_required
@patch("agentops.auth.views.API_URL", "https://api.agentops.ai")
def test_rate_limiting_basic(mock_request):
    """Test that the rate limiter blocks requests after the limit is exceeded."""
    ip = "192.168.0.1"
    mock_request.headers["x-forwarded-for"] = ip

    # Clear any existing data
    rate_limit.clear(ip)

    # Verify initial state
    assert rate_limit.get_count(ip) == 0
    assert not rate_limit.is_blocked(ip)

    # Make requests up to the limit
    for i in range(RATE_LIMIT_COUNT):
        _validate_request(mock_request)
        assert rate_limit.get_count(ip) == i + 1
        assert not rate_limit.is_blocked(ip)

    # The next request should exceed the limit
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(mock_request)
    assert exc_info.value.status_code == 429
    assert rate_limit.is_blocked(ip)


@redis_required
@patch("agentops.auth.views.API_URL", "https://api.agentops.ai")
def test_rate_limit_ip_isolation():
    """Test that different IPs have separate rate limits."""
    ip1 = "192.168.0.1"
    ip2 = "192.168.0.2"

    # Create two requests with different IPs
    request1 = MagicMock(spec=Request)
    request1.headers = {
        "x-forwarded-for": ip1,
        "x-forwarded-host": API_DOMAIN,
        "origin": APP_URL,
        "referer": f"{APP_URL}/signin",
        "user-agent": "Mozilla/5.0 Chrome/91.0.4472.124",
    }

    request2 = MagicMock(spec=Request)
    request2.headers = {
        "x-forwarded-for": ip2,
        "x-forwarded-host": API_DOMAIN,
        "origin": APP_URL,
        "referer": f"{APP_URL}/signin",
        "user-agent": "Mozilla/5.0 Chrome/91.0.4472.124",
    }

    # Exceed the limit for the first IP
    for _ in range(RATE_LIMIT_COUNT + 1):
        rate_limit.record_interaction(ip1)

    # Verify the first IP is blocked
    assert rate_limit.is_blocked(ip1)
    with pytest.raises(HTTPException) as exc_info:
        _validate_request(request1)
    assert exc_info.value.status_code == 429

    # But the second IP should not be blocked
    assert not rate_limit.is_blocked(ip2)
    _validate_request(request2)  # Should not raise exceptions


@patch("agentops.auth.views.API_URL", "https://api.agentops.ai")
def test_public_route_decorator():
    """Test that the public_route decorator properly marks functions and validates requests."""

    # Check that the decorator properly marks functions
    @public_route
    async def test_view(request):
        return "test response"

    # Verify the function is marked as public
    assert hasattr(test_view, "is_public")
    assert test_view.is_public is True


@patch("agentops.auth.views.API_URL", "https://api.agentops.ai")
def test_public_route_decorator_class_based_view():
    """Test that the public_route decorator properly works with class-based views."""

    # Test with a class-based view
    @public_route
    class TestView(BaseView):
        async def __call__(self):
            return "test class response"

    # Verify the class __call__ method is marked as public
    assert hasattr(TestView.__call__, "is_public")
    assert TestView.__call__.is_public is True

    # Test that the decorator validates requests properly for class-based views
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        "x-forwarded-for": "192.168.0.1",
        "x-forwarded-host": API_DOMAIN,
        "origin": APP_URL,
        "referer": f"{APP_URL}/signin",
        "user-agent": "Mozilla/5.0 Chrome/91.0.4472.124",
    }

    # Create an instance and test validation
    view_instance = TestView(mock_request)
    
    # The wrapped __call__ method should validate the request
    with patch('agentops.auth.views._validate_request') as mock_validate:
        import asyncio
        asyncio.run(view_instance())
        # Verify that _validate_request was called with the instance's request
        mock_validate.assert_called_once_with(mock_request)


@patch("agentops.auth.views.API_URL", "https://api.agentops.ai")  
def test_public_route_decorator_invalid_class():
    """Test that the public_route decorator raises TypeError for non-BaseView classes."""
    
    # Should raise TypeError when decorating a non-BaseView class
    with pytest.raises(TypeError, match="must inherit from BaseView"):
        @public_route
        class BadView:
            async def __call__(self):
                return "invalid"
