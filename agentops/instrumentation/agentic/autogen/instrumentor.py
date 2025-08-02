"""AutoGen (Original) Instrumentation Module

This module provides a clean, modular instrumentation for the original AutoGen framework.
It uses specialized instrumentors for different agent types and operations.
"""

import logging
from typing import Dict, Any
from opentelemetry.metrics import Meter
from wrapt import wrap_function_wrapper
from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    StandardMetrics,
    SpanAttributeManager,
)
from agentops.instrumentation.agentic.autogen import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.agentic.autogen.noop_tracer import disable_autogen_telemetry, restore_autogen_telemetry

# Import modular instrumentors
from .agents import (
    BaseChatAgentInstrumentor,
    AssistantAgentInstrumentor,
    UserProxyAgentInstrumentor,
    CodeExecutorAgentInstrumentor,
    SocietyOfMindAgentInstrumentor,
)
from .teams import (
    RoundRobinGroupChatInstrumentor,
    SelectorGroupChatInstrumentor,
    SwarmInstrumentor,
)

logger = logging.getLogger(__name__)


class AutoGenInstrumentor(CommonInstrumentor):
    """Refactored Instrumentor for original AutoGen framework

    This instrumentor uses modular agent-specific instrumentors for clean
    separation of concerns and better maintainability.
    """

    def __init__(self):
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=[],
            metrics_enabled=True,
            dependencies=["autogen_agentchat >= 0.6.4"],
        )
        super().__init__(config)
        self._attribute_manager = None
        self._agent_instrumentors = []
        self._team_instrumentors = []

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for AutoGen instrumentation."""
        return StandardMetrics.create_standard_metrics(meter)

    def _initialize(self, **kwargs):
        """Initialize attribute manager and modular instrumentors."""
        self._attribute_manager = SpanAttributeManager(service_name="agentops", deployment_environment="production")

        # Initialize agent instrumentors
        self._agent_instrumentors = [
            BaseChatAgentInstrumentor(self._tracer, self._attribute_manager),
            AssistantAgentInstrumentor(self._tracer, self._attribute_manager),
            UserProxyAgentInstrumentor(self._tracer, self._attribute_manager),
            CodeExecutorAgentInstrumentor(self._tracer, self._attribute_manager),
            SocietyOfMindAgentInstrumentor(self._tracer, self._attribute_manager),
        ]

        # Initialize team instrumentors
        self._team_instrumentors = [
            RoundRobinGroupChatInstrumentor(self._tracer, self._attribute_manager),
            SelectorGroupChatInstrumentor(self._tracer, self._attribute_manager),
            SwarmInstrumentor(self._tracer, self._attribute_manager),
        ]

    def _enhance_autogen_core_telemetry(self):
        """Disable autogen-core's telemetry to prevent duplicate spans."""
        disable_autogen_telemetry()

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping using modular instrumentors."""
        logger.debug("[AutoGen DEBUG] Starting modular wrapping for AutoGen methods...")

        # Disable autogen-core's telemetry
        self._enhance_autogen_core_telemetry()

        # Collect all wrappers from agent instrumentors
        all_wrappers = []

        for instrumentor in self._agent_instrumentors:
            wrappers = instrumentor.get_wrappers()
            all_wrappers.extend(wrappers)

        for instrumentor in self._team_instrumentors:
            wrappers = instrumentor.get_wrappers()
            all_wrappers.extend(wrappers)

        # Apply all wrappers
        for wrapper_data in all_wrappers:
            try:
                # Support both 3-tuple (class, method, factory) and 4-tuple (module, class, method, factory)
                if len(wrapper_data) == 4:
                    module_name, class_name, method_name, wrapper_factory = wrapper_data
                else:
                    class_name, method_name, wrapper_factory = wrapper_data  # type: ignore
                    module_name = "autogen_agentchat.agents"

                wrapper = wrapper_factory()
                wrap_function_wrapper(module_name, f"{class_name}.{method_name}", wrapper)

            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"[AutoGen DEBUG] Failed to wrap {wrapper_data}: {e}")

    def _custom_unwrap(self, **kwargs):
        """Remove instrumentation from AutoGen using modular approach."""
        logger.debug("[AutoGen DEBUG] Unwrapping AutoGen methods...")

        # Restore autogen-core's original telemetry
        restore_autogen_telemetry()

        # Collect all method paths to unwrap
        all_method_paths = []

        def _add_paths_from_wrappers(wrappers):
            for wrapper_data in wrappers:
                if len(wrapper_data) == 4:
                    module_name, class_name, method_name, _ = wrapper_data
                else:
                    class_name, method_name, _ = wrapper_data  # type: ignore
                    module_name = "autogen_agentchat.agents"
                all_method_paths.append((module_name, f"{class_name}.{method_name}"))

        for instrumentor in self._agent_instrumentors:
            _add_paths_from_wrappers(instrumentor.get_wrappers())

        for instrumentor in self._team_instrumentors:
            _add_paths_from_wrappers(instrumentor.get_wrappers())

        # Unwrap all methods
        for module, method in all_method_paths:
            try:
                otel_unwrap(module, method)
            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Failed to unwrap {method}: {e}")

    def get_agent_instrumentor(self, agent_type: str):
        """Get a specific agent instrumentor by type."""
        instrumentor_map = {
            "BaseChatAgent": BaseChatAgentInstrumentor,
            "AssistantAgent": AssistantAgentInstrumentor,
            "UserProxyAgent": UserProxyAgentInstrumentor,
            "CodeExecutorAgent": CodeExecutorAgentInstrumentor,
            "SocietyOfMindAgent": SocietyOfMindAgentInstrumentor,
        }

        instrumentor_class = instrumentor_map.get(agent_type)
        if instrumentor_class:
            for instrumentor in self._agent_instrumentors:
                if isinstance(instrumentor, instrumentor_class):
                    return instrumentor
        return None

    def get_team_instrumentor(self, team_type: str):
        """Get a specific team instrumentor by type."""
        instrumentor_map = {
            "RoundRobinGroupChat": RoundRobinGroupChatInstrumentor,
            "SelectorGroupChat": SelectorGroupChatInstrumentor,
            "Swarm": SwarmInstrumentor,
        }

        instrumentor_class = instrumentor_map.get(team_type)
        if instrumentor_class:
            for instrumentor in self._team_instrumentors:
                if isinstance(instrumentor, instrumentor_class):
                    return instrumentor
        return None
