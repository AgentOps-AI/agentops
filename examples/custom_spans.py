#!/usr/bin/env python
"""
Example of creating and using custom spans with the AgentOps SDK.

This example demonstrates how to create custom spans for tracking specific
operations or components in your application.
"""

import os
import sys
import time
import random
from typing import List, Dict, Any

from agentops.config import Config
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators.session import session
from agentops.sdk.spans.custom import CustomSpan


def initialize_tracing():
    """Initialize the tracing core."""
    config = Config(
        api_key="test_key",  # Replace with your API key
        host="https://api.agentops.ai",  # Replace with your host
        project_id="example-project",  # Replace with your project ID
    )
    core = TracingCore.get_instance()
    core.initialize(config)
    return core


@session(name="custom_spans_session", tags=["example", "custom"])
class CustomSpansSession:
    """A session that demonstrates custom spans."""
    
    def __init__(self):
        """Initialize the session."""
        self.core = TracingCore.get_instance()
    
    def run(self) -> Dict[str, Any]:
        """Run the session with custom spans."""
        print("Starting custom spans session")
        
        # Create a custom span for data loading
        data_span = self.core.create_span(
            kind="custom",
            name="data_loading",
            parent=self._session_span,
            attributes={"operation": "load"},
            immediate_export=True
        )
        
        try:
            # Start the span
            data_span.start()
            
            # Simulate data loading
            print("Loading data...")
            time.sleep(0.5)
            data = self.load_data()
            
            # Add an event to the span
            data_span.add_event("data_loaded", {"data_size": len(data)})
            
            # End the span successfully
            data_span.end()
        except Exception as e:
            # End the span with error
            data_span.end(status="ERROR", description=str(e))
            raise
        
        # Create a custom span for data processing
        with self.core.create_span(
            kind="custom",
            name="data_processing",
            parent=self._session_span,
            attributes={"operation": "process"},
            immediate_export=True
        ) as process_span:
            # Simulate data processing
            print("Processing data...")
            time.sleep(0.7)
            processed_data = self.process_data(data)
            
            # Add an event to the span
            process_span.add_event("data_processed", {"processed_items": len(processed_data)})
        
        # Create a custom span for result generation
        with self.core.create_span(
            kind="custom",
            name="result_generation",
            parent=self._session_span,
            attributes={"operation": "generate"},
            immediate_export=True
        ) as result_span:
            # Simulate result generation
            print("Generating results...")
            time.sleep(0.3)
            results = self.generate_results(processed_data)
            
            # Add an event to the span
            result_span.add_event("results_generated", {"result_count": len(results)})
        
        print("Custom spans session completed")
        
        return {
            "data_size": len(data),
            "processed_items": len(processed_data),
            "results": results,
            "timestamp": time.time()
        }
    
    def load_data(self) -> List[Dict[str, Any]]:
        """Simulate loading data."""
        return [
            {"id": i, "name": f"Item {i}", "value": random.random()}
            for i in range(1, 11)
        ]
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate processing data."""
        return [
            {**item, "processed": True, "score": item["value"] * random.random()}
            for item in data
        ]
    
    def generate_results(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate generating results."""
        # Sort by score and take the top 5
        sorted_data = sorted(data, key=lambda x: x["score"], reverse=True)
        return sorted_data[:5]


def main():
    """Run the example."""
    # Initialize tracing
    initialize_tracing()
    
    # Create and run the session
    session = CustomSpansSession()
    result = session.run()
    
    # Print the result
    print("\nFinal result:")
    print(f"Data size: {result['data_size']}")
    print(f"Processed items: {result['processed_items']}")
    print("Top results:")
    for i, item in enumerate(result['results'], 1):
        print(f"  {i}. {item['name']} (score: {item['score']:.2f})")


if __name__ == "__main__":
    main()
