"""
Tests for the session cookie JWT helpers.

The session cookie is signed with `AUTH_COOKIE_SECRET`. These tests pin two
properties:

1. A cookie signed with the literal that used to be committed as the fallback
   secret must NOT verify, so the known-key forgery path stays closed.
2. Encoding and decoding a session cookie round-trips the session ID.
"""

from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest

from agentops.auth import views as auth_views
from agentops.auth.environment import AUTH_COOKIE_SECRET, AUTH_JWT_ALGO
from agentops.auth.exceptions import AuthException
from agentops.auth.session import Session

# The literal that used to be the committed fallback in `auth/environment.py`.
# It is now only referenced here, to prove it can no longer verify a cookie.
LEGACY_DEV_SECRET = "your_cookie_signing_secret"


def _forge_cookie(session_id: str, secret: str) -> str:
    """Mint a session cookie signed with an arbitrary secret."""
    return jwt.encode({"session_id": session_id}, secret, algorithm=AUTH_JWT_ALGO)


def test_committed_fallback_secret_is_not_in_use():
    """The signing secret must never be the value that was committed to the repo."""
    assert AUTH_COOKIE_SECRET != LEGACY_DEV_SECRET
    assert AUTH_COOKIE_SECRET


def test_cookie_signed_with_legacy_secret_is_rejected():
    """A forged cookie signed with the old committed key must not decode."""
    forged = _forge_cookie(str(uuid4()), LEGACY_DEV_SECRET)

    with pytest.raises(AuthException, match="Could not decode internal session JWT."):
        auth_views._decode_session_cookie(forged)


def test_cookie_signed_with_legacy_secret_is_rejected_even_for_known_session():
    """Signature verification happens before the session lookup, so a forged
    cookie cannot be redeemed even when it names a session that exists."""
    session = Session(session_id=uuid4(), user_id=uuid4())
    forged = _forge_cookie(str(session.session_id), LEGACY_DEV_SECRET)

    with patch.object(auth_views.Session, "get", return_value=session):
        with pytest.raises(AuthException, match="Could not decode internal session JWT."):
            auth_views._decode_session_cookie(forged)


def test_session_cookie_round_trip():
    """A cookie signed with the configured secret decodes back to its session."""
    session = Session(session_id=uuid4(), user_id=uuid4())
    cookie = auth_views._encode_session_cookie(session)

    with patch.object(auth_views.Session, "get", return_value=session) as get_session:
        assert auth_views._decode_session_cookie(cookie) == session

    get_session.assert_called_once_with(str(session.session_id))


def test_decoding_unknown_session_returns_none():
    """A well-signed cookie for a session that no longer exists returns None."""
    session = Session(session_id=uuid4(), user_id=uuid4())
    cookie = auth_views._encode_session_cookie(session)

    with patch.object(auth_views.Session, "get", return_value=None):
        assert auth_views._decode_session_cookie(cookie) is None


def test_cookie_payload_only_contains_session_id():
    """The cookie carries the session ID and nothing else."""
    session = Session(session_id=uuid4(), user_id=uuid4())
    cookie = auth_views._encode_session_cookie(session)

    decoded = jwt.decode(cookie, AUTH_COOKIE_SECRET, algorithms=[AUTH_JWT_ALGO])
    assert decoded == {"session_id": str(session.session_id)}
