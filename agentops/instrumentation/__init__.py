from typing import Optional
from types import ModuleType
from dataclasses import dataclass
import importlib
import sys
from importlib.metadata import version
from packaging.version import Version, parse

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import TracingCore

_active_instrumentors: list[BaseInstrumentor] = []

PROVIDERS = {
    "openai": {
        "module_name": "agentops.instrumentation.openai",
        "class_name": "OpenAIInstrumentor",
        "min_version": "1.0.0",
    },
    "anthropic": {
        "module_name": "agentops.instrumentation.anthropic",
        "class_name": "AnthropicInstrumentor",
        "min_version": "0.32.0",
    },
    "google.genai": {
        "module_name": "agentops.instrumentation.google_generativeai",
        "class_name": "GoogleGenerativeAIInstrumentor",
        "min_version": "0.1.0",
    },
    "ibm_watsonx_ai": {
        "module_name": "agentops.instrumentation.ibm_watsonx_ai",
        "class_name": "IBMWatsonXInstrumentor",
        "min_version": "0.1.0",
    },
}

AGENTIC_LIBRARIES = {
    "crewai": {
        "module_name": "agentops.instrumentation.crewai",
        "class_name": "CrewAIInstrumentor",
        "min_version": "0.56.0",
    },
    "autogen": {"module_name": "agentops.instrumentation.ag2", "class_name": "AG2Instrumentor", "min_version": "0.1.0"},
    "agents": {
        "module_name": "agentops.instrumentation.openai_agents",
        "class_name": "OpenAIAgentsInstrumentor",
        "min_version": "0.1.0",
    },
}


def get_active_libraries() -> set[str]:
    """
    Get all actively used libraries in the current execution context.
    This includes both directly imported and indirectly imported libraries.
    """
    active_libs = set()

    # Check sys.modules for direct imports
    for name, module in sys.modules.items():
        if isinstance(module, ModuleType):
            root_package = name.split(".")[0]
            if root_package in PROVIDERS or root_package in AGENTIC_LIBRARIES:
                active_libs.add(root_package)

    return active_libs


@dataclass
class InstrumentorLoader:
    """
    Represents a dynamically-loadable instrumentor.
    """

    module_name: str
    class_name: str
    min_version: str

    @property
    def module(self) -> ModuleType:
        """Reference to the instrumentor module."""
        return importlib.import_module(self.module_name)

    @property
    def should_activate(self) -> bool:
        """Is the provider/library available in the environment with correct version?"""
        try:
            provider_name = self.module_name.split(".")[-1]
            module_version = version(provider_name)

            if module_version is None:
                logger.warning(f"Cannot determine {provider_name} version.")
                return False

            return Version(module_version) >= parse(self.min_version)
        except ImportError:
            return False

    def get_instance(self) -> BaseInstrumentor:
        """Return a new instance of the instrumentor."""
        return getattr(self.module, self.class_name)()


def instrument_one(loader: InstrumentorLoader) -> Optional[BaseInstrumentor]:
    """Instrument a single instrumentor."""
    if not loader.should_activate:
        logger.debug(
            f"Package {loader.module_name} not found or version < {loader.min_version}; skipping instrumentation"
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

    # Get all active libraries
    active_libs = get_active_libraries()
    logger.debug(f"Active libraries detected: {active_libs}")

    # First check for agentic libraries
    agentic_detected = False
    for lib_name, lib_config in AGENTIC_LIBRARIES.items():
        if lib_name in active_libs:
            loader = InstrumentorLoader(**lib_config)
            if loader.should_activate:
                agentic_detected = True
                instrumentor = instrument_one(loader)
                if instrumentor is not None:
                    _active_instrumentors.append(instrumentor)

    # If no agentic libraries are detected, instrument active providers
    if not agentic_detected:
        for provider_name, provider_config in PROVIDERS.items():
            if provider_name in active_libs:
                loader = InstrumentorLoader(**provider_config)
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
