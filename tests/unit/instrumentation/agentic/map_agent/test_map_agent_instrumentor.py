"""Tests for Map-Agent instrumentation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry.trace import Status, StatusCode

from agentops.instrumentation.agentic.map_agent.instrumentor import MapAgentInstrumentor


class TestMapAgentInstrumentor:
    """Test suite for MapAgentInstrumentor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instrumentor = MapAgentInstrumentor()
        self.mock_tracer = Mock()
        self.instrumentor.tracer = self.mock_tracer

    def test_init(self):
        """Test instrumentor initialization."""
        assert isinstance(self.instrumentor._original_telemetry_functions, dict)
        assert len(self.instrumentor._original_telemetry_functions) == 0

    def test_instrumentation_dependencies(self):
        """Test instrumentation dependencies."""
        deps = self.instrumentor.instrumentation_dependencies()
        assert "map-agent >= 0.1.0" in deps

    def test_get_instrumentation_config(self):
        """Test instrumentation configuration."""
        config = self.instrumentor._get_instrumentation_config()
        assert config.module_name == "map_agent"
        assert config.service_name == "map-agent"
        assert config.span_prefix == "map_agent"
        assert config.metrics_prefix == "map_agent"

    @patch('agentops.instrumentation.agentic.map_agent.instrumentor.logger')
    def test_instrument_no_map_agent(self, mock_logger):
        """Test instrumentation when map-agent is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'map_agent'")):
            self.instrumentor._instrument()
        
        mock_logger.debug.assert_called_with("AgentOps: map-agent not found or telemetry module not available")

    @patch('agentops.instrumentation.agentic.map_agent.instrumentor.logger')
    def test_instrument_with_map_agent(self, mock_logger):
        """Test successful instrumentation of map-agent."""
        # Create mock telemetry module
        mock_telemetry_module = Mock()
        mock_telemetry_module.log_event = Mock()
        mock_telemetry_module.log_metric = Mock()
        mock_telemetry_module.start_span = Mock()
        
        # Create mock map_agent module
        mock_map_agent = Mock()
        mock_map_agent.MapAgent = Mock()
        
        with patch.dict('sys.modules', {
            'map_agent.telemetry': mock_telemetry_module,
            'map_agent': mock_map_agent
        }):
            self.instrumentor._instrument()
        
        # Verify telemetry functions were wrapped
        assert 'log_event' in self.instrumentor._original_telemetry_functions
        assert 'log_metric' in self.instrumentor._original_telemetry_functions
        assert 'start_span' in self.instrumentor._original_telemetry_functions
        
        mock_logger.debug.assert_any_call("AgentOps: Found map-agent telemetry module, instrumenting...")
        mock_logger.debug.assert_any_call("AgentOps: Successfully instrumented map-agent")

    def test_create_telemetry_wrapper(self):
        """Test telemetry function wrapper creation."""
        original_func = Mock(return_value="test_result")
        mock_span = Mock()
        self.mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        
        wrapper = self.instrumentor._create_telemetry_wrapper("log_event", original_func)
        result = wrapper("test_event", extra_data="test")
        
        # Verify original function was called
        original_func.assert_called_once_with("test_event", extra_data="test")
        assert result == "test_result"
        
        # Verify span was configured
        mock_span.set_attribute.assert_any_call("map_agent.telemetry.function", "log_event")
        mock_span.set_attribute.assert_any_call("map_agent.telemetry.args_count", 1)
        mock_span.set_attribute.assert_any_call("map_agent.telemetry.kwargs_count", 1)
        mock_span.set_status.assert_called_with(Status(StatusCode.OK))

    def test_create_telemetry_wrapper_with_exception(self):
        """Test telemetry wrapper exception handling."""
        original_func = Mock(side_effect=ValueError("Test error"))
        mock_span = Mock()
        self.mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        
        wrapper = self.instrumentor._create_telemetry_wrapper("log_event", original_func)
        
        with pytest.raises(ValueError, match="Test error"):
            wrapper("test_event")
        
        # Verify error was recorded
        mock_span.set_status.assert_called()
        mock_span.record_exception.assert_called()

    def test_add_telemetry_attributes_log_event(self):
        """Test telemetry attributes for log_event function."""
        mock_span = Mock()
        args = ("navigation_start",)
        kwargs = {"user_id": "123"}
        
        self.instrumentor._add_telemetry_attributes(mock_span, "log_event", args, kwargs)
        
        mock_span.set_attribute.assert_any_call("map_agent.telemetry.function", "log_event")
        mock_span.set_attribute.assert_any_call("map_agent.event.type", "navigation_start")
        mock_span.set_attribute.assert_any_call("map_agent.telemetry.args_count", 1)
        mock_span.set_attribute.assert_any_call("map_agent.telemetry.kwargs_count", 1)

    def test_add_telemetry_attributes_log_metric(self):
        """Test telemetry attributes for log_metric function."""
        mock_span = Mock()
        args = ("route_distance", 15.5)
        kwargs = {}
        
        self.instrumentor._add_telemetry_attributes(mock_span, "log_metric", args, kwargs)
        
        mock_span.set_attribute.assert_any_call("map_agent.metric.name", "route_distance")
        mock_span.set_attribute.assert_any_call("map_agent.metric.value", "15.5")

    def test_add_telemetry_attributes_location_update(self):
        """Test telemetry attributes for location update function."""
        mock_span = Mock()
        args = ()
        kwargs = {"latitude": 40.7128, "longitude": -74.0060}
        
        self.instrumentor._add_telemetry_attributes(mock_span, "log_location_update", args, kwargs)
        
        mock_span.set_attribute.assert_any_call("map_agent.location.latitude", "40.7128")
        mock_span.set_attribute.assert_any_call("map_agent.location.longitude", "-74.0060")

    def test_add_telemetry_attributes_route_calculation(self):
        """Test telemetry attributes for route calculation function."""
        mock_span = Mock()
        args = ()
        kwargs = {"origin": "New York", "destination": "Boston"}
        
        self.instrumentor._add_telemetry_attributes(mock_span, "log_route_calculation", args, kwargs)
        
        mock_span.set_attribute.assert_any_call("map_agent.route.origin", "New York")
        mock_span.set_attribute.assert_any_call("map_agent.route.destination", "Boston")

    def test_create_method_wrapper(self):
        """Test method wrapper creation."""
        original_method = Mock(return_value=Mock(distance=100, duration=600))
        mock_span = Mock()
        self.mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        
        wrapper = self.instrumentor._create_method_wrapper("RouteCalculator", "calculate_route", original_method)
        
        # Create a mock self object
        mock_self = Mock()
        result = wrapper(mock_self, "Start", "End", mode="driving")
        
        # Verify original method was called
        original_method.assert_called_once_with(mock_self, "Start", "End", mode="driving")
        
        # Verify span attributes
        mock_span.set_attribute.assert_any_call("map_agent.class", "RouteCalculator")
        mock_span.set_attribute.assert_any_call("map_agent.method", "calculate_route")
        mock_span.set_attribute.assert_any_call("map_agent.route.origin", "Start")
        mock_span.set_attribute.assert_any_call("map_agent.route.destination", "End")
        mock_span.set_attribute.assert_any_call("map_agent.route.distance", "100")
        mock_span.set_attribute.assert_any_call("map_agent.route.duration", "600")

    def test_create_method_wrapper_navigation(self):
        """Test method wrapper for navigation method."""
        original_method = Mock(return_value=None)
        mock_span = Mock()
        self.mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        
        wrapper = self.instrumentor._create_method_wrapper("MapAgent", "navigate", original_method)
        
        mock_self = Mock()
        wrapper(mock_self, "Times Square")
        
        mock_span.set_attribute.assert_any_call("map_agent.navigation.destination", "Times Square")

    def test_create_method_wrapper_location_update(self):
        """Test method wrapper for location update method."""
        original_method = Mock(return_value=None)
        mock_span = Mock()
        self.mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        
        wrapper = self.instrumentor._create_method_wrapper("LocationTracker", "update_location", original_method)
        
        mock_self = Mock()
        wrapper(mock_self, lat=40.7128, lon=-74.0060)
        
        mock_span.set_attribute.assert_any_call("map_agent.location.latitude", "40.7128")
        mock_span.set_attribute.assert_any_call("map_agent.location.longitude", "-74.0060")

    @patch('agentops.instrumentation.agentic.map_agent.instrumentor.logger')
    def test_uninstrument(self, mock_logger):
        """Test uninstrumentation."""
        # Set up some original functions
        self.instrumentor._original_telemetry_functions = {
            'log_event': Mock(),
            'log_metric': Mock()
        }
        
        mock_telemetry_module = Mock()
        
        with patch.dict('sys.modules', {'map_agent.telemetry': mock_telemetry_module}):
            self.instrumentor._uninstrument()
        
        # Verify original functions were restored
        assert hasattr(mock_telemetry_module, 'log_event')
        assert hasattr(mock_telemetry_module, 'log_metric')
        assert len(self.instrumentor._original_telemetry_functions) == 0
        
        mock_logger.debug.assert_called_with("AgentOps: Successfully uninstrumented map-agent")

    @patch('agentops.instrumentation.agentic.map_agent.instrumentor.logger')
    def test_uninstrument_error(self, mock_logger):
        """Test uninstrumentation error handling."""
        self.instrumentor._original_telemetry_functions = {'log_event': Mock()}
        
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            self.instrumentor._uninstrument()
        
        mock_logger.error.assert_called()

    def test_instrument_class(self):
        """Test class instrumentation."""
        mock_class = Mock()
        mock_class.__name__ = "TestClass"
        mock_class.navigate = Mock()
        mock_class.calculate_route = Mock()
        
        self.instrumentor._instrument_class(mock_class)
        
        # Verify methods were wrapped
        assert mock_class.navigate != Mock()  # Should be wrapped
        assert mock_class.calculate_route != Mock()  # Should be wrapped

    @patch('agentops.instrumentation.agentic.map_agent.instrumentor.logger')
    def test_instrument_core_functionality_no_module(self, mock_logger):
        """Test core functionality instrumentation when module is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'map_agent'")):
            self.instrumentor._instrument_core_functionality()
        
        mock_logger.debug.assert_called_with("AgentOps: map-agent core module not available for instrumentation")

    def test_instrument_core_functionality_success(self):
        """Test successful core functionality instrumentation."""
        mock_map_agent = Mock()
        mock_map_agent.MapAgent = Mock()
        mock_map_agent.MapAgent.__name__ = "MapAgent"
        mock_map_agent.MapAgent.navigate = Mock()
        
        with patch.dict('sys.modules', {'map_agent': mock_map_agent}):
            self.instrumentor._instrument_core_functionality()
        
        # Verify the class was instrumented
        assert hasattr(mock_map_agent.MapAgent, 'navigate')