# HTTP only cookie- allowed to be accessed during requests only; not accessible to javascript
# set to agentops.ai domain to share across subdomains
# store session ID in cookie, reference central session store (redis?)
# extend session expiration +30 mins when it is used to extend login
# require MFA when editing sensitive information

# supabase returns the tokens as part of the URL hash, which makes them harder to leak;
# they won't show up in logs/proxies/etc but we must call window.location.replace to
# remove them from the browser history

# we use the returned hash params to query the supabase backed which returns a
# Supabase JWT, containing the user_id, among other fields.
# after validating that JWT, we create our own session ID, store it in the session
# store backend, and then JWT-encode the session_id before storing it as an
# HTTP-only cookie

# since we host the auth callback on the api subdomain it doesn't need to live
# across domains

## Reasons for not using client-side JWTs
# JWT stores session state client-side, so avoids central session store
# can be accessed from javascript if stored in local storage
# JWTs can be signed to prevent tampering, but not encrypted
# JWTs can be set to expire after a certain amount of time, but not extendable,
# not invalidatable from a central location
# can be used across domains, which is useful but also XSS risk
from typing import Union, Callable, Optional
import os
from functools import wraps
import inspect
import base64
import uuid
import jwt
from pathlib import Path
import urllib.parse

import pydantic
from fastapi import Request, Response
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
import gotrue

from agentops.api.log_config import logger
from agentops.common.route_config import reverse_path, BaseView
from agentops.common.environment import DASHBOARD_URL, API_DOMAIN, API_URL, APP_URL
from agentops.common import rate_limit
from agentops.api.db.supabase_client import get_supabase  # TODO move this

from .environment import (
    SUPABASE_JWT_SECRET,
    AUTH_COOKIE_SECRET,
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_EXPIRY,
    AUTH_JWT_ALGO,
    AUTH_ADDITIONAL_REFERERS,
)
from .schemas import (
    StatusResponse,
    RedirectMessageResponse,
    LoginSchema,
    OTPSchema,
    OAuthProvider,
    OAuthSchema,
    SignupSchema,
    PasswordResetSchema,
)
from .exceptions import AuthException
from .session import Session

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


_all__ = [
    'public_route',
    'auth_callback',
    'auth_code',
    'auth_session',
    'auth_login',
    'auth_otp',
    'auth_oauth',
    'auth_signup',
    'auth_password_reset',
    'auth_logout',
]


OAUTH_SCOPES: dict[OAuthProvider, str] = {
    'github': "read:user user:email",
    'google': "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
}
# don't redirect to these pages after login/signup; this prevents from returning users
# to the signin page if that's where they started
REDIRECT_OVERRIDES = (
    "/signin",
    "/signup",
)


def _get_api_domain() -> str:
    """
    Removes the port from the development domain.
    """
    return API_DOMAIN.split(':')[0]


class SupabaseUserData(pydantic.BaseModel):
    """
    Dataclass for data extracted from a Supabase JWT.
    """

    model_config = {'extra': 'ignore'}

    iss: Optional[str] = None  # Issuer: The URL of your Supabase project (optional for local dev)
    sub: str  # Subject: The user's UUID
    iat: int  # Issued At: When the token was created
    exp: int  # Expiration Time: When the token expires
    aud: str  # Audience: Usually "authenticated"

    email: str  # The user's email address
    role: str  # The user's role (typically "authenticated")
    app_metadata: dict  # Contains information like the provider used for authentication
    user_metadata: dict  # Custom data associated with the user, such as their name
    session_id: str  # A unique identifier for the current session


def _decode_supabase_jwt(token: str) -> SupabaseUserData:
    """
    Decode the Supabase JWT to get the available data about the authenticated user.
    """
    # Add leeway to account for clock skew between Supabase and our server
    user_info = jwt.decode(
        token, SUPABASE_JWT_SECRET, algorithms=['HS256'], audience="authenticated", leeway=10
    )
    return SupabaseUserData(**user_info)


def _encode_session_cookie(session: Session) -> str:
    """
    Encode the session as a JWT for use in setting our own session cookie.

    Currently this just includes the session_id in order to avoid storing any
    sensitive information in the cookie.
    """
    session_id = str(session.session_id)
    return jwt.encode({"session_id": session_id}, AUTH_COOKIE_SECRET, algorithm=AUTH_JWT_ALGO)


def _decode_session_cookie(cookie: str) -> Session | None:
    """
    Decode the session cookie to get the Session object.
    Raises AuthException if the cookie is invalid or expired.
    Returns None if the session is not found.
    """
    try:
        data = jwt.decode(cookie, AUTH_COOKIE_SECRET, algorithms=[AUTH_JWT_ALGO])
        return Session.get(data['session_id'])
    except (KeyError, jwt.InvalidTokenError):
        raise AuthException("Could not decode internal session JWT.")


def _validate_request(request: Request) -> None:
    """
    Validate the request to lock down public roues; 100% security through
    obscurity, but better than nothing.
    """

    if 'localhost' in API_URL:
        # Bypass all checks in local development
        return

    # Railway always sets the x-forwarded-for header, so we can use that to get the
    # original IP address of the request. This should never be empty, but maybe our
    # IP address gets exposed and someone makes a direct request to the API?
    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        logger.error("Request was made to a public route without a forwarded IP address.")
        raise HTTPException(500)

    # Rate limit the request based on the forwarded IP address
    rate_limit.record_interaction(forwarded_for)
    if rate_limit.is_blocked(forwarded_for):
        logger.warning(f"Rate limit exceeded for IP: {forwarded_for}")
        raise HTTPException(429)

    # Check if the request was made to the correct host. This is also set by
    # Railway, but we should check it anyway.
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host != API_DOMAIN:
        logger.error(f"Request was made to a public route from an unexpected host: {forwarded_host}")
        raise HTTPException(500)

    # Check if the Origin header is present
    # If this is missing this is a strong indicator we are being accessed outside a browser
    origin = request.headers.get("origin")
    if origin and not origin.startswith(APP_URL):
        logger.warning(f"Request was made to a public route from an unexpected origin: {origin}")
        raise HTTPException(500)

    # Check if the referrer header is present
    # If this is missing this is a strong indicator we are being accessed outside a browser
    referrer = request.headers.get("referer")
    if referrer and not any(referrer.startswith(u) for u in (APP_URL, *AUTH_ADDITIONAL_REFERERS)):
        logger.warning(f"Request was made to a public route from an unexpected referrer: {referrer}")
        raise HTTPException(500)

    # Check for a user agent header.
    # If this is missing this is a strong indicator we are being accessed outside a browser
    user_agent = request.headers.get("user-agent")
    if not user_agent:
        logger.warning(f"Request was made to a public route from an unexpected user agent: {user_agent}")
        raise HTTPException(500)


def public_route(decorated: Union[Callable, type[BaseView]]) -> Union[Callable, type[BaseView]]:
    """
    Mark a route as public.

    We default to requiring authentication on all routes unless they are
    explicitly marked as public. This is enforced by the middleware.

    Can be applied to functions or BaseView classes.
    """

    if inspect.isclass(decorated):
        # class based views
        if not issubclass(decorated, BaseView):
            raise TypeError(f"Class {decorated.__name__} must inherit from BaseView to use @public_route")

        view_func = decorated.__call__

        @wraps(view_func)
        async def wrapper(self, *args, **kwargs):
            # for BaseView, request is available as self.request
            _validate_request(self.request)
            return await view_func(self, *args, **kwargs)

        wrapper.is_public = True
        decorated.__call__ = wrapper
        return decorated
    else:
        # function-based views
        @wraps(decorated)
        async def wrapper(*args, **kwargs):
            # for functions, request comes from kwargs
            request = kwargs.get('request')
            assert request is not None, "`Request` must be available to views decorated with `@public_route`"
            _validate_request(request)
            return await decorated(*args, **kwargs)

        wrapper.is_public = True
        return wrapper


@public_route
async def auth_callback(request: Request) -> HTMLResponse:
    """
    Serves the authentication callback page, which captures the tokens from the URL hash
    and forwards them to our auth_session endpoint.

    This view just serves the HTML page, which is a simple JavaScript app that
    captures the tokens from the URL hash and forwards them to our auth_session endpoint.
    """
    # Content Security Policy headers prevent any scripts from running on the page,
    # except those with the correct nonce
    nonce = base64.b64encode(os.urandom(32)).decode('utf-8')
    headers = {
        'Content-Security-Policy': f"script-src 'nonce-{nonce}'",
        'Referrer-Policy': 'no-referrer',
    }

    # Check if there's a redirect_to parameter in the query string
    redirect_to = request.query_params.get('redirect_to')

    # If no explicit redirect_to, check for invite parameter to construct the redirect
    if not redirect_to:
        invite_org_id = request.query_params.get('invite')
        if invite_org_id:
            redirect_to = f"{APP_URL}/settings/organization?invite={invite_org_id}"
        else:
            redirect_to = DASHBOARD_URL

    # Ensure the redirect URL is to our app domain for security
    if not redirect_to.startswith(APP_URL):
        redirect_to = DASHBOARD_URL

    template = templates.get_template('auth_callback.html')
    content = template.render(
        nonce=nonce, auth_session_url=reverse_path('auth_session'), dashboard_url=redirect_to
    )

    return HTMLResponse(content=content, headers=headers)


def _create_session_for_response(response: Response, access_token: str) -> Response:
    """
    Create a session for the user based on the access token and set the session cookie in the response.
    """
    user_data: SupabaseUserData = _decode_supabase_jwt(access_token)
    user_id = uuid.UUID(user_data.sub)

    session = Session.create(user_id)

    cookie_value = _encode_session_cookie(session)

    cookie_domain = _get_api_domain()
    # Use secure cookies only with HTTPS
    cookie_secure = 'https' in API_URL
    # Use 'lax' for HTTP (development) to allow cross-origin requests, 'strict' for HTTPS (production)
    cookie_samesite = "lax" if not cookie_secure else "strict"

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=cookie_value,
        httponly=True,  # not accessible to JavaScript
        secure=cookie_secure,  # only send over https in production
        domain=cookie_domain,  # set cookie for the api domain
        max_age=AUTH_COOKIE_EXPIRY,
        samesite=cookie_samesite,
        path="/",  # valid across all paths
    )

    return response


@public_route
async def auth_code(request: Request, code: str) -> RedirectResponse:
    """
    Handles the OAuth callback by exchanging the authorization code for a session.
    This is the endpoint that the OAuth provider redirects to after the user has authenticated.
    It expects a 'code' parameter in the query string, which is the authorization code
    received from the OAuth provider.
    """
    supabase_client = get_supabase()

    try:
        auth_response = supabase_client.auth.exchange_code_for_session({'auth_code': code})
    except gotrue.errors.AuthApiError as e:
        raise AuthException.from_gotrue_autherror(e)

    if hasattr(auth_response, 'error'):
        raise AuthException("Failed to exchange code for session.")

    access_token = auth_response.session.access_token

    # TODO this often redirects back to the signin page, just send all users to the dashboard
    # redirect_to = request.query_params.get('redirect_to')
    # if redirect_to and redirect_to.startswith('/'):
    #     response = RedirectResponse(url=f"{APP_URL}{redirect_to}")
    # else:
    #     response = RedirectResponse(url=DASHBOARD_URL)

    response = RedirectResponse(url=DASHBOARD_URL)
    return _create_session_for_response(response, access_token)


# TODO annotate response type
@public_route
async def auth_session(request: Request) -> JSONResponse:
    """
    Receives the auth payload from the callback, validates it, creates a session,
    and returns a response with a cookie referencing the session.
    """
    print("auth_session: Processing request")

    # we just pass the hash params directly into the body of the request
    # so these are URL-encoded
    body = await request.body()
    print(f"auth_session: Raw body length: {len(body)}")

    params = urllib.parse.parse_qs(body.decode('utf-8'))
    print(f"auth_session: Parsed params keys: {list(params.keys())}")

    access_token = params.get('access_token', [None])[0]

    if not access_token:
        print("auth_session: ERROR - No access_token in request body")
        raise AuthException("Invalid parameters passed to callback URL.")

    print("auth_session: Found access_token, attempting to decode JWT")

    try:
        # Decode the JWT to see what user info we have
        user_data = _decode_supabase_jwt(access_token)
        print(f"auth_session: Decoded JWT for user {user_data.sub} with email {user_data.email}")

        # Check if this is an invite acceptance (look for invited_to_org in metadata)
        invited_to_org = None
        if user_data.user_metadata and 'invited_to_org' in user_data.user_metadata:
            invited_to_org = user_data.user_metadata.get('invited_to_org')
            print(f"auth_session: User is accepting invite to org {invited_to_org}")
    except Exception as e:
        print(f"auth_session: ERROR - Failed to decode JWT: {str(e)}")
        raise AuthException("Failed to decode access token")

    content = StatusResponse(message="User authenticated successfully.")
    response = JSONResponse(content=content.model_dump())

    print("auth_session: Creating session and setting cookie")
    result = _create_session_for_response(response, access_token)
    print("auth_session: Session created successfully, returning response")

    return result


# TODO annotate response type
@public_route
async def auth_login(request: Request, body: LoginSchema) -> JSONResponse:
    """
    Handle username/password logins.
    """
    supabase = get_supabase()
    # returns `AuthResponse` (.venv/lib/python3.12/site-packages/gotrue/types.py:95)
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {
                'email': body.email,
                'password': body.password,
            }
        )
    except gotrue.errors.AuthApiError as e:
        raise AuthException.from_gotrue_autherror(e)

    if hasattr(auth_response, 'error'):
        raise AuthException()

    access_token = auth_response.session.access_token
    content = StatusResponse(message="User authenticated successfully.")
    response = JSONResponse(content=content.model_dump())
    return _create_session_for_response(response, access_token)


@public_route
async def auth_otp(request: Request, body: OTPSchema) -> StatusResponse:
    """
    Initiates the login flow by sending a one-time password (OTP) to the user's email.
    """
    supabase = get_supabase()
    try:
        auth_response = supabase.auth.sign_in_with_otp(
            {
                'email': body.email,
                'options': {
                    # set this to false if you do not want the user to be automatically signed up
                    'should_create_user': False,
                    'email_redirect_to': f"{APP_URL}/auth/callback",
                },
            }
        )
    except gotrue.errors.AuthApiError as e:
        raise AuthException.from_gotrue_autherror(e)

    if hasattr(auth_response, 'error'):
        raise AuthException("Failed to send OTP.")

    return StatusResponse(message="Please check your email.")


@public_route
async def auth_oauth(request: Request, body: OAuthSchema) -> RedirectMessageResponse:
    """
    Redirects the user to the OAuth provider for authentication.
    """
    supabase = get_supabase()
    provider = body.provider
    redirect_url = f"{API_URL}{reverse_path('auth_code')}"

    if provider not in OAUTH_SCOPES:
        raise AuthException(f"Unsupported OAuth provider: {provider}")

    # TODO re-enable this once invalid redirect destinations have been fixed in `auth_code`
    # if body.redirect_to:
    #     params = urllib.parse.urlencode({"redirect_to": body.redirect_to})
    #     redirect_url += f"?redirect_to={params}"

    try:
        auth_response = supabase.auth.sign_in_with_oauth(
            {
                'provider': provider,
                'options': {
                    'redirect_to': redirect_url,
                    'scopes': OAUTH_SCOPES[provider],
                },
            }
        )
    except gotrue.errors.AuthApiError as e:
        raise AuthException.from_gotrue_autherror(e)

    if hasattr(auth_response, 'error'):
        raise AuthException("Failed to initiate OAuth flow.")

    return RedirectMessageResponse(
        message="Redirecting to OAuth provider...",
        url=auth_response.url,
    )


@public_route
async def auth_signup(request: Request, body: SignupSchema) -> StatusResponse:
    """
    Handles user signup by creating a new user with the provided email and password.
    """
    supabase = get_supabase()

    try:
        auth_response = supabase.auth.sign_up(
            {
                'email': body.email,
                'password': body.password,
                'options': {
                    'data': {
                        'full_name': body.full_name,
                    }
                },
            }
        )
    except gotrue.errors.AuthApiError as e:
        raise AuthException.from_gotrue_autherror(e)

    if hasattr(auth_response, 'error'):
        raise AuthException("Failed to sign up user.")

    return StatusResponse(message="User signed up successfully.")


@public_route
async def auth_password_reset(request: Request, body: PasswordResetSchema) -> StatusResponse:
    """
    Initiates a password reset flow by sending a reset email to the user.
    """
    supabase = get_supabase()

    try:
        # Use the frontend callback URL, same as the invite flow
        redirect_url = f"{APP_URL}/auth/callback"
        auth_response = supabase.auth.reset_password_for_email(body.email, {"redirect_to": redirect_url})
    except gotrue.errors.AuthApiError as e:
        raise AuthException.from_gotrue_autherror(e)

    if hasattr(auth_response, 'error'):
        raise AuthException("Failed to send password reset email.")

    return StatusResponse(message="Password reset email sent successfully.")


async def auth_logout(request: Request) -> StatusResponse:
    """
    Signs the user out by clearing the session cookie and expiring the session.
    """
    content = StatusResponse(message="User logged out successfully.")
    response = JSONResponse(content=content.model_dump())

    response.delete_cookie(key=AUTH_COOKIE_NAME, domain=_get_api_domain(), path="/")
    request.state.session.expire()

    return response
