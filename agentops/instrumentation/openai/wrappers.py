"""Wrapper functions for OpenAI API instrumentation.

This module contains wrapper functions for the OpenAI API calls,
including both synchronous and asynchronous variants.
"""
from opentelemetry import context as context_api
from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY
from opentelemetry.trace import SpanKind, Status, StatusCode
import time


def _create_response_span(tracer, span_name="openai.responses.create"):
    """Create a span for an OpenAI Responses API call.
    
    Args:
        tracer: The OpenTelemetry tracer to use
        span_name: The name to use for the span
        
    Returns:
        A span for the API call
    """
    return tracer.start_span(
        span_name,
        kind=SpanKind.CLIENT,
    )


def _handle_response_span(span, start_time, success=True, exception=None):
    """Handle common tasks for a response span.
    
    Args:
        span: The span to handle
        start_time: The start time of the operation
        success: Whether the operation was successful
        exception: Any exception that occurred
    """
    # Set status based on success
    if success:
        span.set_status(Status(StatusCode.OK))
    else:
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))
    
    # Record the duration
    duration = time.time() - start_time
    span.set_attribute("duration_s", duration)


def sync_responses_wrapper(tracer, formatter):
    """Wrapper for synchronous openai.resources.responses.Responses.create API calls.
    
    This wrapper creates a span for tracking OpenAI Responses API calls.
    It uses the provided formatter to extract attributes from the response.
    
    Args:
        tracer: The OpenTelemetry tracer to use for creating spans
        formatter: Function to extract attributes from the response object
        
    Returns:
        A wrapper function that instruments the synchronous OpenAI Responses API
    """
    def wrapper(wrapped, instance, args, kwargs):
        # Skip instrumentation if it's suppressed in the current context
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)
        
        # Start a span for the responses API call
        with tracer.start_as_current_span(
            "openai.responses.create",
            kind=SpanKind.CLIENT,
        ) as span:
            # Record the start time for duration calculation
            start_time = time.time()
            
            # Execute the wrapped function and get the response
            try:
                response = wrapped(*args, **kwargs)
                
                # Use the formatter to extract and set attributes from response
                if response:
                    attributes = formatter(response)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                _handle_response_span(span, start_time, success=True)
            except Exception as e:
                _handle_response_span(span, start_time, success=False, exception=e)
                raise
        
        return response
    
    return wrapper


def async_responses_wrapper(tracer, formatter):
    """Wrapper for asynchronous openai.resources.responses.AsyncResponses.create API calls.
    
    This wrapper creates a span for tracking asynchronous OpenAI Responses API calls.
    It uses the provided formatter to extract attributes from the response.
    
    Args:
        tracer: The OpenTelemetry tracer to use for creating spans
        formatter: Function to extract attributes from the response object
        
    Returns:
        A wrapper function that instruments the asynchronous OpenAI Responses API
    """
    async def wrapper(wrapped, instance, args, kwargs):
        # Skip instrumentation if it's suppressed in the current context
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return await wrapped(*args, **kwargs)
        
        # Start a span for the responses API call
        with tracer.start_as_current_span(
            "openai.responses.create",
            kind=SpanKind.CLIENT,
        ) as span:
            # Record the start time for duration calculation
            start_time = time.time()
            
            # Execute the wrapped function and get the response
            try:
                response = await wrapped(*args, **kwargs)
                
                # Use the formatter to extract and set attributes from response
                if response:
                    attributes = formatter(response)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                        
                _handle_response_span(span, start_time, success=True)
            except Exception as e:
                _handle_response_span(span, start_time, success=False, exception=e)
                raise
        
        return response
    
    return wrapper