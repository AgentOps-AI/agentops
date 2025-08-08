from fastapi import FastAPI, APIRouter

from agentops.common.middleware import (
    CacheControlMiddleware,
    DefaultContentTypeMiddleware,
    ExceptionMiddleware,
)
from agentops.common.route_config import register_routes

from .routes import route_config

__all__ = ["app"]

app = FastAPI(title="AgentOps Public API")

app.add_middleware(DefaultContentTypeMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(ExceptionMiddleware)

router = APIRouter(prefix="/v1")
register_routes(router, route_config, prefix="/public/v1")
app.include_router(router)
