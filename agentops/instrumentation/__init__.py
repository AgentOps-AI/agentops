from opentelemetry.instrumentation.openai import OpenAIInstrumentor

from agentops.logging import logger

# Export all insturmentors (see opentelemetry.instrumentation.instrumentor.BaseInstrumentor)
# Can iteratively call .instrument() on each entry


instrumentors = [OpenAIInstrumentor]
# Keep live references to instrumentor instances
_active_instrumentors = []


def instrument_all():
    """
    Instrument all available instrumentors.
    This function is called when instrument_llm_calls is enabled.
    """
    global _active_instrumentors
    _active_instrumentors = []


    from agentops.telemetry.session import get_tracer_provider
    tracer_provider = get_tracer_provider()

    for instrumentor_class in instrumentors:
        instrumentor = instrumentor_class()
        instrumentor.instrument(tracer_provider=tracer_provider)
        logger.info(f"Instrumented {instrumentor_class.__name__}")
        _active_instrumentors.append(instrumentor)


def uninstrument_all():
    """
    Uninstrument all available instrumentors.
    This can be called to disable instrumentation.
    """
    global _active_instrumentors
    for instrumentor in _active_instrumentors:
        instrumentor.uninstrument()
        logger.info(f"Uninstrumented {instrumentor.__class__.__name__}")
    _active_instrumentors = []
