from collections.abc import Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute

from .environment import (
    AUTH_EXTEND_SESSIONS,
    AUTH_COOKIE_NAME,
)
from .exceptions import AuthException
from .session import Session
from .views import _decode_session_cookie


class AuthenticatedRoute(APIRoute):
    """
    Route class that enforces authentication for endpoints.

    Protects all endpoints except those explicitly marked as public.

    Populates request.state.session with the user's Session object.

    Usage:
    from fastapi import FastAPI, APIRouter
    from api.agentops.auth.middleware import AuthenticatedRoute

    app = FastAPI()
    router = APIRouter(route_class=AuthenticatedRoute)
    app.include_router(router)
    ...
    """

    def _get_session(self, request: Request) -> Session:
        """
        Get the user's session from the request.

        Raises AuthException if the user is not authenticated or if the session has expired.

        If AUTH_EXTEND_SESSIONS is enabled, the session expiry is extended.
        """
        if not (cookie := request.cookies.get(AUTH_COOKIE_NAME)):
            raise AuthException("User is not authenticated.")

        if not (session := _decode_session_cookie(cookie)):
            raise AuthException("User's session has expired.")

        if AUTH_EXTEND_SESSIONS:
            session.extend()

        return session

    def get_route_handler(self) -> Callable:
        """
        Override the default route handler to inject authentication logic.

        This method wraps the original route handler to ensure that the session
        is populated in request.state.session before calling the handler.

        If the endpoint is marked as public, it will not raise an AuthException
        when the session is not found or invalid.
        """
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                request.state.session = self._get_session(request)
            except AuthException as e:
                if not getattr(self.endpoint, 'is_public', False):
                    raise e

            response = await original_route_handler(request)
            return response

        return custom_route_handler
