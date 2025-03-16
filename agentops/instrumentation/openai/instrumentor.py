"""OpenAI Responses Instrumentor for AgentOps

This module provides instrumentation for the OpenAI API, with specialized handling for 
both traditional Chat Completions API and the newer Response API format. It ensures proper
extraction and normalization of telemetry data regardless of the API format used.

IMPORTANT DISTINCTION BETWEEN OPENAI API FORMATS:
1. OpenAI Completions API - The traditional API format using prompt_tokens/completion_tokens
2. OpenAI Response API - The newer format used by the Agents SDK using input_tokens/output_tokens

The instrumentor handles both formats through shared utilities in the responses module,
providing consistent span attributes according to OpenTelemetry semantic conventions.
"""
import functools
import time
from typing import Any, Collection, Dict, Optional

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode

from agentops.semconv import (
    CoreAttributes,
    SpanAttributes,
    InstrumentationAttributes,
)
from agentops.logging import logger

# Import response extraction utilities
from agentops.instrumentation.openai.responses.extractors import extract_from_response


class OpenAIResponsesInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI API responses that handles both API formats.
    
    This instrumentor patches OpenAI API response handling to extract telemetry data
    from both traditional Chat Completions API and the newer Response API format.
    """
    
    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["openai >= 0.27.0"]
    
    def _instrument(self, **kwargs):
        """Instrument the OpenAI API."""
        tracer_provider = kwargs.get("tracer_provider")
        
        try:
            import openai
            import openai.version
            
            openai_version = getattr(openai, "__version__", "unknown")
            logger.debug(f"OpenAI detected, version: {openai_version}")
            
            # For OpenAI v1+ (modern API)
            # For modern Response API, check both the OpenAI client and direct access
            # The client.responses.create() is the main path we want to instrument
            try:
                self._patch_modern_response(openai, tracer_provider)
                logger.debug("Patched OpenAI v1+ Response API")
            except Exception as e:
                logger.warning(f"Failed to patch OpenAI Response API: {e}")
            
            # For legacy Chat Completions API
            try:
                self._patch_legacy_response(openai, tracer_provider)
                logger.debug("Patched OpenAI Legacy Response API")
            except Exception as e:
                logger.warning(f"Failed to patch OpenAI Legacy Response API: {e}")
            
            logger.debug("Successfully instrumented OpenAI responses")
            
        except ImportError as e:
            logger.debug(f"Failed to import OpenAI: {e}")
        except Exception as e:
            logger.warning(f"Failed to instrument OpenAI responses: {e}")
    
    def _patch_modern_response(self, openai_module, tracer_provider):
        """Patch OpenAI v1+ Response class."""
        # First try to patch the client's responses.create method
        try:
            from openai import OpenAI
            client = OpenAI.__new__(OpenAI)
            if hasattr(client, "responses") and hasattr(client.responses, "create"):
                logger.debug("Found responses.create in OpenAI client")
        except Exception as e:
            logger.debug(f"Could not find responses.create in OpenAI client: {e}")
            
        # Then try to patch the Response class
        try:
            # Import directly from the module path
            from openai.resources.responses.__init__ import Response
        except ImportError:
            try:
                # Try alternate path
                from openai.resources.responses import Response
            except ImportError:
                try:
                    # Fallback for older OpenAI versions
                    from openai._response import APIResponse as Response
                except ImportError:
                    logger.warning("Could not import Response class from OpenAI module")
                    return
        
        # Store the original method
        original_parse = Response.parse
        
        # Define wrapped method with the same signature as the original
        @functools.wraps(original_parse)
        def instrumented_parse(*args, **kwargs):
            # Call original parse method with the same arguments
            result = original_parse(*args, **kwargs)
            
            try:
                # Create tracer
                tracer = get_tracer(
                    "agentops.instrumentation.openai",
                    instrumenting_library_version="0.1.0",
                    tracer_provider=tracer_provider
                )
                
                # Get current context to maintain context propagation
                from opentelemetry import context as context_api
                from opentelemetry.trace import INVALID_SPAN, SpanContext, get_current_span
                from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
                
                # Get the current active span to maintain parent-child relationship
                current_span = get_current_span()
                current_context = context_api.get_current()
                
                # Start a span for the response, linked to current trace context
                with tracer.start_as_current_span(
                    name="openai.response",
                    context=current_context,
                    kind=SpanKind.CLIENT,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "openai",
                        InstrumentationAttributes.NAME: "agentops.instrumentation.openai",
                        InstrumentationAttributes.VERSION: "0.1.0",
                    }
                ) as span:
                    # Link to parent span if one exists
                    if current_span != INVALID_SPAN:
                        span.set_attribute(CoreAttributes.PARENT_ID, current_span.get_span_context().span_id)
                    # Extract response as dictionary
                    if hasattr(result, "model_dump"):
                        # Pydantic v2+
                        response_dict = result.model_dump()
                    elif hasattr(result, "dict"):
                        # Pydantic v1
                        response_dict = result.dict()
                    else:
                        # Fallback to direct attribute access
                        response_dict = {
                            attr: getattr(result, attr)
                            for attr in dir(result)
                            if not attr.startswith("_") and not callable(getattr(result, attr))
                        }
                    
                    # Extract attributes from response
                    attributes = extract_from_response(response_dict)
                    
                    # Set attributes on span
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
            
            except Exception as e:
                logger.warning(f"Error in instrumented_parse: {e}")
            
            return result
        
        # Apply the patch
        Response.parse = instrumented_parse
    
    def _patch_legacy_response(self, openai_module, tracer_provider):
        """Patch OpenAI legacy response class."""
        try:
            # Try importing directly from the chat completions module
            from openai.resources.chat.completions.__init__ import ChatCompletion as LegacyAPIResponse
        except ImportError:
            try:
                # Try alternate path
                from openai.resources.chat.completions import ChatCompletion as LegacyAPIResponse
            except ImportError:
                try:
                    # Fallback for older OpenAI versions
                    from openai._legacy_response import LegacyAPIResponse
                except ImportError:
                    logger.warning("Could not import LegacyAPIResponse class from OpenAI module")
                    return
        
        # Store the original method
        original_parse = LegacyAPIResponse.parse
        
        # Define wrapped method with the same signature as the original
        @functools.wraps(original_parse)
        def instrumented_parse(*args, **kwargs):
            # Call original parse method with the same arguments
            result = original_parse(*args, **kwargs)
            
            try:
                # Create tracer
                tracer = get_tracer(
                    "agentops.instrumentation.openai",
                    instrumenting_library_version="0.1.0",
                    tracer_provider=tracer_provider
                )
                
                # Get current context to maintain context propagation
                from opentelemetry import context as context_api
                from opentelemetry.trace import INVALID_SPAN, SpanContext, get_current_span
                from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
                
                # Get the current active span to maintain parent-child relationship
                current_span = get_current_span()
                current_context = context_api.get_current()
                
                # Start a span for the response, linked to current trace context
                with tracer.start_as_current_span(
                    name="openai.legacy_response.parse",
                    context=current_context,
                    kind=SpanKind.CLIENT,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "openai",
                        InstrumentationAttributes.NAME: "agentops.instrumentation.openai",
                        InstrumentationAttributes.VERSION: "0.1.0",
                    }
                ) as span:
                    # Link to parent span if one exists
                    if current_span != INVALID_SPAN:
                        span.set_attribute(CoreAttributes.PARENT_ID, current_span.get_span_context().span_id)
                    # Extract response as dictionary
                    if hasattr(result, "model_dump"):
                        # Pydantic v2+
                        response_dict = result.model_dump()
                    elif hasattr(result, "dict"):
                        # Pydantic v1
                        response_dict = result.dict()
                    else:
                        # Fallback to direct attribute access
                        response_dict = {
                            attr: getattr(result, attr)
                            for attr in dir(result)
                            if not attr.startswith("_") and not callable(getattr(result, attr))
                        }
                    
                    # Extract attributes from response
                    attributes = extract_from_response(response_dict)
                    
                    # Set attributes on span
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
            
            except Exception as e:
                logger.warning(f"Error in instrumented_parse: {e}")
            
            return result
        
        # Apply the patch
        LegacyAPIResponse.parse = classmethod(instrumented_parse)
    
    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API."""
        try:
            import openai
            
            # Restore original parse methods if we've saved them
            if hasattr(openai, "_response"):
                # We would need to restore the original method here
                # For a production implementation, we would need to save the original methods
                # in class variables and restore them here
                pass
            
            if hasattr(openai, "_legacy_response"):
                # Same as above for legacy response
                pass
            
            logger.debug("Uninstrumented OpenAI responses")
        except Exception as e:
            logger.warning(f"Failed to uninstrument OpenAI responses: {e}")