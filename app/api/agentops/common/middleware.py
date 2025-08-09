from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from agentops.api.log_config import logger


DEFAULT_CONTENT_TYPE = "application/json"


class DefaultContentTypeMiddleware(BaseHTTPMiddleware):
    """Middleware to set default Content-Type if not set by the view"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if "content-type" not in response.headers:
            response.headers["content-type"] = DEFAULT_CONTENT_TYPE

        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Middleware to set cache control headers on responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if "cache-control" not in response.headers:
            response.headers["cache-control"] = "no-store, no-cache, must-revalidate, max-age=0"
        if "pragma" not in response.headers:
            response.headers["pragma"] = "no-cache"
        if "expires" not in response.headers:
            response.headers["expires"] = "0"

        return response


class ExceptionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return a JSON response"""

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Return a JSON response with a 500 status code if an unhandled exception occurs.

        Intentionally exclude all information about the exception in the response.

        Note that `HTTPException`s are handled by FastAPI and will not reach this point.
        """
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Exception: {e}", exc_info=True)

            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error"},
            )
