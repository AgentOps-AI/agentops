# Map-Agent Integration Example

This example demonstrates how AgentOps automatically instruments map-agent to provide comprehensive observability for navigation and mapping operations.

## Overview

The map-agent integration hooks into the `telemetry.py` module of map-agent to capture:
- Navigation events and waypoints
- Route calculations and optimizations
- Location searches and updates
- Performance metrics and timing data

## Files

- `map_agent_example.py` - Main example script showing integration usage
- `README.md` - This documentation file

## What Gets Captured

When you run this example with AgentOps, you'll see telemetry data for:

### Navigation Operations
- Route calculations with origin/destination
- Navigation start/complete events
- Waypoint reached events
- Location updates with coordinates

### Metrics
- Route distance and duration
- Search result counts
- Calculation counts
- Performance timing

### Spans
- `map_agent.MapAgent.calculate_route` - Route calculation operations
- `map_agent.MapAgent.navigate` - Navigation sessions
- `map_agent.MapAgent.find_location` - Location searches
- `map_agent.telemetry.log_event` - Event logging
- `map_agent.telemetry.log_metric` - Metric collection
- `map_agent.telemetry.log_location_update` - Location tracking

## Running the Example

1. Install AgentOps:
   ```bash
   pip install agentops
   ```

2. Get your API key from [AgentOps Dashboard](https://app.agentops.ai)

3. Update the API key in `map_agent_example.py`

4. Run the example:
   ```bash
   python map_agent_example.py
   ```

5. Check your AgentOps dashboard to see the captured data

## Mock Implementation

This example uses mock classes to simulate map-agent functionality since the actual map-agent package may not be publicly available. In a real implementation:

- Replace mock classes with actual map-agent imports
- The AgentOps integration will automatically detect and instrument the real map-agent
- All telemetry hooks will work seamlessly with the actual implementation

## Expected Output

When you run the example, you'll see:

```
=== Map-Agent Integration Example ===

AgentOps initialized - map-agent integration is now active!

1. Searching for location...
Telemetry: Event 'location_search' - {'query': 'Central Park'}
Telemetry: Metric 'search_results' = 1 
Found: Central Park at 40.7831, -73.9712

2. Calculating route...
Telemetry: Route from 'Times Square' to 'Central Park' - 15.5km, 25.0min
Telemetry: Metric 'route_distance' = 15.5 km
Telemetry: Metric 'route_duration' = 25.0 min
Route calculated: 15.5km, 25.0 minutes

3. Starting navigation...
Telemetry: Event 'navigation_start' - {'destination': 'Central Park'}
Telemetry: Location update - 40.7128, -74.006
Telemetry: Event 'waypoint_reached' - {'waypoint': 1, 'name': 'Start'}
Telemetry: Location update - 40.7589, -73.9851
Telemetry: Event 'waypoint_reached' - {'waypoint': 2, 'name': 'Midpoint'}
Telemetry: Location update - 40.7831, -73.9712
Telemetry: Event 'waypoint_reached' - {'waypoint': 3, 'name': 'Central Park'}
Telemetry: Event 'navigation_complete' - {'destination': 'Central Park'}
Navigation completed: True

4. Advanced route calculation...
Telemetry: Metric 'calculation_count' = 1
Telemetry: Route from 'Brooklyn Bridge' to 'Manhattan Bridge' - 18.2km, 32.0min
Toll-free route: 18.2km, 32.0 minutes

Telemetry: Metric 'calculation_count' = 2
Telemetry: Route from 'Brooklyn Bridge' to 'Manhattan Bridge' - 15.5km, 25.0min
Fastest route: 15.5km, 25.0 minutes

=== All operations completed! ===
Check your AgentOps dashboard to see the captured telemetry data.
```

## Dashboard View

In your AgentOps dashboard, you'll see:

- **Session Overview**: Complete navigation session with timing
- **Span Traces**: Hierarchical view of route calculations and navigation
- **Metrics**: Distance, duration, and performance metrics
- **Events**: Navigation events, waypoints, and location updates
- **Attributes**: Detailed information about routes, locations, and preferences

## Integration Benefits

The map-agent integration provides:

1. **Complete Visibility**: See every navigation operation and decision
2. **Performance Monitoring**: Track route calculation times and efficiency
3. **Error Tracking**: Catch and analyze navigation failures
4. **Usage Analytics**: Understand how your mapping features are used
5. **Debugging Support**: Detailed traces for troubleshooting issues