"""Xpander trace probe for automatic instrumentation activation.

This module provides automatic instrumentation for Xpander SDK when imported.
It should be imported early in the application lifecycle to ensure all
Xpander interactions are captured.
"""

import logging
from agentops.instrumentation.agentic.xpander.instrumentor import XpanderInstrumentor

logger = logging.getLogger(__name__)

# Global instrumentor instance
_instrumentor = None


def activate_xpander_instrumentation():
    """Activate Xpander instrumentation."""
    global _instrumentor

    if _instrumentor is None:
        try:
            _instrumentor = XpanderInstrumentor()
            _instrumentor.instrument()
            logger.info("Xpander instrumentation activated successfully")
        except Exception as e:
            logger.error(f"Failed to activate Xpander instrumentation: {e}")
            _instrumentor = None

    return _instrumentor


def deactivate_xpander_instrumentation():
    """Deactivate Xpander instrumentation."""
    global _instrumentor

    if _instrumentor is not None:
        try:
            _instrumentor.uninstrument()
            logger.info("Xpander instrumentation deactivated successfully")
        except Exception as e:
            logger.error(f"Failed to deactivate Xpander instrumentation: {e}")
        finally:
            _instrumentor = None


def get_instrumentor():
    """Get the active instrumentor instance."""
    return _instrumentor


# Stub functions for backward compatibility
def wrap_openai_call_for_xpander(openai_call_func, purpose="general"):
    """Backward compatibility stub - functionality now handled by auto-instrumentation."""
    logger.debug(f"wrap_openai_call_for_xpander called with purpose: {purpose}")
    return openai_call_func


def is_xpander_session_active():
    """Check if xpander session is active."""
    return _instrumentor is not None


def get_active_xpander_session():
    """Get active xpander session."""
    return _instrumentor._context if _instrumentor else None


# Convenience functions for cleaner OpenAI integration
def wrap_openai_analysis(openai_call_func):
    """Wrap OpenAI calls for analysis/reasoning steps."""
    return wrap_openai_call_for_xpander(openai_call_func, "analysis")


def wrap_openai_planning(openai_call_func):
    """Wrap OpenAI calls for planning steps."""
    return wrap_openai_call_for_xpander(openai_call_func, "planning")


def wrap_openai_synthesis(openai_call_func):
    """Wrap OpenAI calls for synthesis/summary steps."""
    return wrap_openai_call_for_xpander(openai_call_func, "synthesis")


# Note: Auto-activation is now handled by the main AgentOps instrumentation system
# activate_xpander_instrumentation()
