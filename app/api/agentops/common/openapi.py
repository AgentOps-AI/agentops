"""
OpenAPI Schema Utilities

Utilities for combining OpenAPI schemas from multiple FastAPI applications.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict


def create_combined_openapi_fn(
    main_app: FastAPI,
    mounted_apps: Dict[str, FastAPI],
    title: str = "Combined API",
    version: str = "1.0.0",
    description: str = "Combined API Schema",
):
    """
    Create a function that combines OpenAPI schemas from multiple FastAPI apps.

    Args:
        main_app: The main FastAPI application
        mounted_apps: Dictionary of mounted apps with their mount paths as keys
        title: Title for the combined OpenAPI schema
        version: Version string for the combined schema
        description: Description for the combined schema

    Returns:
        A function that can be assigned to app.openapi
    """

    def custom_openapi():
        # Return cached schema if available
        if main_app.openapi_schema:
            return main_app.openapi_schema

        # Get the OpenAPI schema for the main app
        openapi_schema = get_openapi(
            title=title,
            version=version,
            description=description,
            routes=main_app.routes,
        )

        # Add paths from mounted apps with proper prefixes
        for mount_path, app in mounted_apps.items():
            # Skip apps mounted at root (these should be handled separately)
            if mount_path == "/":
                prefix = ""
            else:
                # Ensure mount_path starts with / and doesn't end with /
                mount_path = "/" + mount_path.strip("/")
                prefix = mount_path

            # Get schema for the mounted app
            app_schema = get_openapi(
                title=f"{app.title}" if hasattr(app, 'title') else "API",
                version=version,
                routes=app.routes,
            )

            # Add paths with appropriate prefix
            for path, path_item in app_schema.get("paths", {}).items():
                # Handle root paths specially (e.g., "/" becomes "/api/")
                if path == "/":
                    path = ""
                # Add the path with the appropriate prefix
                openapi_schema["paths"][f"{prefix}{path}"] = path_item

            # Merge components
            if "components" in app_schema and "schemas" in app_schema["components"]:
                if "components" not in openapi_schema:
                    openapi_schema["components"] = {}
                if "schemas" not in openapi_schema["components"]:
                    openapi_schema["components"]["schemas"] = {}

                openapi_schema["components"]["schemas"].update(app_schema["components"]["schemas"])

            # Merge security schemes if present
            if "components" in app_schema and "securitySchemes" in app_schema["components"]:
                if "components" not in openapi_schema:
                    openapi_schema["components"] = {}
                if "securitySchemes" not in openapi_schema["components"]:
                    openapi_schema["components"]["securitySchemes"] = {}

                openapi_schema["components"]["securitySchemes"].update(
                    app_schema["components"]["securitySchemes"]
                )

        # Cache the schema
        main_app.openapi_schema = openapi_schema
        return main_app.openapi_schema

    return custom_openapi
