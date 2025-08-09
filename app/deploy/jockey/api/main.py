from fastapi import FastAPI
from jockey import __version__
from jockey.worker import queue


app = FastAPI(title="Internal Deployment Status API", version=__version__)


@app.get("/queue/status")
async def get_queue_status():
    """Get deployment queue status."""
    try:
        # Get queue length
        queue_length = queue.get_queue_length()
        processing_count = queue.get_processing_count()

        return {
            "queue_length": queue_length,
            "processing_count": processing_count,
            "status": "active" if queue_length > 0 or processing_count > 0 else "idle",
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test Redis connection
        if queue.health_check():
            return {"status": "healthy", "redis": "connected"}
        else:
            return {"status": "unhealthy", "redis": "disconnected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}
