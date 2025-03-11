import logging
from typing import Collection
from opentelemetry.instrumentation.haystack.config import Config
from wrapt import wrap_function_wrapper

from opentelemetry.trace import get_tracer
from opentelemetry.metrics import get_meter
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import (
    unwrap,
)
from opentelemetry.instrumentation.haystack.wrap_openai import wrap as openai_wrapper
from opentelemetry.instrumentation.haystack.wrap_pipeline import (
    wrap as pipeline_wrapper,
)
from opentelemetry.instrumentation.haystack.version import __version__
from agentops.semconv import Meters

logger = logging.getLogger(__name__)

_instruments = ("haystack-ai >= 2.0.0",)

WRAPPED_METHODS = [
    {
        "package": "haystack.components.generators.openai",
        "object": "OpenAIGenerator",
        "method": "run",
        "wrapper": openai_wrapper,
    },
    {
        "package": "haystack.components.generators.chat.openai",
        "object": "OpenAIChatGenerator",
        "method": "run",
        "wrapper": openai_wrapper,
    },
    {
        "package": "haystack.core.pipeline.pipeline",
        "object": "Pipeline",
        "method": "run",
        "wrapper": pipeline_wrapper,
    },
]

# Global metrics objects
_tokens_histogram = None
_request_counter = None
_response_time_histogram = None
_pipeline_duration_histogram = None


class HaystackInstrumentor(BaseInstrumentor):
    """An instrumentor for the Haystack framework."""

    def __init__(self, exception_logger=None):
        super().__init__()
        Config.exception_logger = exception_logger

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)
        
        # Initialize metrics
        global _tokens_histogram, _request_counter, _response_time_histogram, _pipeline_duration_histogram
        meter_provider = kwargs.get("meter_provider")
        if meter_provider:
            meter = get_meter(__name__, __version__, meter_provider)
            
            _tokens_histogram = meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE,
                unit="token",
                description="Measures number of input and output tokens used in Haystack LLM calls"
            )
            
            _request_counter = meter.create_counter(
                name="haystack.requests",
                unit="request",
                description="Counts Haystack LLM API requests"
            )
            
            _response_time_histogram = meter.create_histogram(
                name="haystack.response_time",
                unit="ms",
                description="Measures response time for Haystack LLM API calls"
            )
            
            _pipeline_duration_histogram = meter.create_histogram(
                name="haystack.pipeline_duration",
                unit="ms",
                description="Measures duration of Haystack pipeline executions"
            )
        
        # Pass metrics to wrappers by updating the Config
        Config.tokens_histogram = _tokens_histogram
        Config.request_counter = _request_counter
        Config.response_time_histogram = _response_time_histogram
        Config.pipeline_duration_histogram = _pipeline_duration_histogram
        
        for wrapped_method in WRAPPED_METHODS:
            wrap_package = wrapped_method.get("package")
            wrap_object = wrapped_method.get("object")
            wrap_method = wrapped_method.get("method")
            wrapper = wrapped_method.get("wrapper")
            wrap_function_wrapper(
                wrap_package,
                f"{wrap_object}.{wrap_method}" if wrap_object else wrap_method,
                wrapper(tracer, wrapped_method),
            )

    def _uninstrument(self, **kwargs):
        for wrapped_method in WRAPPED_METHODS:
            wrap_package = wrapped_method.get("package")
            wrap_object = wrapped_method.get("object")
            wrap_method = wrapped_method.get("method")
            unwrap(
                f"{wrap_package}.{wrap_object}" if wrap_object else wrap_package,
                wrap_method,
            )
