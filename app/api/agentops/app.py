"""
AgentOps Backend parent app

Collect app instances from all sub-apps and mount them here.

This allows for a single entry point for the backend, and for us to have
domain-specific middleware for each sub-app.

"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

from agentops.api.log_config import logger
from .common.sentry import sanitize_event
from .common.environment import API_DOMAIN
from .common.openapi import create_combined_openapi_fn
from .common.lifespan import lifespan
from .auth.app import app as auth_app
from .api.app import app as api_app
from .opsboard.app import app as opsboard_app
from .public.app import app as public_app
from .deploy.app import app as deploy_app

__all__ = ['app']

sentry_sdk.init(
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    before_send=sanitize_event,
)

# Create the main app with docs enabled in dev only
app = FastAPI(
    title="AgentOps Backend",
    description="AgentOps Backend Services",
    docs_url="/docs" if ("localhost" in API_DOMAIN) else None,
    openapi_url="/openapi.json" if ("localhost" in API_DOMAIN) else None,
    lifespan=lifespan,
)
logger.info("⚡️FastAPI app initialized")
logger.info(f"Docs available at: {app.docs_url}" if app.docs_url else "Docs disabled")

# Add CORS middleware for local development
if "localhost" in API_DOMAIN or "127.0.0.1" in API_DOMAIN:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware enabled for local development")

# Configure the mounted apps
# TODO this is redundant, but it's just for docs
mounted_apps = {
    "/": api_app,
    # Add other mounted apps when they are enabled
    "/auth": auth_app,
    "/opsboard": opsboard_app,
    "/public": public_app,
    "/deploy": deploy_app,
}

# Set the custom OpenAPI schema generator that combines all APIs
app.openapi = create_combined_openapi_fn(
    main_app=app,
    mounted_apps=mounted_apps,
    title="AgentOps Combined API",
    version="1.0.0",
    description="Combined API for all AgentOps services",
)

app.mount("/auth", auth_app)
app.mount("/opsboard", opsboard_app)
app.mount("/public", public_app)
app.mount("/deploy", deploy_app)
app.mount("/", api_app)


if "localhost" not in API_DOMAIN:
    # only run Sentry in prod since it breaks the docs routes.
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    logger.info("Sentry middleware enabled")
    app = SentryAsgiMiddleware(app)
