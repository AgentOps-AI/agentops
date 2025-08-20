from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from agentops.common.route_config import RouteConfig, register_routes
from agentops.common.middleware import CacheControlMiddleware, ExceptionMiddleware
from agentops.common.environment import ALLOWED_ORIGINS

from .middleware import AuthenticatedRoute
from .views import (
    auth_callback,
    auth_code,
    auth_session,
    auth_login,
    auth_otp,
    auth_oauth,
    auth_signup,
    auth_password_reset,
    auth_logout,
)

__all__ = ['app']

route_config: list[RouteConfig] = [
    RouteConfig(
        name='auth_callback',
        path="/callback",
        endpoint=auth_callback,
        methods=["GET"],
    ),
    RouteConfig(
        name='auth_code',
        path="/code",
        endpoint=auth_code,
        methods=["GET"],
    ),
    RouteConfig(
        name='auth_session',
        path="/session",
        endpoint=auth_session,
        methods=["POST"],
    ),
    RouteConfig(
        name='auth_login',
        path="/login",
        endpoint=auth_login,
        methods=["POST"],
    ),
    RouteConfig(
        name='auth_otp',
        path="/otp",
        endpoint=auth_otp,
        methods=["POST"],
    ),
    RouteConfig(
        name='auth_oauth',
        path="/oauth",
        endpoint=auth_oauth,
        methods=["POST"],
    ),
    RouteConfig(
        name='auth_signup',
        path="/signup",
        endpoint=auth_signup,
        methods=["POST"],
    ),
    RouteConfig(
        name='auth_password_reset',
        path="/password_reset",
        endpoint=auth_password_reset,
        methods=["POST"],
    ),
    RouteConfig(
        name='auth_logout',
        path="/logout",
        endpoint=auth_logout,
        methods=["POST"],
    ),
]

app = FastAPI(title="AgentOps Auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=["*"],
)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(ExceptionMiddleware)

router = APIRouter(route_class=AuthenticatedRoute)
register_routes(router, route_config, prefix="/auth")
app.include_router(router)