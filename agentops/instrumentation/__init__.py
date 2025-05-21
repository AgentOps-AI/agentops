"""
AgentOps Instrumentation Module

This module provides automatic instrumentation for various LLM providers and agentic libraries.
It works by monitoring Python imports and automatically instrumenting packages as they are imported.

Key Features:
- Automatic detection and instrumentation of LLM providers (OpenAI, Anthropic, etc.)
- Support for agentic libraries (CrewAI, AutoGen, etc.)
- Version-aware instrumentation (only activates for supported versions)
- Smart handling of provider vs agentic library conflicts
- Non-intrusive monitoring using Python's import system
"""

from typing import Optional, Set, TypedDict
from types import ModuleType
from dataclasses import dataclass
import importlib
import sys
from importlib.metadata import version
from packaging.version import Version, parse
import builtins

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import TracingCore


# Module-level state variables
_active_instrumentors: list[BaseInstrumentor] = []
_original_builtins_import = builtins.__import__  # Store original import
_instrumenting_packages: Set[str] = set()
_has_agentic_library: bool = False


def _is_package_instrumented(package_name: str) -> bool:
    """Check if a package is already instrumented by looking at active instrumentors."""
    return any(
        instrumentor.__class__.__name__.lower().startswith(package_name.lower())
        for instrumentor in _active_instrumentors
    )


def _uninstrument_providers():
    """Uninstrument all provider instrumentors while keeping agentic libraries active."""
    global _active_instrumentors
    providers_to_remove = []
    for instrumentor in _active_instrumentors:
        if any(instrumentor.__class__.__name__.lower().startswith(provider.lower()) for provider in PROVIDERS.keys()):
            instrumentor.uninstrument()
            logger.debug(f"Uninstrumented provider {instrumentor.__class__.__name__}")
            providers_to_remove.append(instrumentor)

    _active_instrumentors = [i for i in _active_instrumentors if i not in providers_to_remove]


def _should_instrument_package(package_name: str) -> bool:
    """
    Determine if a package should be instrumented based on current state.
    Handles special cases for agentic libraries and providers.
    """
    global _has_agentic_library
    # If this is an agentic library, uninstrument all providers first
    if package_name in AGENTIC_LIBRARIES:
        _uninstrument_providers()
        _has_agentic_library = True
        logger.debug(f"Uninstrumented all providers due to agentic library {package_name} detection")
        return True

    # Skip providers if an agentic library is already instrumented
    if package_name in PROVIDERS and _has_agentic_library:
        logger.debug(f"Skipping provider {package_name} instrumentation as an agentic library is already instrumented")
        return False

    # Skip if already instrumented
    if _is_package_instrumented(package_name):
        logger.debug(f"Package {package_name} is already instrumented")
        return False

    return True


def _perform_instrumentation(package_name: str):
    """Helper function to perform instrumentation for a given package."""
    global _instrumenting_packages, _active_instrumentors
    if not _should_instrument_package(package_name):
        return

    # Get the appropriate configuration for the package
    config = PROVIDERS.get(package_name) or AGENTIC_LIBRARIES[package_name]
    loader = InstrumentorLoader(**config)

    if loader.should_activate:
        instrumentor = instrument_one(loader)  # instrument_one is already a module function
        if instrumentor is not None:
            _active_instrumentors.append(instrumentor)


def _import_monitor(name: str, globals_dict=None, locals_dict=None, fromlist=(), level=0):
    """
    Monitor imports and instrument packages as they are imported.
    This replaces the built-in import function to intercept package imports.
    """
    global _instrumenting_packages
    root = name.split(".", 1)[0]

    # Skip providers if an agentic library is already instrumented
    if _has_agentic_library and root in PROVIDERS:
        return _original_builtins_import(name, globals_dict, locals_dict, fromlist, level)

    # Check if this is a package we should instrument
    if (
        root in TARGET_PACKAGES
        and root not in _instrumenting_packages
        and not _is_package_instrumented(root)  # Check if already instrumented before adding
    ):
        logger.debug(f"Detected import of {root}")
        _instrumenting_packages.add(root)
        try:
            _perform_instrumentation(root)
        except Exception as e:
            logger.error(f"Error instrumenting {root}: {str(e)}")
        finally:
            _instrumenting_packages.discard(root)

    return _original_builtins_import(name, globals_dict, locals_dict, fromlist, level)


def _check_existing_imports():
    """Check and instrument packages that were already imported before monitoring started."""
    global _instrumenting_packages
    for name in list(sys.modules.keys()):
        module = sys.modules.get(name)
        if not isinstance(module, ModuleType):
            continue

        root = name.split(".", 1)[0]
        if _has_agentic_library and root in PROVIDERS:
            continue

        if root in TARGET_PACKAGES and root not in _instrumenting_packages and not _is_package_instrumented(root):
            _instrumenting_packages.add(root)
            try:
                _perform_instrumentation(root)
            except Exception as e:
                logger.error(f"Error instrumenting {root}: {str(e)}")
            finally:
                _instrumenting_packages.discard(root)


# Define the structure for instrumentor configurations
class InstrumentorConfig(TypedDict):
    module_name: str
    class_name: str
    min_version: str


# Configuration for supported LLM providers
PROVIDERS: dict[str, InstrumentorConfig] = {
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

# Configuration for supported agentic libraries
AGENTIC_LIBRARIES: dict[str, InstrumentorConfig] = {
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

# Combine all target packages for monitoring
TARGET_PACKAGES = set(PROVIDERS.keys()) | set(AGENTIC_LIBRARIES.keys())

# Create a single instance of the manager
# _manager = InstrumentationManager() # Removed


@dataclass
class InstrumentorLoader:
    """
    Represents a dynamically-loadable instrumentor.
    Handles version checking and instantiation of instrumentors.
    """

    module_name: str
    class_name: str
    min_version: str

    @property
    def module(self) -> ModuleType:
        """Get the instrumentor module."""
        return importlib.import_module(self.module_name)

    @property
    def should_activate(self) -> bool:
        """Check if the package is available and meets version requirements."""
        try:
            provider_name = self.module_name.split(".")[-1]
            module_version = version(provider_name)
            return module_version is not None and Version(module_version) >= parse(self.min_version)
        except ImportError:
            return False

    def get_instance(self) -> BaseInstrumentor:
        """Create and return a new instance of the instrumentor."""
        return getattr(self.module, self.class_name)()


def instrument_one(loader: InstrumentorLoader) -> Optional[BaseInstrumentor]:
    """
    Instrument a single package using the provided loader.
    Returns the instrumentor instance if successful, None otherwise.
    """
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
    """Start monitoring and instrumenting packages if not already started."""
    # Check if active_instrumentors is empty, as a proxy for not started.
    if not _active_instrumentors:
        builtins.__import__ = _import_monitor
        _check_existing_imports()


def uninstrument_all():
    """Stop monitoring and uninstrument all packages."""
    global _active_instrumentors, _has_agentic_library
    builtins.__import__ = _original_builtins_import
    for instrumentor in _active_instrumentors:
        instrumentor.uninstrument()
        logger.debug(f"Uninstrumented {instrumentor.__class__.__name__}")
    _active_instrumentors = []
    _has_agentic_library = False


def get_active_libraries() -> set[str]:
    """
    Get all actively used libraries in the current execution context.
    Returns a set of package names that are currently imported and being monitored.
    """
    return {
        name.split(".")[0]
        for name, module in sys.modules.items()
        if isinstance(module, ModuleType) and name.split(".")[0] in TARGET_PACKAGES
    }
