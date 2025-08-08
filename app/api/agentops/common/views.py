import functools
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .environment import APP_URL


def add_cors_headers(
    *,
    origins: list[str] | None = None,
    methods: list[str] | None = None,
):
    """
    Render a Pydantic object response as a JSON response with CORS headers.

    Use this decorator when you need control over individual views that need to
    have CORS headers added to the response.

    Arguments:
        origins: List of allowed origins for CORS. Defaults to the APP_URL.
        methods: List of allowed methods for CORS. Defaults to GET, OPTIONS.
    """

    if origins is None:
        origins = [APP_URL]

    if methods is None:
        methods = ["GET", "OPTIONS"]

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> JSONResponse:
            response_object: BaseModel = await func(*args, **kwargs)
            assert isinstance(response_object, BaseModel), "View must return a Pydantic model"

            return JSONResponse(
                content=response_object.model_dump(),
                headers={
                    "Access-Control-Allow-Origin": ', '.join(origins),
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": ', '.join(methods),
                    "Access-Control-Allow-Headers": "*",
                },
            )

        return wrapper

    return decorator
