import os
from agentops.api.log_config import logger

# Generate an AUTH_COOKIE_SECRET with:
# import secrets; print(secrets.token_hex(32))
AUTH_COOKIE_SECRET: str | None = os.getenv("AUTH_COOKIE_SECRET")

AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "session_id")
AUTH_JWT_ALGO = "HS256"  # this is for our internal JWT on the session cookie


# Sessions are extended on every interaction with the API. This means a user
# won't need to log in again as long as they interact with the API at least once
# every 7 days, for up to 30 days while the cookie remains valid.

# extend sessions on every interaction
AUTH_EXTEND_SESSIONS: bool = True
# session expiry relates to the record stored in the cache backend
AUTH_SESSION_EXPIRY = 60 * 60 * 24 * 7  # 7 days in seconds
# cookie expiry relates to the cookie stored in the browser
AUTH_COOKIE_EXPIRY = 60 * 60 * 24 * 30  # 30 days in seconds

SUPABASE_JWT_SECRET: str = os.getenv("JWT_SECRET_KEY")


if not AUTH_COOKIE_SECRET:
    logger.error("[agentops.auth.environment] AUTH_COOKIE_SECRET is not configured")

if not SUPABASE_JWT_SECRET:
    logger.warning("[agentops.auth.environment] No JWT_SECRET_KEY set")


AUTH_ADDITIONAL_REFERERS = [
    # Add any additional referers that should be allowed to access the auth app
    "https://accounts.google.com/",
    "https://github.com/",
]
