from .openai import OpenAIInstrumentor

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

    for instrumentor_class in instrumentors:
        instrumentor = instrumentor_class()
        instrumentor.instrument()
        _active_instrumentors.append(instrumentor)


def uninstrument_all():
    """
    Uninstrument all available instrumentors.
    This can be called to disable instrumentation.
    """
    global _active_instrumentors
    for instrumentor in _active_instrumentors:
        instrumentor.uninstrument()
    _active_instrumentors = []
