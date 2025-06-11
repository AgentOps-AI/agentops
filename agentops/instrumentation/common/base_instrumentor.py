"""Enhanced base instrumentor with common initialization and lifecycle management.

This module provides an enhanced base instrumentor class that abstracts common
patterns found across all AgentOps instrumentors, including:
- Tracer and meter initialization
- Common metric definitions
- Method wrapping with error handling
- Streaming support utilities
- Standard uninstrumentation logic
"""

from typing import List, Dict, Optional, Any, Callable
from abc import abstractmethod
import logging

from opentelemetry.trace import get_tracer, Tracer
from opentelemetry.metrics import get_meter, Meter
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.semconv import Meters

logger = logging.getLogger(__name__)


class EnhancedBaseInstrumentor(BaseInstrumentor):
    """Enhanced base instrumentor with common functionality for all AgentOps instrumentors.

    This class provides:
    - Automatic tracer and meter initialization
    - Common metric creation based on provider type
    - Standardized method wrapping with error handling
    - Built-in streaming support
    - Consistent uninstrumentation

    Subclasses must implement:
    - library_name: Property returning the library name (e.g., "openai")
    - library_version: Property returning the library version
    - wrapped_methods: Property returning list of WrapConfig objects
    - instrumentation_dependencies: Method returning required packages
    """

    def __init__(self):
        """Initialize the enhanced base instrumentor."""
        super().__init__()
        self._tracer: Optional[Tracer] = None
        self._meter: Optional[Meter] = None
        self._metrics: Dict[str, Any] = {}
        self._wrapped_methods_cache: Optional[List[WrapConfig]] = None

    @property
    @abstractmethod
    def library_name(self) -> str:
        """Return the name of the library being instrumented."""
        pass

    @property
    @abstractmethod
    def library_version(self) -> str:
        """Return the version of the library being instrumented."""
        pass

    @property
    @abstractmethod
    def wrapped_methods(self) -> List[WrapConfig]:
        """Return list of methods to be wrapped for instrumentation."""
        pass

    @property
    def supports_streaming(self) -> bool:
        """Whether this instrumentor supports streaming responses."""
        return False

    def get_streaming_wrapper(self, tracer: Tracer) -> Optional[Callable]:
        """Return streaming wrapper function if supported."""
        return None

    def get_async_streaming_wrapper(self, tracer: Tracer) -> Optional[Callable]:
        """Return async streaming wrapper function if supported."""
        return None

    def _instrument(self, **kwargs):
        """Instrument the target library with common initialization."""
        # Initialize tracer
        tracer_provider = kwargs.get("tracer_provider")
        self._tracer = get_tracer(self.library_name, self.library_version, tracer_provider)

        # Initialize meter and metrics
        meter_provider = kwargs.get("meter_provider")
        self._meter = get_meter(self.library_name, self.library_version, meter_provider)
        self._metrics = self._create_metrics(self._meter)

        # Cache wrapped methods for uninstrumentation
        self._wrapped_methods_cache = self.wrapped_methods

        # Apply standard method wrapping
        self._wrap_methods(self._wrapped_methods_cache, self._tracer)

        # Apply streaming wrappers if supported
        if self.supports_streaming:
            self._apply_streaming_wrappers(self._tracer)

        # Call provider-specific initialization if needed
        self._instrument_provider(**kwargs)

    def _uninstrument(self, **kwargs):
        """Remove instrumentation with common cleanup."""
        # Unwrap standard methods
        if self._wrapped_methods_cache:
            self._unwrap_methods(self._wrapped_methods_cache)

        # Remove streaming wrappers if supported
        if self.supports_streaming:
            self._remove_streaming_wrappers()

        # Call provider-specific cleanup if needed
        self._uninstrument_provider(**kwargs)

        # Clear references
        self._tracer = None
        self._meter = None
        self._metrics.clear()
        self._wrapped_methods_cache = None

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create common metrics for LLM instrumentation."""
        metrics = {}

        # Common LLM metrics (OpenTelemetry GenAI standard)
        metrics["token_usage_histogram"] = meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE,
            unit="token",
            description=f"Measures number of input and output tokens used with {self.library_name}",
        )

        metrics["operation_duration_histogram"] = meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION, unit="s", description=f"{self.library_name} operation duration"
        )

        metrics["generation_choices_counter"] = meter.create_counter(
            name=Meters.LLM_GENERATION_CHOICES,
            unit="choice",
            description=f"Number of choices returned by {self.library_name} completions",
        )

        # Provider-specific metrics
        provider_metrics = self._create_provider_metrics(meter)
        metrics.update(provider_metrics)

        return metrics

    def _create_provider_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create provider-specific metrics. Override in subclasses."""
        return {}

    def _wrap_methods(self, methods: List[WrapConfig], tracer: Tracer):
        """Wrap methods with consistent error handling."""
        for wrap_config in methods:
            try:
                wrap(wrap_config, tracer)
                logger.debug(f"Successfully wrapped {wrap_config}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(
                    f"Could not wrap {wrap_config.package}.{wrap_config.class_name}." f"{wrap_config.method_name}: {e}"
                )
            except Exception as e:
                logger.warning(f"Unexpected error wrapping {wrap_config}: {e}")

    def _unwrap_methods(self, methods: List[WrapConfig]):
        """Unwrap methods with consistent error handling."""
        for wrap_config in methods:
            try:
                unwrap(wrap_config)
                logger.debug(f"Successfully unwrapped {wrap_config}")
            except Exception as e:
                logger.debug(
                    f"Failed to unwrap {wrap_config.package}.{wrap_config.class_name}."
                    f"{wrap_config.method_name}: {e}"
                )

    def _apply_streaming_wrappers(self, tracer: Tracer):
        """Apply streaming-specific wrappers. Override in subclasses that support streaming."""
        pass

    def _remove_streaming_wrappers(self):
        """Remove streaming-specific wrappers. Override in subclasses that support streaming."""
        pass

    def _instrument_provider(self, **kwargs):
        """Provider-specific instrumentation. Override in subclasses if needed."""
        pass

    def _uninstrument_provider(self, **kwargs):
        """Provider-specific uninstrumentation. Override in subclasses if needed."""
        pass

    @property
    def tracer(self) -> Optional[Tracer]:
        """Get the initialized tracer."""
        return self._tracer

    @property
    def meter(self) -> Optional[Meter]:
        """Get the initialized meter."""
        return self._meter

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get the created metrics."""
        return self._metrics
