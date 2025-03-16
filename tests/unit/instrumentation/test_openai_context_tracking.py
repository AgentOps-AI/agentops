"""
Test OpenAI Context Tracking between different API calls

This test verifies that the trace context is properly maintained between
different types of OpenAI API calls, ensuring that response parsing spans
are correctly attached to their parent API call spans.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import pytest

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.span import SpanContext, TraceFlags

import agentops
from agentops.instrumentation.openai import OpenAIResponsesInstrumentor
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanAttributes, MessageAttributes, CoreAttributes

# Mock OpenAI API responses
CHAT_COMPLETION_RESPONSE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-4-turbo",
    "system_fingerprint": "fp_12345",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello, how can I help you today?",
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}

RESPONSE_API_RESPONSE = {
    "id": "resp_abc123",
    "object": "response",
    "created_at": 1683950300,
    "model": "o1",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": "Hello! How can I assist you today?"
                }
            ]
        }
    ],
    "usage": {
        "input_tokens": 15,
        "output_tokens": 25,
        "total_tokens": 40,
        "output_tokens_details": {
            "reasoning_tokens": 10
        }
    }
}


# Mock Response classes
class MockResponseBase:
    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return self.data

    def dict(self):
        return self.data

    @classmethod
    def parse(cls, data):
        return cls(data)


class MockLegacyAPIResponse(MockResponseBase):
    pass


class MockResponse(MockResponseBase):
    pass


# Span collector for test assertions
class TestSpanCollector(SpanProcessor):
    def __init__(self):
        self.spans = []
        self.span_dicts = []

    def on_start(self, span, parent_context):
        pass

    def on_end(self, span):
        self.spans.append(span)
        # Convert to dict for easier assertions
        span_dict = {
            "name": span.name,
            "trace_id": span.context.trace_id,
            "span_id": span.context.span_id,
            "parent_id": span.parent.span_id if span.parent else None,
            "attributes": dict(span.attributes),
        }
        self.span_dicts.append(span_dict)

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        pass


class TestOpenAIContextTracking(unittest.TestCase):
    """Test context tracking between different OpenAI API formats."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment with a custom TracerProvider."""
        # Initialize a custom tracer provider with a span collector
        cls.span_collector = TestSpanCollector()
        cls.tracer_provider = TracerProvider()
        cls.tracer_provider.add_span_processor(cls.span_collector)
        
        # Also add console exporter in verbose mode
        cls.tracer_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )
        
        # Patch TracingCore to use our custom tracer provider
        cls.original_get_instance = TracingCore.get_instance
        
        # Create a mock TracingCore instance
        mock_core = MagicMock()
        mock_core._provider = cls.tracer_provider
        
        # Patch get_instance to return our mock
        TracingCore.get_instance = MagicMock(return_value=mock_core)
        
        # Initialize AgentOps with instrumentation
        agentops.init(api_key="test-api-key", instrument_llm_calls=True)
        
        # Create and instrument our OpenAI responses instrumentor
        cls.instrumentor = OpenAIResponsesInstrumentor()
        cls.instrumentor.instrument(tracer_provider=cls.tracer_provider)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        # Restore original TracingCore get_instance
        TracingCore.get_instance = cls.original_get_instance
        
        # Uninstrument
        cls.instrumentor.uninstrument()

    def setUp(self):
        """Reset span collection before each test."""
        self.span_collector.spans = []
        self.span_collector.span_dicts = []

    @patch("openai._response.Response", MockResponse)
    @patch("openai._legacy_response.LegacyAPIResponse", MockLegacyAPIResponse)
    def test_openai_api_context_tracking(self):
        """Test that spans from different OpenAI APIs maintain trace context."""
        # Create a tracer for our test
        tracer = trace.get_tracer("test_tracer", tracer_provider=self.tracer_provider)
        
        # Simulate an API call workflow with a parent span
        with tracer.start_as_current_span("openai_api_workflow") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id
            parent_span_id = parent_span.get_span_context().span_id
            
            # Set some attributes on the parent span
            parent_span.set_attribute("workflow.name", "test_workflow")
            
            # 1. Simulate Chat Completions API call
            with tracer.start_as_current_span("openai.chat_completion") as chat_span:
                chat_span.set_attribute(SpanAttributes.LLM_SYSTEM, "openai")
                chat_span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, "gpt-4-turbo")
                
                # Simulate response parsing in the Chat Completions API
                chat_response = MockLegacyAPIResponse.parse(CHAT_COMPLETION_RESPONSE)
                
                # Manually extract and set attributes (normally done by the instrumentor)
                chat_span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, "gpt-4-turbo")
                chat_span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, 10)
            
            # 2. Simulate Response API call
            with tracer.start_as_current_span("openai.response_api") as response_span:
                response_span.set_attribute(SpanAttributes.LLM_SYSTEM, "openai")
                response_span.set_attribute(SpanAttributes.LLM_REQUEST_MODEL, "o1")
                
                # Simulate response parsing in the Response API
                response_api_response = MockResponse.parse(RESPONSE_API_RESPONSE)
                
                # Manually extract and set attributes
                response_span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, "o1")
                response_span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, 15)
        
        # Check that we have at least 6 spans:
        # 1. Parent workflow span
        # 2. Chat completion span
        # 3. Legacy response parse span (from instrumentor)
        # 4. Response API span
        # 5. Response parse span (from instrumentor)
        # Note: There might be more depending on how many spans are created inside the parse methods
        assert len(self.span_collector.spans) >= 5
        
        # Get spans by name
        spans_by_name = {}
        for span in self.span_collector.span_dicts:
            spans_by_name.setdefault(span["name"], []).append(span)
        
        # Verify parent workflow span
        workflow_spans = spans_by_name.get("openai_api_workflow", [])
        assert len(workflow_spans) == 1
        workflow_span = workflow_spans[0]
        assert workflow_span["trace_id"] == parent_trace_id
        assert workflow_span["span_id"] == parent_span_id
        
        # Verify chat completion span is a child of the workflow span
        chat_spans = spans_by_name.get("openai.chat_completion", [])
        assert len(chat_spans) == 1
        chat_span = chat_spans[0]
        assert chat_span["trace_id"] == parent_trace_id
        assert chat_span["parent_id"] == parent_span_id
        
        # Verify response API span is a child of the workflow span
        response_spans = spans_by_name.get("openai.response_api", [])
        assert len(response_spans) == 1
        response_span = response_spans[0]
        assert response_span["trace_id"] == parent_trace_id
        assert response_span["parent_id"] == parent_span_id
        
        # Verify legacy response parse spans
        legacy_parse_spans = spans_by_name.get("openai.legacy_response.parse", [])
        assert len(legacy_parse_spans) > 0
        for span in legacy_parse_spans:
            assert span["trace_id"] == parent_trace_id
            assert CoreAttributes.PARENT_ID in span["attributes"], "Parse span missing parent ID attribute"
        
        # Verify response parse spans
        response_parse_spans = spans_by_name.get("openai.response", [])
        assert len(response_parse_spans) > 0
        for span in response_parse_spans:
            assert span["trace_id"] == parent_trace_id
            assert CoreAttributes.PARENT_ID in span["attributes"], "Parse span missing parent ID attribute"
        
        # Print span hierarchy for debugging
        print("\nSpan Hierarchy:")
        for span in self.span_collector.span_dicts:
            parent = f" (parent: {span['parent_id']})" if span["parent_id"] else ""
            print(f"- {span['name']} (id: {span['span_id']}){parent}")
            
            # Print attributes related to context tracking
            attrs = span["attributes"]
            context_attrs = {k: v for k, v in attrs.items() if k.startswith("parent.") or k == CoreAttributes.PARENT_ID}
            if context_attrs:
                print(f"  Context attributes: {context_attrs}")


if __name__ == "__main__":
    unittest.main()