#!/usr/bin/env python3
"""Startup script for the Jockey Deployment API."""

import uvicorn
import os


def main():
    """Run the API server."""
    try:
        from jockey.api.main import app

        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        reload = os.getenv("API_RELOAD", "true").lower() == "true"

        print(f"Starting Jockey Deployment API on {host}:{port}")
        print(f"Redis host: {os.getenv('DEPLOY_REDIS_HOST', 'localhost')}")
        print(f"Redis port: {os.getenv('DEPLOY_REDIS_PORT', '6379')}")

        if reload:
            # Use import string for reload mode
            uvicorn.run("jockey.api.main:app", host=host, port=port, reload=reload)
        else:
            uvicorn.run(app, host=host, port=port, reload=reload)

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this from the correct directory")
        return 1
    except Exception as e:
        print(f"Error starting API: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
