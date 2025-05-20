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


class InstrumentationManager:
    """
    Manages the instrumentation state and provides methods for monitoring and instrumenting packages.
    This is implemented as a singleton to maintain consistent state across the application.
    """

    def __init__(self):
        # List of currently active instrumentors
        self._active_instrumentors: list[BaseInstrumentor] = []
        # Store the original import function to restore it later
        self._original_import = builtins.__import__
        # Track packages currently being instrumented to prevent recursion
        self._instrumenting_packages: Set[str] = set()
        # Flag to track if an agentic library is currently instrumented
        self._has_agentic_library: bool = False

    def is_package_instrumented(self, package_name: str) -> bool:
        """Check if a package is already instrumented by looking at active instrumentors."""
        return any(
            instrumentor.__class__.__name__.lower().startswith(package_name.lower())
            for instrumentor in self._active_instrumentors
        )

    def should_instrument_package(self, package_name: str) -> bool:
        """
        Determine if a package should be instrumented based on current state.
        Handles special cases for agentic libraries and providers.
        """
        # If this is an agentic library, uninstrument all providers first
        if package_name in AGENTIC_LIBRARIES:
            self.uninstrument_providers()
            self._has_agentic_library = True
            logger.debug(f"Uninstrumented all providers due to agentic library {package_name} detection")
            return True

        # Skip providers if an agentic library is already instrumented
        if package_name in PROVIDERS and self._has_agentic_library:
            logger.debug(
                f"Skipping provider {package_name} instrumentation as an agentic library is already instrumented"
            )
            return False

        # Skip if already instrumented
        if self.is_package_instrumented(package_name):
            logger.debug(f"Package {package_name} is already instrumented")
            return False

        return True

    def uninstrument_providers(self):
        """Uninstrument all provider instrumentors while keeping agentic libraries active."""
        providers_to_remove = []
        for instrumentor in self._active_instrumentors:
            if any(
                instrumentor.__class__.__name__.lower().startswith(provider.lower()) for provider in PROVIDERS.keys()
            ):
                instrumentor.uninstrument()
                logger.debug(f"Uninstrumented provider {instrumentor.__class__.__name__}")
                providers_to_remove.append(instrumentor)

        self._active_instrumentors = [i for i in self._active_instrumentors if i not in providers_to_remove]

    def _import_monitor(self, name: str, globals=None, locals=None, fromlist=(), level=0):
        """
        Monitor imports and instrument packages as they are imported.
        This replaces the built-in import function to intercept package imports.
        """
        root = name.split(".", 1)[0]

        # Skip providers if an agentic library is already instrumented
        if self._has_agentic_library and root in PROVIDERS:
            return self._original_import(name, globals, locals, fromlist, level)

        # Check if this is a package we should instrument
        if (
            root in TARGET_PACKAGES
            and root not in self._instrumenting_packages
            and not self.is_package_instrumented(root)
        ):
            logger.debug(f"Detected import of {root}")
            self._instrumenting_packages.add(root)
            try:
                if not self.should_instrument_package(root):
                    return self._original_import(name, globals, locals, fromlist, level)

                # Get the appropriate configuration for the package
                config = PROVIDERS.get(root) or AGENTIC_LIBRARIES[root]
                loader = InstrumentorLoader(**config)

                if loader.should_activate:
                    instrumentor = instrument_one(loader)
                    if instrumentor is not None:
                        self._active_instrumentors.append(instrumentor)
            except Exception as e:
                logger.error(f"Error instrumenting {root}: {str(e)}")
            finally:
                self._instrumenting_packages.discard(root)

        return self._original_import(name, globals, locals, fromlist, level)

    def start_monitoring(self):
        """Start monitoring imports and check already imported packages."""
        builtins.__import__ = self._import_monitor
        self._check_existing_imports()

    def stop_monitoring(self):
        """Stop monitoring imports and restore the original import function."""
        builtins.__import__ = self._original_import

    def _check_existing_imports(self):
        """Check and instrument packages that were already imported before monitoring started."""
        for name in list(sys.modules.keys()):
            module = sys.modules.get(name)
            if not isinstance(module, ModuleType):
                continue

            root = name.split(".", 1)[0]
            if self._has_agentic_library and root in PROVIDERS:
                continue

            if (
                root in TARGET_PACKAGES
                and root not in self._instrumenting_packages
                and not self.is_package_instrumented(root)
            ):
                self._instrumenting_packages.add(root)
                try:
                    if not self.should_instrument_package(root):
                        continue

                    config = PROVIDERS.get(root) or AGENTIC_LIBRARIES[root]
                    loader = InstrumentorLoader(**config)

                    if loader.should_activate:
                        instrumentor = instrument_one(loader)
                        if instrumentor is not None:
                            self._active_instrumentors.append(instrumentor)
                except Exception as e:
                    logger.error(f"Error instrumenting {root}: {str(e)}")
                finally:
                    self._instrumenting_packages.discard(root)

    def uninstrument_all(self):
        """Stop monitoring and uninstrument all packages."""
        self.stop_monitoring()
        for instrumentor in self._active_instrumentors:
            instrumentor.uninstrument()
            logger.debug(f"Uninstrumented {instrumentor.__class__.__name__}")
        self._active_instrumentors = []
        self._has_agentic_library = False


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
_manager = InstrumentationManager()


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
    if not _manager._active_instrumentors:
        _manager.start_monitoring()


def uninstrument_all():
    """Stop monitoring and uninstrument all packages."""
    _manager.uninstrument_all()


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
