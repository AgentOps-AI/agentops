# Map-Agent Integration for AgentOps

This module provides comprehensive instrumentation for map-agent, a mapping and navigation agent framework. It hooks into map-agent's `telemetry.py` module to provide observability and monitoring capabilities through OpenTelemetry.

## Features

- **Telemetry Hooks**: Automatically instruments map-agent's telemetry functions
- **Navigation Tracking**: Monitors route calculations, location updates, and navigation events
- **Core Functionality**: Instruments key map-agent classes and methods
- **OpenTelemetry Integration**: Provides spans, metrics, and traces for comprehensive observability

## Instrumented Components

### Telemetry Functions
The integration hooks into common telemetry functions in `map_agent.telemetry`:
- `log_event` - General event logging
- `log_metric` - Metric collection
- `log_trace` - Trace logging
- `start_span` / `end_span` - Span management
- `log_navigation_event` - Navigation-specific events
- `log_route_calculation` - Route calculation logging
- `log_location_update` - Location tracking
- `send_telemetry` / `flush_telemetry` - Telemetry transmission

### Core Classes
The integration instruments common map-agent classes:
- `MapAgent` - Main agent class
- `NavigationAgent` - Navigation-specific agent
- `RouteCalculator` - Route calculation functionality
- `LocationTracker` - Location tracking
- `MapRenderer` - Map rendering

### Monitored Methods
Key methods that are automatically instrumented:
- `navigate()` - Navigation operations
- `calculate_route()` - Route calculations
- `update_location()` - Location updates
- `render_map()` - Map rendering
- `find_location()` - Location search
- `get_directions()` - Direction requests
- `track_movement()` - Movement tracking

## Attributes Captured

### Navigation Attributes
- `map_agent.navigation.destination` - Navigation target
- `map_agent.route.origin` - Route starting point
- `map_agent.route.destination` - Route ending point
- `map_agent.route.distance` - Calculated route distance
- `map_agent.route.duration` - Estimated travel time

### Location Attributes
- `map_agent.location.latitude` - Current latitude
- `map_agent.location.longitude` - Current longitude

### Telemetry Attributes
- `map_agent.telemetry.function` - Called telemetry function
- `map_agent.event.type` - Event type for logged events
- `map_agent.metric.name` - Metric name
- `map_agent.metric.value` - Metric value

## Usage

The integration is automatically activated when map-agent is detected in your environment. No manual configuration is required.

```python
import agentops
import map_agent

# Initialize AgentOps (this will automatically instrument map-agent)
agentops.init(api_key="your-api-key")

# Use map-agent normally - all telemetry will be captured
agent = map_agent.MapAgent()
route = agent.calculate_route("Start Location", "End Location")
agent.navigate(route)
```

## Requirements

- `map-agent >= 0.1.0`
- `opentelemetry-api`
- `opentelemetry-sdk`

## Span Structure

The integration creates spans with the following naming convention:
- `map_agent.telemetry.{function_name}` - For telemetry function calls
- `map_agent.{class_name}.{method_name}` - For core functionality

Example span hierarchy:
```
map_agent.MapAgent.navigate
├── map_agent.RouteCalculator.calculate_route
│   ├── map_agent.telemetry.log_route_calculation
│   └── map_agent.telemetry.log_metric
├── map_agent.LocationTracker.update_location
│   └── map_agent.telemetry.log_location_update
└── map_agent.telemetry.log_navigation_event
```

## Error Handling

The integration gracefully handles cases where:
- map-agent is not installed
- The telemetry module is not available
- Specific classes or methods don't exist
- Telemetry functions fail

All errors are logged at the debug level to avoid disrupting the main application flow.

## Customization

The integration can be extended to support additional map-agent functionality by:
1. Adding new function names to the `telemetry_functions` list
2. Adding new class names to the `classes_to_instrument` list
3. Adding new method names to the `methods_to_instrument` list
4. Implementing custom attribute extraction logic

## Thread Safety

The integration is thread-safe and uses proper locking mechanisms to ensure correct instrumentation in multi-threaded environments.