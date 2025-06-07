"""
Instrumentation for concurrent.futures module.

This module provides automatic instrumentation for ThreadPoolExecutor to ensure
proper OpenTelemetry context propagation across thread boundaries.
"""

from .instrumentation import ConcurrentFuturesInstrumentor

__all__ = ["ConcurrentFuturesInstrumentor"]
