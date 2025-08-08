from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from agentops.common.environment import ALLOWED_ORIGINS
from agentops.common.middleware import (
    CacheControlMiddleware,
    DefaultContentTypeMiddleware,
    ExceptionMiddleware,
)
from agentops.common.route_config import register_routes
from agentops.auth.middleware import AuthenticatedRoute

from .routes import route_config

__all__ = ["app"]

app = FastAPI(title="Opsboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PUT"],
    allow_headers=["*"],
)

app.add_middleware(DefaultContentTypeMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(ExceptionMiddleware)

router = APIRouter(route_class=AuthenticatedRoute)
register_routes(router, route_config, prefix="/opsboard")
app.include_router(router)
