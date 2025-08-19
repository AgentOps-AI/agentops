"""
Map-Agent Integration Example

This example demonstrates how AgentOps automatically instruments map-agent
to provide comprehensive observability for navigation and mapping operations.
"""

import agentops
import time
from typing import Optional, Dict, Any


# Mock map-agent classes for demonstration
# In real usage, these would be imported from the actual map-agent package
class MockTelemetry:
    """Mock telemetry module for demonstration."""
    
    @staticmethod
    def log_event(event_type: str, data: Optional[Dict[str, Any]] = None):
        """Log a navigation event."""
        print(f"Telemetry: Event '{event_type}' - {data}")
    
    @staticmethod
    def log_metric(metric_name: str, value: float, unit: str = ""):
        """Log a metric value."""
        print(f"Telemetry: Metric '{metric_name}' = {value} {unit}")
    
    @staticmethod
    def log_location_update(latitude: float, longitude: float):
        """Log a location update."""
        print(f"Telemetry: Location update - {latitude}, {longitude}")
    
    @staticmethod
    def log_route_calculation(origin: str, destination: str, distance: float, duration: float):
        """Log route calculation details."""
        print(f"Telemetry: Route from '{origin}' to '{destination}' - {distance}km, {duration}min")


class Route:
    """Mock route object."""
    
    def __init__(self, origin: str, destination: str, distance: float, duration: float):
        self.origin = origin
        self.destination = destination
        self.distance = distance  # in kilometers
        self.duration = duration  # in minutes


class MapAgent:
    """Mock MapAgent class for demonstration."""
    
    def __init__(self, name: str = "DefaultMapAgent"):
        self.name = name
        self.current_location = {"lat": 0.0, "lon": 0.0}
        print(f"Initialized MapAgent: {name}")
    
    def calculate_route(self, origin: str, destination: str, mode: str = "driving") -> Route:
        """Calculate a route between two locations."""
        # Simulate route calculation
        distance = 15.5  # km
        duration = 25.0  # minutes
        
        # Log the calculation via telemetry
        MockTelemetry.log_route_calculation(origin, destination, distance, duration)
        MockTelemetry.log_metric("route_distance", distance, "km")
        MockTelemetry.log_metric("route_duration", duration, "min")
        
        return Route(origin, destination, distance, duration)
    
    def navigate(self, destination: str) -> bool:
        """Navigate to a destination."""
        MockTelemetry.log_event("navigation_start", {"destination": destination})
        
        # Simulate navigation steps
        waypoints = [
            {"lat": 40.7128, "lon": -74.0060, "name": "Start"},
            {"lat": 40.7589, "lon": -73.9851, "name": "Midpoint"},
            {"lat": 40.7831, "lon": -73.9712, "name": destination}
        ]
        
        for i, waypoint in enumerate(waypoints):
            time.sleep(0.1)  # Simulate travel time
            self.update_location(waypoint["lat"], waypoint["lon"])
            MockTelemetry.log_event("waypoint_reached", {
                "waypoint": i + 1,
                "name": waypoint["name"]
            })
        
        MockTelemetry.log_event("navigation_complete", {"destination": destination})
        return True
    
    def update_location(self, lat: float, lon: float):
        """Update current location."""
        self.current_location = {"lat": lat, "lon": lon}
        MockTelemetry.log_location_update(lat, lon)
    
    def find_location(self, query: str) -> Dict[str, Any]:
        """Find a location by search query."""
        MockTelemetry.log_event("location_search", {"query": query})
        
        # Mock search result
        result = {
            "name": query,
            "lat": 40.7831,
            "lon": -73.9712,
            "address": f"123 Main St, {query}"
        }
        
        MockTelemetry.log_metric("search_results", 1)
        return result


class RouteCalculator:
    """Mock RouteCalculator class for demonstration."""
    
    def __init__(self):
        self.calculation_count = 0
    
    def calculate_route(self, origin: str, destination: str, preferences: Dict[str, Any] = None) -> Route:
        """Calculate optimal route with preferences."""
        self.calculation_count += 1
        
        # Simulate different route calculations based on preferences
        if preferences and preferences.get("avoid_tolls"):
            distance = 18.2
            duration = 32.0
        else:
            distance = 15.5
            duration = 25.0
        
        MockTelemetry.log_metric("calculation_count", self.calculation_count)
        MockTelemetry.log_route_calculation(origin, destination, distance, duration)
        
        return Route(origin, destination, distance, duration)


def main():
    """Main example function."""
    print("=== Map-Agent Integration Example ===\n")
    
    # Initialize AgentOps - this will automatically detect and instrument map-agent
    agentops.init(
        api_key="your-api-key-here",  # Replace with your actual API key
        default_tags=["map-agent-example", "navigation"],
        auto_start_session=True
    )
    
    print("AgentOps initialized - map-agent integration is now active!\n")
    
    try:
        # Create map agent instance
        agent = MapAgent("NYC_Navigator")
        
        # Perform location search
        print("1. Searching for location...")
        location = agent.find_location("Central Park")
        print(f"Found: {location['name']} at {location['lat']}, {location['lon']}\n")
        
        # Calculate route
        print("2. Calculating route...")
        route = agent.calculate_route("Times Square", "Central Park", mode="walking")
        print(f"Route calculated: {route.distance}km, {route.duration} minutes\n")
        
        # Navigate to destination
        print("3. Starting navigation...")
        success = agent.navigate("Central Park")
        print(f"Navigation completed: {success}\n")
        
        # Use RouteCalculator for advanced routing
        print("4. Advanced route calculation...")
        calculator = RouteCalculator()
        
        # Calculate route avoiding tolls
        toll_free_route = calculator.calculate_route(
            "Brooklyn Bridge", 
            "Manhattan Bridge", 
            preferences={"avoid_tolls": True}
        )
        print(f"Toll-free route: {toll_free_route.distance}km, {toll_free_route.duration} minutes\n")
        
        # Calculate fastest route
        fast_route = calculator.calculate_route("Brooklyn Bridge", "Manhattan Bridge")
        print(f"Fastest route: {fast_route.distance}km, {fast_route.duration} minutes\n")
        
        print("=== All operations completed! ===")
        print("Check your AgentOps dashboard to see the captured telemetry data.")
        
    except Exception as e:
        print(f"Error during execution: {e}")
    
    finally:
        # End the session
        agentops.end_session("Success")


if __name__ == "__main__":
    main()