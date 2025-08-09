import pytest
import uuid


@pytest.fixture(scope="session")
def mock_request():
    """Create a mock request with a session user_id."""
    from unittest.mock import MagicMock
    from fastapi import Request

    request = MagicMock(spec=Request)
    request.state.session.user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return request
