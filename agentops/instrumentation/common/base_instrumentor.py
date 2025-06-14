from typing import List, Collection, Optional, Dict, Any
from abc import ABC, abstractmethod
from opentelemetry.trace import get_tracer, Tracer
from opentelemetry.metrics import get_meter, Meter
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor as OTelBaseInstrumentor
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.common.metrics import MetricsManager, CommonMetrics


class AgentOpsBaseInstrumentor(OTelBaseInstrumentor, ABC):
    """Base class for all AgentOps instrumentors providing common functionality."""

    def __init__(self):
        super().__init__()
        self._wrapped_methods: List[WrapConfig] = []
        self._streaming_methods: List[Dict[str, Any]] = []
        self._tracer: Optional[Tracer] = None
        self._meter: Optional[Meter] = None
        self._metrics_manager: Optional[MetricsManager] = None
        self._metrics: Optional[CommonMetrics] = None

    @abstractmethod
    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        pass

    @abstractmethod
    def get_library_name(self) -> str:
        """Return the library name for this instrumentor."""
        pass

    @abstractmethod
    def get_library_version(self) -> str:
        """Return the library version for this instrumentor."""
        pass

    def get_wrapped_methods(self) -> List[WrapConfig]:
        """Get methods to wrap. Override to provide custom wrapped methods."""
        return self._wrapped_methods

    def get_streaming_methods(self) -> List[Dict[str, Any]]:
        """Get streaming methods that need special handling. Override if needed."""
        return self._streaming_methods

    def _instrument(self, **kwargs):
        """Instrument the target library."""
        tracer_provider = kwargs.get("tracer_provider")
        self._tracer = get_tracer(self.get_library_name(), self.get_library_version(), tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        self._meter = get_meter(self.get_library_name(), self.get_library_version(), meter_provider)

        # Initialize metrics using MetricsManager
        self._metrics_manager = MetricsManager(self._meter, self.get_library_name())
        self._metrics = self._metrics_manager.init_standard_metrics()

        # Allow subclasses to add custom metrics
        self._init_custom_metrics()

        # Wrap standard methods
        for wrap_config in self.get_wrapped_methods():
            self._wrap_method(wrap_config)

        # Handle streaming methods if any
        for stream_method in self.get_streaming_methods():
            self._wrap_streaming_method(stream_method)

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from the target library."""
        # Unwrap standard methods
        for wrap_config in self.get_wrapped_methods():
            self._unwrap_method(wrap_config)

        # Unwrap streaming methods
        for stream_method in self.get_streaming_methods():
            self._unwrap_streaming_method(stream_method)

    def _wrap_method(self, wrap_config: WrapConfig):
        """Wrap a single method with instrumentation."""
        try:
            wrap(wrap_config, self._tracer)
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(
                f"Could not wrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
            )

    def _unwrap_method(self, wrap_config: WrapConfig):
        """Unwrap a single method."""
        try:
            unwrap(wrap_config)
        except Exception as e:
            logger.debug(
                f"Failed to unwrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
            )

    def _wrap_streaming_method(self, stream_method: Dict[str, Any]):
        """Wrap a streaming method with special handling."""
        try:
            wrap_function_wrapper(
                stream_method["module"],
                stream_method["class_method"],
                stream_method["wrapper"](self._tracer),
            )
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to wrap {stream_method['module']}.{stream_method['class_method']}: {e}")

    def _unwrap_streaming_method(self, stream_method: Dict[str, Any]):
        """Unwrap a streaming method."""
        try:
            from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

            module_path, method_name = stream_method["class_method"].rsplit(".", 1)
            otel_unwrap(stream_method["module"], stream_method["class_method"])
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to unwrap {stream_method['module']}.{stream_method['class_method']}: {e}")

    def _init_custom_metrics(self):
        """Initialize custom metrics specific to this instrumentor. Override in subclasses if needed."""
        pass

    def add_custom_metric(self, name: str, metric_type: str, **kwargs):
        """Add a custom metric specific to this instrumentor."""
        if self._metrics_manager:
            return self._metrics_manager.add_custom_metric(name, metric_type, **kwargs)
        return None

    def get_metrics(self) -> Optional[CommonMetrics]:
        """Get all initialized metrics."""
        return self._metrics

    def _wrap_methods(self, methods: List[WrapConfig], tracer: Optional[Tracer] = None):
        """Wrap multiple methods at once.

        Args:
            methods: List of WrapConfig objects defining methods to wrap
            tracer: Optional tracer to use (defaults to self._tracer)
        """
        if tracer is None:
            tracer = self._tracer

        for method_config in methods:
            try:
                wrap(method_config, tracer)
            except (AttributeError, ModuleNotFoundError) as e:
                # Use debug level for missing optional packages
                logger.debug(f"Skipping {method_config.module}.{method_config.method} - package not installed: {e}")
            except Exception as e:
                # Log unexpected errors as warnings
                logger.warning(f"Unexpected error wrapping {method_config.module}.{method_config.method}: {e}")

    def _unwrap_methods(self, methods: List[WrapConfig]):
        """Unwrap multiple methods at once.

        Args:
            methods: List of WrapConfig objects defining methods to unwrap
        """
        for method_config in methods:
            try:
                unwrap(method_config)
            except Exception as e:
                logger.debug(f"Failed to unwrap {method_config.module}.{method_config.method}: {e}")
