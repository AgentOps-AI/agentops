"""Regression tests for required session-cookie signing configuration."""

from uuid import uuid4

import jwt
import pytest

from agentops.auth import environment
from agentops.auth import views
from agentops.auth.exceptions import AuthException
from agentops.auth.session import Session


def test_missing_cookie_secret_has_no_committed_fallback(monkeypatch):
    """Cookie signing must fail closed when AUTH_COOKIE_SECRET is absent."""
    monkeypatch.delenv("AUTH_COOKIE_SECRET", raising=False)
    monkeypatch.setattr(environment, "AUTH_COOKIE_SECRET", None)
    monkeypatch.setattr(views, "AUTH_COOKIE_SECRET", None)

    assert environment.AUTH_COOKIE_SECRET != "your_cookie_signing_secret"
    session = Session(session_id=uuid4(), user_id=uuid4())

    with pytest.raises(AuthException, match="AUTH_COOKIE_SECRET"):
        views._encode_session_cookie(session)
    with pytest.raises(AuthException, match="AUTH_COOKIE_SECRET"):
        views._decode_session_cookie("not-a-token")


def test_configured_cookie_secret_signs_and_verifies_session_cookie(monkeypatch):
    """A deployment-provided secret continues to support cookie authentication."""
    secret = "test-only-cookie-secret"
    monkeypatch.setattr(views, "AUTH_COOKIE_SECRET", secret)
    session = Session(session_id=uuid4(), user_id=uuid4())
    monkeypatch.setattr(Session, "get", classmethod(lambda cls, session_id: session))

    token = views._encode_session_cookie(session)

    decoded = jwt.decode(token, secret, algorithms=[views.AUTH_JWT_ALGO])
    assert decoded["session_id"] == str(session.session_id)
    assert views._decode_session_cookie(token) is session
