"""
Simple test script for OpenAI response instrumentation

This script demonstrates a simple example of response context tracking.
It can be run directly with Python to see the console output of spans.
"""

import sys
import os
from unittest.mock import patch, MagicMock

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

import agentops
from agentops.instrumentation.openai import OpenAIResponsesInstrumentor
from agentops.semconv import SpanAttributes

# Mock Response classes 
class MockResponse:
    def __init__(self, data):
        self.data = data
        
    def model_dump(self):
        return self.data
        
    @classmethod
    def parse(cls, data):
        return cls(data)

class MockLegacyResponse(MockResponse):
    pass

# Sample response data
CHAT_RESPONSE = {
    "id": "chat123",
    "model": "gpt-4",
    "choices": [{"message": {"role": "assistant", "content": "Hello"}}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
}

AGENTS_RESPONSE = {
    "id": "response123",
    "model": "gpt-4o",
    "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hi"}]}],
    "usage": {"input_tokens": 12, "output_tokens": 6, "total_tokens": 18}
}

def run_test():
    """Run a simple test of response context tracking."""
    # Set up a tracer provider with console exporter
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    
    # Create and instrument our OpenAI responses instrumentor
    with patch("openai.resources.responses.Response", MockResponse), \
         patch("openai.resources.chat.completions.ChatCompletion", MockLegacyResponse):
        
        # Initialize agentops and instrumentor
        agentops.init(api_key="test-api-key")
        instrumentor = OpenAIResponsesInstrumentor()
        instrumentor.instrument(tracer_provider=tracer_provider)
        
        # Get a tracer
        tracer = trace.get_tracer("test_tracer", tracer_provider=tracer_provider)
        
        # Create a workflow span
        with tracer.start_as_current_span("openai_workflow") as workflow_span:
            # Set some attributes
            workflow_span.set_attribute("workflow.name", "test_workflow")
            
            # Create a chat completion span
            with tracer.start_as_current_span("openai.chat_completion") as chat_span:
                chat_span.set_attribute(SpanAttributes.LLM_SYSTEM, "openai")
                chat_span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, "gpt-4")
                
                # Simulate response (this will trigger our instrumentor)
                MockLegacyResponse.parse(CHAT_RESPONSE)
                
            # Create a response API span    
            with tracer.start_as_current_span("openai.response") as response_span:
                response_span.set_attribute(SpanAttributes.LLM_SYSTEM, "openai")
                response_span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, "gpt-4o")
                
                # Simulate response (this will trigger our instrumentor)
                MockResponse.parse(AGENTS_RESPONSE)
                
        # Uninstrument
        instrumentor.uninstrument()
        
        print("Test completed. Check console output for spans.")

if __name__ == "__main__":
    run_test()