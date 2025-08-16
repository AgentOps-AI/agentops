"""Map-Agent Instrumentation for AgentOps

This module provides instrumentation for map-agent, implementing OpenTelemetry
instrumentation for map-agent's telemetry hooks and navigation workflows.
"""

from typing import Any, Dict, Optional, Collection
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import Meter
import threading
import json

from agentops.logging import logger
from agentops.instrumentation.common import (
    CommonInstrumentor,
    StandardMetrics,
    InstrumentorConfig,
)
from agentops.instrumentation.common.wrappers import WrapConfig


class MapAgentInstrumentor(CommonInstrumentor):
    """Instrumentor for map-agent framework."""

    def __init__(self):
        super().__init__()
        self._original_telemetry_functions = {}
        self._lock = threading.Lock()

    def _get_instrumentation_config(self) -> InstrumentorConfig:
        """Get the instrumentation configuration for map-agent."""
        return InstrumentorConfig(
            module_name="map_agent",
            service_name="map-agent",
            span_prefix="map_agent",
            metrics_prefix="map_agent",
        )

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return the dependencies required for instrumentation."""
        return ("map-agent >= 0.1.0",)

    def _instrument(self, **kwargs):
        """Instrument map-agent by hooking into their telemetry.py module."""
        try:
            # Try to import map-agent telemetry module
            import map_agent.telemetry as telemetry_module
            
            logger.debug("AgentOps: Found map-agent telemetry module, instrumenting...")
            
            # Hook into telemetry functions
            self._instrument_telemetry_module(telemetry_module)
            
            # Hook into core map-agent functionality if available
            self._instrument_core_functionality()
            
            logger.debug("AgentOps: Successfully instrumented map-agent")
            
        except ImportError:
            logger.debug("AgentOps: map-agent not found or telemetry module not available")
        except Exception as e:
            logger.error(f"AgentOps: Error instrumenting map-agent: {e}")

    def _uninstrument(self, **kwargs):
        """Uninstrument map-agent by restoring original functions."""
        try:
            # Restore original telemetry functions
            if hasattr(self, '_original_telemetry_functions'):
                import map_agent.telemetry as telemetry_module
                
                for func_name, original_func in self._original_telemetry_functions.items():
                    setattr(telemetry_module, func_name, original_func)
                
                self._original_telemetry_functions.clear()
            
            logger.debug("AgentOps: Successfully uninstrumented map-agent")
            
        except Exception as e:
            logger.error(f"AgentOps: Error uninstrumenting map-agent: {e}")

    def _instrument_telemetry_module(self, telemetry_module):
        """Instrument the telemetry module functions."""
        # Common telemetry function names to hook into
        telemetry_functions = [
            'log_event',
            'log_metric',
            'log_trace',
            'start_span',
            'end_span',
            'log_navigation_event',
            'log_route_calculation',
            'log_location_update',
            'send_telemetry',
            'flush_telemetry',
        ]
        
        for func_name in telemetry_functions:
            if hasattr(telemetry_module, func_name):
                original_func = getattr(telemetry_module, func_name)
                self._original_telemetry_functions[func_name] = original_func
                
                # Create wrapped version
                wrapped_func = self._create_telemetry_wrapper(func_name, original_func)
                setattr(telemetry_module, func_name, wrapped_func)

    def _create_telemetry_wrapper(self, func_name: str, original_func):
        """Create a wrapper for telemetry functions."""
        def wrapper(*args, **kwargs):
            span_name = f"map_agent.telemetry.{func_name}"
            
            with self.tracer.start_as_current_span(span_name) as span:
                try:
                    # Add attributes based on function name and arguments
                    self._add_telemetry_attributes(span, func_name, args, kwargs)
                    
                    # Call original function
                    result = original_func(*args, **kwargs)
                    
                    # Add result attributes if applicable
                    if result is not None:
                        span.set_attribute("map_agent.telemetry.result_type", type(result).__name__)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper

    def _add_telemetry_attributes(self, span, func_name: str, args, kwargs):
        """Add attributes to telemetry spans based on function and arguments."""
        span.set_attribute("map_agent.telemetry.function", func_name)
        span.set_attribute("map_agent.telemetry.args_count", len(args))
        span.set_attribute("map_agent.telemetry.kwargs_count", len(kwargs))
        
        # Function-specific attributes
        if func_name in ['log_event', 'log_navigation_event']:
            if args:
                span.set_attribute("map_agent.event.type", str(args[0])[:100])
        elif func_name == 'log_metric':
            if args:
                span.set_attribute("map_agent.metric.name", str(args[0])[:100])
                if len(args) > 1:
                    span.set_attribute("map_agent.metric.value", str(args[1])[:100])
        elif func_name in ['start_span', 'end_span']:
            if args:
                span.set_attribute("map_agent.span.name", str(args[0])[:100])
        elif func_name == 'log_location_update':
            if kwargs.get('latitude'):
                span.set_attribute("map_agent.location.latitude", str(kwargs['latitude']))
            if kwargs.get('longitude'):
                span.set_attribute("map_agent.location.longitude", str(kwargs['longitude']))
        elif func_name == 'log_route_calculation':
            if kwargs.get('origin'):
                span.set_attribute("map_agent.route.origin", str(kwargs['origin'])[:100])
            if kwargs.get('destination'):
                span.set_attribute("map_agent.route.destination", str(kwargs['destination'])[:100])

    def _instrument_core_functionality(self):
        """Instrument core map-agent functionality beyond telemetry."""
        try:
            # Try to hook into main map-agent classes
            import map_agent
            
            # Common map-agent class names to instrument
            classes_to_instrument = [
                'MapAgent',
                'NavigationAgent', 
                'RouteCalculator',
                'LocationTracker',
                'MapRenderer',
            ]
            
            for class_name in classes_to_instrument:
                if hasattr(map_agent, class_name):
                    self._instrument_class(getattr(map_agent, class_name))
                    
        except ImportError:
            logger.debug("AgentOps: map-agent core module not available for instrumentation")
        except Exception as e:
            logger.debug(f"AgentOps: Could not instrument map-agent core functionality: {e}")

    def _instrument_class(self, cls):
        """Instrument a map-agent class with common methods."""
        methods_to_instrument = [
            'navigate',
            'calculate_route',
            'update_location',
            'render_map',
            'find_location',
            'get_directions',
            'track_movement',
        ]
        
        for method_name in methods_to_instrument:
            if hasattr(cls, method_name):
                original_method = getattr(cls, method_name)
                wrapped_method = self._create_method_wrapper(cls.__name__, method_name, original_method)
                setattr(cls, method_name, wrapped_method)

    def _create_method_wrapper(self, class_name: str, method_name: str, original_method):
        """Create a wrapper for map-agent class methods."""
        def wrapper(self, *args, **kwargs):
            span_name = f"map_agent.{class_name}.{method_name}"
            
            with self.tracer.start_as_current_span(span_name) as span:
                try:
                    # Add method attributes
                    span.set_attribute("map_agent.class", class_name)
                    span.set_attribute("map_agent.method", method_name)
                    span.set_attribute("map_agent.args_count", len(args))
                    
                    # Method-specific attributes
                    if method_name == 'navigate' and args:
                        span.set_attribute("map_agent.navigation.destination", str(args[0])[:100])
                    elif method_name == 'calculate_route':
                        if args:
                            span.set_attribute("map_agent.route.origin", str(args[0])[:100])
                        if len(args) > 1:
                            span.set_attribute("map_agent.route.destination", str(args[1])[:100])
                    elif method_name == 'update_location':
                        if kwargs.get('lat'):
                            span.set_attribute("map_agent.location.latitude", str(kwargs['lat']))
                        if kwargs.get('lon'):
                            span.set_attribute("map_agent.location.longitude", str(kwargs['lon']))
                    
                    # Call original method
                    result = original_method(self, *args, **kwargs)
                    
                    # Add result attributes
                    if result is not None:
                        span.set_attribute("map_agent.result.type", type(result).__name__)
                        if method_name == 'calculate_route' and hasattr(result, 'distance'):
                            span.set_attribute("map_agent.route.distance", str(result.distance))
                        if method_name == 'calculate_route' and hasattr(result, 'duration'):
                            span.set_attribute("map_agent.route.duration", str(result.duration))
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper