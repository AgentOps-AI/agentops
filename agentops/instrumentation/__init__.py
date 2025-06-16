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

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired
from types import ModuleType
from dataclasses import dataclass
import importlib
import sys
from importlib.metadata import version
from packaging.version import Version, parse
import builtins

# Add os and site for path checking
import os
import site

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import tracer


# Define the structure for instrumentor configurations
class InstrumentorConfig(TypedDict):
    module_name: str
    class_name: str
    min_version: str
    package_name: NotRequired[str]  # Optional: actual pip package name if different from module


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
    "ibm_watsonx_ai": {
        "module_name": "agentops.instrumentation.ibm_watsonx_ai",
        "class_name": "IBMWatsonXInstrumentor",
        "min_version": "0.1.0",
    },
    "google.genai": {
        "module_name": "agentops.instrumentation.google_genai",
        "class_name": "GoogleGenAIInstrumentor",
        "min_version": "0.1.0",
        "package_name": "google-genai",  # Actual pip package name
    },
    "mem0": {
        "module_name": "agentops.instrumentation.mem0",
        "class_name": "Mem0Instrumentor",
        "min_version": "0.1.0",
        "package_name": "mem0ai",
    },
}

# Configuration for utility instrumentors
UTILITY_INSTRUMENTORS: dict[str, InstrumentorConfig] = {
    "concurrent.futures": {
        "module_name": "agentops.instrumentation.concurrent_futures",
        "class_name": "ConcurrentFuturesInstrumentor",
        "min_version": "3.7.0",  # Python 3.7+ (concurrent.futures is stdlib)
        "package_name": "python",  # Special case for stdlib modules
    },
}

# Configuration for supported agentic libraries
AGENTIC_LIBRARIES: dict[str, InstrumentorConfig] = {
    "crewai": {
        "module_name": "agentops.instrumentation.crewai",
        "class_name": "CrewAIInstrumentor",
        "min_version": "0.56.0",
    },
    "autogen": {"module_name": "agentops.instrumentation.ag2", "class_name": "AG2Instrumentor", "min_version": "0.3.2"},
    "agents": {
        "module_name": "agentops.instrumentation.openai_agents",
        "class_name": "OpenAIAgentsInstrumentor",
        "min_version": "0.0.1",
    },
    "google.adk": {
        "module_name": "agentops.instrumentation.google_adk",
        "class_name": "GoogleADKInstrumentor",
        "min_version": "0.1.0",
    },
}

# Combine all target packages for monitoring
TARGET_PACKAGES = set(PROVIDERS.keys()) | set(AGENTIC_LIBRARIES.keys()) | set(UTILITY_INSTRUMENTORS.keys())

# Create a single instance of the manager
# _manager = InstrumentationManager() # Removed

# Module-level state variables
_active_instrumentors: list[BaseInstrumentor] = []
_original_builtins_import = builtins.__import__  # Store original import
_instrumenting_packages: Set[str] = set()
_has_agentic_library: bool = False


# New helper function to check module origin
def _is_installed_package(module_obj: ModuleType, package_name_key: str) -> bool:
    """
    Determines if the given module object corresponds to an installed site-package
    rather than a local module, especially when names might collide.
    `package_name_key` is the key from TARGET_PACKAGES (e.g., 'agents', 'google.adk').
    """
    # Special case for stdlib modules (marked with package_name="python" in UTILITY_INSTRUMENTORS)
    if (
        package_name_key in UTILITY_INSTRUMENTORS
        and UTILITY_INSTRUMENTORS[package_name_key].get("package_name") == "python"
    ):
        logger.debug(
            f"_is_installed_package: Module '{package_name_key}' is a Python standard library module. Considering it an installed package."
        )
        return True

    if not hasattr(module_obj, "__file__") or not module_obj.__file__:
        logger.debug(
            f"_is_installed_package: Module '{package_name_key}' has no __file__, assuming it might be an SDK namespace package. Returning True."
        )
        return True

    module_path = os.path.normcase(os.path.realpath(os.path.abspath(module_obj.__file__)))

    # Priority 1: Check if it's in any site-packages directory.
    site_packages_dirs = site.getsitepackages()
    if isinstance(site_packages_dirs, str):
        site_packages_dirs = [site_packages_dirs]

    if hasattr(site, "USER_SITE") and site.USER_SITE and os.path.exists(site.USER_SITE):
        site_packages_dirs.append(site.USER_SITE)

    normalized_site_packages_dirs = [
        os.path.normcase(os.path.realpath(p)) for p in site_packages_dirs if p and os.path.exists(p)
    ]

    for sp_dir in normalized_site_packages_dirs:
        if module_path.startswith(sp_dir):
            logger.debug(
                f"_is_installed_package: Module '{package_name_key}' is a library, instrumenting '{package_name_key}'."
            )
            return True

    # Priority 2: If not in site-packages, it's highly likely a local module or not an SDK we target.
    logger.debug(f"_is_installed_package: Module '{package_name_key}' is a local module, skipping instrumentation.")
    return False


def _is_package_instrumented(package_name: str) -> bool:
    """Check if a package is already instrumented by looking at active instrumentors."""
    # Handle package.module names by converting dots to underscores for comparison
    normalized_target_name = package_name.replace(".", "_").lower()
    for instrumentor in _active_instrumentors:
        # Check based on the key it was registered with
        if (
            hasattr(instrumentor, "_agentops_instrumented_package_key")
            and instrumentor._agentops_instrumented_package_key == package_name
        ):
            return True

        # Fallback to class name check (existing logic, less precise)
        # We use split('.')[-1] for cases like 'google.genai' to match GenAIInstrumentor
        instrumentor_class_name_prefix = instrumentor.__class__.__name__.lower().replace("instrumentor", "")
        target_base_name = package_name.split(".")[-1].lower()
        normalized_class_name_match = (
            normalized_target_name.startswith(instrumentor_class_name_prefix)
            or target_base_name == instrumentor_class_name_prefix
        )

        if normalized_class_name_match:
            # This fallback can be noisy, let's make it more specific or rely on the key above more
            # For now, if the key matches or this broad name match works, consider instrumented.
            # This helps if _agentops_instrumented_package_key was somehow not set.
            return True

    return False


def _uninstrument_providers():
    """Uninstrument all provider instrumentors while keeping agentic libraries active."""
    global _active_instrumentors
    new_active_instrumentors = []
    uninstrumented_any = False
    for instrumentor in _active_instrumentors:
        instrumented_key = getattr(instrumentor, "_agentops_instrumented_package_key", None)
        if instrumented_key and instrumented_key in PROVIDERS:
            try:
                instrumentor.uninstrument()
                logger.info(
                    f"AgentOps: Uninstrumented provider: {instrumentor.__class__.__name__} (for package '{instrumented_key}') due to agentic library activation."
                )
                uninstrumented_any = True
            except Exception as e:
                logger.error(f"Error uninstrumenting provider {instrumentor.__class__.__name__}: {e}")
        else:
            # Keep non-provider instrumentors or those without our key (shouldn't happen for managed ones)
            new_active_instrumentors.append(instrumentor)

    if uninstrumented_any or not new_active_instrumentors and _active_instrumentors:
        logger.debug(
            f"_uninstrument_providers: Processed. Previous active: {len(_active_instrumentors)}, New active after filtering providers: {len(new_active_instrumentors)}"
        )
    _active_instrumentors = new_active_instrumentors


def _should_instrument_package(package_name: str) -> bool:
    """
    Determine if a package should be instrumented based on current state.
    Handles special cases for agentic libraries, providers, and utility instrumentors.
    """
    global _has_agentic_library

    # If already instrumented by AgentOps (using our refined check), skip.
    if _is_package_instrumented(package_name):
        logger.debug(f"_should_instrument_package: '{package_name}' already instrumented by AgentOps. Skipping.")
        return False

    # Utility instrumentors should always be instrumented regardless of agentic library state
    if package_name in UTILITY_INSTRUMENTORS:
        logger.debug(f"_should_instrument_package: '{package_name}' is a utility instrumentor. Always allowing.")
        return True

    # Only apply agentic/provider logic if it's NOT a utility instrumentor
    is_target_agentic = package_name in AGENTIC_LIBRARIES
    is_target_provider = package_name in PROVIDERS

    if not is_target_agentic and not is_target_provider:
        logger.debug(
            f"_should_instrument_package: '{package_name}' is not a targeted provider or agentic library. Skipping."
        )
        return False

    if _has_agentic_library:
        # An agentic library is already active.
        if is_target_agentic:
            logger.info(
                f"AgentOps: An agentic library is active. Skipping instrumentation for subsequent agentic library '{package_name}'."
            )
            return False
        if is_target_provider:
            logger.info(
                f"AgentOps: An agentic library is active. Skipping instrumentation for provider '{package_name}'."
            )
            return False
    else:
        # No agentic library is active yet.
        if is_target_agentic:
            logger.info(
                f"AgentOps: '{package_name}' is the first-targeted agentic library. Will uninstrument providers if any are/become active."
            )
            _uninstrument_providers()
            return True
        if is_target_provider:
            logger.debug(
                f"_should_instrument_package: '{package_name}' is a provider, no agentic library active. Allowing."
            )
            return True

    logger.debug(
        f"_should_instrument_package: Defaulting to False for '{package_name}' (state: _has_agentic_library={_has_agentic_library})"
    )
    return False


def _perform_instrumentation(package_name: str):
    """Helper function to perform instrumentation for a given package."""
    global _instrumenting_packages, _active_instrumentors, _has_agentic_library
    if not _should_instrument_package(package_name):
        return

    # Get the appropriate configuration for the package
    # Ensure package_name is a key in either PROVIDERS, AGENTIC_LIBRARIES, or UTILITY_INSTRUMENTORS
    if (
        package_name not in PROVIDERS
        and package_name not in AGENTIC_LIBRARIES
        and package_name not in UTILITY_INSTRUMENTORS
    ):
        logger.debug(
            f"_perform_instrumentation: Package '{package_name}' not found in PROVIDERS, AGENTIC_LIBRARIES, or UTILITY_INSTRUMENTORS. Skipping."
        )
        return

    config = PROVIDERS.get(package_name) or AGENTIC_LIBRARIES.get(package_name) or UTILITY_INSTRUMENTORS[package_name]
    loader = InstrumentorLoader(**config)

    # instrument_one already checks loader.should_activate
    instrumentor_instance = instrument_one(loader)
    if instrumentor_instance is not None:
        # Check if it was *actually* instrumented by instrument_one by seeing if the instrument method was called successfully.
        # This relies on instrument_one returning None if its internal .instrument() call failed (if we revert that, this needs adjustment)
        # For now, assuming instrument_one returns instance only on full success.
        # User request was to return instrumentor even if .instrument() fails. So, we check if _agentops_instrumented_package_key was set by us.

        # Let's assume instrument_one might return an instance whose .instrument() failed.
        # The key is set before _active_instrumentors.append, so if it's already there and matches, it means it's a re-attempt on the same package.
        # The _is_package_instrumented check at the start of _should_instrument_package should prevent most re-entry for the same package_name.

        # Store the package key this instrumentor is for, to aid _is_package_instrumented
        instrumentor_instance._agentops_instrumented_package_key = package_name

        # Add to active_instrumentors only if it's not a duplicate in terms of package_key being instrumented
        # This is a safeguard, _is_package_instrumented should catch this earlier.
        is_newly_added = True
        for existing_inst in _active_instrumentors:
            if (
                hasattr(existing_inst, "_agentops_instrumented_package_key")
                and existing_inst._agentops_instrumented_package_key == package_name
            ):
                is_newly_added = False
                logger.debug(
                    f"_perform_instrumentation: Instrumentor for '{package_name}' already in _active_instrumentors. Not adding again."
                )
                break
        if is_newly_added:
            _active_instrumentors.append(instrumentor_instance)

        # If this was an agentic library AND it's newly effectively instrumented.
        if (
            package_name in AGENTIC_LIBRARIES and not _has_agentic_library
        ):  # Check _has_agentic_library to ensure this is the *first* one.
            # _uninstrument_providers() was already called in _should_instrument_package for the first agentic library.
            _has_agentic_library = True
    else:
        logger.debug(
            f"_perform_instrumentation: instrument_one for '{package_name}' returned None. Not added to active instrumentors."
        )


def _import_monitor(name: str, globals_dict=None, locals_dict=None, fromlist=(), level=0):
    """
    Monitor imports and instrument packages as they are imported.
    This replaces the built-in import function to intercept package imports.
    """
    global _instrumenting_packages, _has_agentic_library

    # If an agentic library is already instrumented, skip all further instrumentation
    if _has_agentic_library:
        return _original_builtins_import(name, globals_dict, locals_dict, fromlist, level)

    # First, do the actual import
    module = _original_builtins_import(name, globals_dict, locals_dict, fromlist, level)

    # Check for exact matches first (handles package.module like google.adk)
    packages_to_check = set()

    # Check the imported module itself
    if name in TARGET_PACKAGES:
        packages_to_check.add(name)
    else:
        # Check if any target package is a prefix of the import name
        for target in TARGET_PACKAGES:
            if name.startswith(target + ".") or name == target:
                packages_to_check.add(target)

    # For "from X import Y" style imports, also check submodules
    if fromlist:
        for item in fromlist:
            # Construct potential full name, e.g., "google.adk" from name="google", item="adk"
            # Or if name="os", item="path", full_name="os.path"
            # If the original name itself is a multi-part name like "a.b", and item is "c", then "a.b.c"
            # This logic needs to correctly identify the root package if 'name' is already a sub-package.
            # The existing TARGET_PACKAGES check is simpler: it checks against pre-defined full names.

            # Check full name if item forms part of a target package name
            full_item_name_candidate = f"{name}.{item}"

            if full_item_name_candidate in TARGET_PACKAGES:
                packages_to_check.add(full_item_name_candidate)
            else:  # Fallback to checking if 'name' itself is a target
                for target in TARGET_PACKAGES:
                    if name == target or name.startswith(target + "."):
                        packages_to_check.add(target)  # Check the base target if a submodule is imported from it.

    # Instrument all matching packages
    for package_to_check in packages_to_check:
        if package_to_check not in _instrumenting_packages and not _is_package_instrumented(package_to_check):
            target_module_obj = sys.modules.get(package_to_check)

            if target_module_obj:
                is_sdk = _is_installed_package(target_module_obj, package_to_check)
                if not is_sdk:
                    logger.info(
                        f"AgentOps: Target '{package_to_check}' appears to be a local module/directory. Skipping AgentOps SDK instrumentation for it."
                    )
                    continue
            else:
                logger.debug(
                    f"_import_monitor: No module object found in sys.modules for '{package_to_check}', proceeding with SDK instrumentation attempt."
                )

            _instrumenting_packages.add(package_to_check)
            try:
                _perform_instrumentation(package_to_check)
                # If we just instrumented an agentic library, stop
                if _has_agentic_library:
                    break
            except Exception as e:
                logger.error(f"Error instrumenting {package_to_check}: {str(e)}")
            finally:
                _instrumenting_packages.discard(package_to_check)

    return module


@dataclass
class InstrumentorLoader:
    """
    Represents a dynamically-loadable instrumentor.
    Handles version checking and instantiation of instrumentors.
    """

    module_name: str
    class_name: str
    min_version: str
    package_name: Optional[str] = None  # Optional: actual pip package name

    @property
    def module(self) -> ModuleType:
        """Get the instrumentor module."""
        return importlib.import_module(self.module_name)

    @property
    def should_activate(self) -> bool:
        """Check if the package is available and meets version requirements."""
        try:
            # Special case for stdlib modules (like concurrent.futures)
            if self.package_name == "python":
                import sys

                python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                return Version(python_version) >= parse(self.min_version)

            # Use explicit package_name if provided, otherwise derive from module_name
            if self.package_name:
                provider_name = self.package_name
            else:
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
        # This log is important for users to know why something wasn't instrumented.
        logger.info(
            f"AgentOps: Package '{loader.package_name or loader.module_name}' not found or version is less than minimum required ('{loader.min_version}'). Skipping instrumentation."
        )
        return None

    instrumentor = loader.get_instance()
    try:
        # Use the provider directly from the global tracer instance
        instrumentor.instrument(tracer_provider=tracer.provider)
        logger.info(
            f"AgentOps: Successfully instrumented '{loader.class_name}' for package '{loader.package_name or loader.module_name}'."
        )
    except Exception as e:
        logger.error(
            f"Failed to instrument {loader.class_name} for {loader.package_name or loader.module_name}: {e}",
            exc_info=True,
        )
    return instrumentor


def instrument_all():
    """Start monitoring and instrumenting packages if not already started."""
    # Check if active_instrumentors is empty, as a proxy for not started.
    if not _active_instrumentors:
        builtins.__import__ = _import_monitor
        global _instrumenting_packages, _has_agentic_library

        # If an agentic library is already instrumented, don't instrument anything else
        if _has_agentic_library:
            return

        for name in list(sys.modules.keys()):
            # Stop if an agentic library gets instrumented during the loop
            if _has_agentic_library:
                break

            module = sys.modules.get(name)
            if not isinstance(module, ModuleType):
                continue

            # Check for exact matches first (handles package.module like google.adk)
            package_to_check = None
            if name in TARGET_PACKAGES:
                package_to_check = name
            else:
                # Check if any target package is a prefix of the module name
                for target in TARGET_PACKAGES:
                    if name.startswith(target + ".") or name == target:
                        package_to_check = target
                        break

            if (
                package_to_check
                and package_to_check not in _instrumenting_packages
                and not _is_package_instrumented(package_to_check)
            ):
                target_module_obj = sys.modules.get(package_to_check)

                if target_module_obj:
                    is_sdk = _is_installed_package(target_module_obj, package_to_check)
                    if not is_sdk:
                        continue
                else:
                    logger.debug(
                        f"instrument_all: No module object found for '{package_to_check}' in sys.modules during startup scan. Proceeding cautiously."
                    )

                _instrumenting_packages.add(package_to_check)
                try:
                    _perform_instrumentation(package_to_check)
                except Exception as e:
                    logger.error(f"Error instrumenting {package_to_check}: {str(e)}")
                finally:
                    _instrumenting_packages.discard(package_to_check)


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
    active_libs = set()
    for name, module in sys.modules.items():
        if not isinstance(module, ModuleType):
            continue

        # Check for exact matches first
        if name in TARGET_PACKAGES:
            active_libs.add(name)
        else:
            # Check if any target package is a prefix of the module name
            for target in TARGET_PACKAGES:
                if name.startswith(target + ".") or name == target:
                    active_libs.add(target)
                    break

    return active_libs
