import fastapi
from fastapi.middleware.cors import CORSMiddleware

from agentops.common.middleware import (
    CacheControlMiddleware,
    ExceptionMiddleware,
    DefaultContentTypeMiddleware,
)
from agentops.api.routes import v1, v2, v3, v4


app = fastapi.FastAPI(
    docs_url=None,  # Disable docs in the mounted app to avoid conflicts
    openapi_url=None,  # Disable OpenAPI in the mounted app to avoid conflicts
    title="AgentOps API",
    description="AgentOps API for managing sessions, agents, and events",
)

# A number of routes inside this app need to have alow_origins set to all, since they
# communicate with the SDK from client machines directly. Traces and Meterics routes
# should be behind CORS protection, and since they use a cookie for auth, they
# theoretically should require that the origins be restricted, but in practice this
# seems to work.
# We use a decorator to explicitly add CORS headers to the routes that need it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

app.add_middleware(CacheControlMiddleware)
app.add_middleware(ExceptionMiddleware)
app.add_middleware(DefaultContentTypeMiddleware)

# Include routers
app.include_router(v1.router)
app.include_router(v2.router)
app.include_router(v3.router)
app.include_router(v4.router)


# Health Check
@app.get("/health")
async def health_check():
    return {"message": "Server Up"}
