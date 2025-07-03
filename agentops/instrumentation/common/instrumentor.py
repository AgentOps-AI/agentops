"""Base instrumentor utilities for AgentOps instrumentation.

This module provides base classes and utilities for creating instrumentors,
reducing boilerplate code across different provider instrumentations.
"""

from abc import ABC, abstractmethod
from typing import Collection, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import Tracer, get_tracer
from opentelemetry.metrics import Meter, get_meter

from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.logging import logger


@dataclass
class InstrumentorConfig:
    """Configuration for an instrumentor."""

    library_name: str
    library_version: str
    wrapped_methods: List[WrapConfig] = field(default_factory=list)
    metrics_enabled: bool = True
    dependencies: Collection[str] = field(default_factory=list)


class CommonInstrumentor(BaseInstrumentor, ABC):
    """Base class for AgentOps instrumentors with common functionality."""

    def __init__(self, config: InstrumentorConfig):
        super().__init__()
        self.config = config
        self._tracer: Optional[Tracer] = None
        self._meter: Optional[Meter] = None
        self._metrics: Dict[str, Any] = {}

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return required dependencies."""
        return self.config.dependencies

    def _instrument(self, **kwargs):
        """Instrument the target library."""
        # Initialize tracer
        tracer_provider = kwargs.get("tracer_provider")
        self._tracer = get_tracer(self.config.library_name, self.config.library_version, tracer_provider)

        # Initialize meter if metrics enabled
        if self.config.metrics_enabled:
            meter_provider = kwargs.get("meter_provider")
            self._meter = get_meter(self.config.library_name, self.config.library_version, meter_provider)
            self._metrics = self._create_metrics(self._meter)

        # Perform custom initialization
        self._initialize(**kwargs)

        # Wrap all configured methods
        self._wrap_methods()

        # Perform custom wrapping
        self._custom_wrap(**kwargs)

    def _uninstrument(self, **kwargs):
        """Remove instrumentation."""
        # Unwrap all configured methods
        for wrap_config in self.config.wrapped_methods:
            try:
                unwrap(wrap_config)
            except Exception as e:
                logger.debug(
                    f"Failed to unwrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
                )

        # Perform custom unwrapping
        self._custom_unwrap(**kwargs)

        # Clear references
        self._tracer = None
        self._meter = None
        self._metrics.clear()

    def _wrap_methods(self):
        """Wrap all configured methods."""
        for wrap_config in self.config.wrapped_methods:
            try:
                wrap(wrap_config, self._tracer)
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(
                    f"Could not wrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
                )

    @abstractmethod
    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for the instrumentor.

        Returns a dictionary of metric name to metric instance.
        """
        pass

    def _initialize(self, **kwargs):
        """Perform custom initialization.

        Override in subclasses for custom initialization logic.
        """
        pass

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping beyond configured methods.

        Override in subclasses for special wrapping needs.
        """
        pass

    def _custom_unwrap(self, **kwargs):
        """Perform custom unwrapping beyond configured methods.

        Override in subclasses for special unwrapping needs.
        """
        pass


def create_wrapper_factory(wrapper_func: Callable, *wrapper_args, **wrapper_kwargs) -> Callable:
    """Create a factory function for wrapt-style wrappers.

    This is useful for creating wrappers that need additional arguments
    beyond the standard (wrapped, instance, args, kwargs).

    Args:
        wrapper_func: The wrapper function to call
        *wrapper_args: Arguments to pass to the wrapper
        **wrapper_kwargs: Keyword arguments to pass to the wrapper

    Returns:
        A factory function that returns the configured wrapper
    """

    def factory(tracer: Tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return wrapper_func(
                tracer, *wrapper_args, wrapped=wrapped, instance=instance, args=args, kwargs=kwargs, **wrapper_kwargs
            )

        return wrapper

    return factory
