from typing import Any, Optional
from types import ModuleType
from dataclasses import dataclass
import importlib

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from agentops.logging import logger
from agentops.sdk.core import TracingCore


# references to all active instrumentors
_active_instrumentors: list[BaseInstrumentor] = []


@dataclass
class InstrumentorLoader:
    """
        Represents a dynamically-loadable instrumentor.

        This class is used to load and activate instrumentors based on their module
    and class names.
        We use the `provider_import_name` to determine if the library is installed i
    n the environment.

        `modue_name` is the name of the module to import from.
        `class_name` is the name of the class to instantiate from the module.
        `provider_import_name` is the name of the package to check for availability.
    """

    module_name: str
    class_name: str
    provider_import_name: str

    @property
    def module(self) -> ModuleType:
        """Reference to the instrumentor module."""
        return importlib.import_module(self.module_name)

    @property
    def should_activate(self) -> bool:
        """Is the provider import available in the environment?"""
        try:
            importlib.import_module(self.provider_import_name)
            return True
        except ImportError:
            return False

    def get_instance(self) -> BaseInstrumentor:
        """Return a new instance of the instrumentor."""
        return getattr(self.module, self.class_name)()


available_instrumentors: list[InstrumentorLoader] = [
    InstrumentorLoader(
        module_name="opentelemetry.instrumentation.openai",
        class_name="OpenAIInstrumentor",
        provider_import_name="openai",
    ),
    InstrumentorLoader(
        module_name="opentelemetry.instrumentation.anthropic",
        class_name="AnthropicInstrumentor",
        provider_import_name="anthropic",
    ),
    InstrumentorLoader(
        module_name="opentelemetry.instrumentation.crewai",
        class_name="CrewAIInstrumentor",
        provider_import_name="crewai",
    ),
    InstrumentorLoader(
        module_name="opentelemetry.instrumentation.agents",
        class_name="AgentsInstrumentor",
        provider_import_name="agents",
    ),
]


def instrument_one(loader: InstrumentorLoader) -> Optional[BaseInstrumentor]:
    """Instrument a single instrumentor."""
    if not loader.should_activate:
        # this package is not in the environment; skip
        logger.debug(
            f"Package {loader.provider_import_name} not found; skipping instrumentation of {loader.class_name}"
        )
        return None

    instrumentor = loader.get_instance()
    instrumentor.instrument(tracer_provider=TracingCore.get_instance()._provider)
    logger.debug(f"Instrumented {loader.class_name}")

    return instrumentor


def instrument_all():
    """
    Instrument all available instrumentors.
    This function is called when `instrument_llm_calls` is enabled.
    """
    global _active_instrumentors

    if len(_active_instrumentors):
        logger.debug("Instrumentors have already been populated.")
        return

    for loader in available_instrumentors:
        if loader.class_name in _active_instrumentors:
            # already instrumented
            logger.debug(f"Instrumentor {loader.class_name} has already been instrumented.")
            return None

        instrumentor = instrument_one(loader)
        if instrumentor is not None:
            _active_instrumentors.append(instrumentor)


def uninstrument_all():
    """
    Uninstrument all available instrumentors.
    This can be called to disable instrumentation.
    """
    global _active_instrumentors
    for instrumentor in _active_instrumentors:
        instrumentor.uninstrument()
        logger.debug(f"Uninstrumented {instrumentor.__class__.__name__}")
    _active_instrumentors = []
