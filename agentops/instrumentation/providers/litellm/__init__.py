"""LiteLLM instrumentation for AgentOps.

This package provides comprehensive instrumentation for LiteLLM using a hybrid 
approach that combines LiteLLM's callback system with wrapt-based instrumentation 
for maximum data collection and observability.

Usage:
    # Automatic instrumentation via AgentOps init
    import agentops
    agentops.init()  # Will auto-instrument LiteLLM if available
    
    # Manual instrumentation
    from agentops.instrumentation.providers.litellm import LiteLLMInstrumentor
    instrumentor = LiteLLMInstrumentor()
    instrumentor.instrument()
    
    # Simple callback setup (users just need this)
    import litellm
    litellm.success_callback = ["agentops"]
    litellm.failure_callback = ["agentops"]
"""

from agentops.instrumentation.providers.litellm.instrumentor import LiteLLMInstrumentor

LIBRARY_NAME = "litellm"
LIBRARY_VERSION = "1.0.0"  # Will be detected dynamically

__all__ = ["LiteLLMInstrumentor", "LIBRARY_NAME", "LIBRARY_VERSION"]


def is_litellm_available() -> bool:
    """Check if LiteLLM is available for instrumentation."""
    try:
        import litellm  # noqa: F401

        return True
    except ImportError:
        return False


def get_litellm_version() -> str:
    """Get the installed LiteLLM version."""
    try:
        import litellm

        return getattr(litellm, "__version__", "unknown")
    except ImportError:
        return "not_installed"
