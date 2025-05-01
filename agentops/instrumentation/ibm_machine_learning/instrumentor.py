"""IBM Machine Learning Instrumentation for AgentOps

This module provides instrumentation for the IBM Machine Learning API (deprecated), implementing OpenTelemetry
instrumentation for model requests and responses. This instrumentor is for the legacy IBM Machine Learning SDK.
For the new WatsonX AI SDK, use the watsonx_ai instrumentor instead.

We focus on instrumenting the following key endpoints:
- Model.generate - Text generation API
- Model.tokenize - Tokenization API
- Model.get_details - Model details API
"""
from typing import List, Optional, Collection
from opentelemetry.trace import get_tracer, SpanKind
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import get_meter
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.ibm_machine_learning import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.ibm_machine_learning.attributes.attributes import (
    get_generate_attributes,
    get_tokenize_attributes,
    get_model_details_attributes,
    get_generate_text_stream_attributes,
)
from agentops.semconv import (
    SpanAttributes,
    Meters,
    LLMRequestTypeValues,
    CoreAttributes,
    MessageAttributes
)

# Methods to wrap for instrumentation
WRAPPED_METHODS: List[WrapConfig] = [
    # Model-based API methods
    WrapConfig(
        trace_name="ibm_ml.generate",
        package="ibm_watson_machine_learning.foundation_models",
        class_name="Model",
        method_name="generate",
        handler=get_generate_attributes,
    ),
    WrapConfig(
        trace_name="ibm_ml.generate_text_stream",
        package="ibm_watson_machine_learning.foundation_models",
        class_name="Model",
        method_name="generate_text_stream",
        handler=get_generate_text_stream_attributes,
    ),
    WrapConfig(
        trace_name="ibm_ml.tokenize",
        package="ibm_watson_machine_learning.foundation_models",
        class_name="Model",
        method_name="tokenize",
        handler=get_tokenize_attributes,
    ),
    WrapConfig(
        trace_name="ibm_ml.get_details",
        package="ibm_watson_machine_learning.foundation_models",
        class_name="Model",
        method_name="get_details",
        handler=get_model_details_attributes,
    ),
]

class TracedStream:
    """A wrapper for IBM Machine Learning's streaming response that adds telemetry.
    
    This class wraps the original stream to capture metrics about the streaming process,
    including token counts, content, and errors.
    """
    
    def __init__(self, original_stream, span):
        """Initialize with the original stream and span.
        
        Args:
            original_stream: The IBM Machine Learning stream to wrap
            span: The OpenTelemetry span to record metrics on
        """
        self.original_stream = original_stream
        self.span = span
        self.completion_content = ""
        self.input_tokens = 0
        self.output_tokens = 0
        
    def __iter__(self):
        """Iterate through chunks, tracking tokens and content.
        
        Yields:
            Chunks from the original stream
        """
        try:
            for chunk in self.original_stream:
                try:
                    if isinstance(chunk, dict) and 'results' in chunk:
                        for result in chunk['results']:
                            if 'generated_text' in result:
                                self.completion_content += result['generated_text']
                                
                            if 'input_token_count' in result:
                                self.input_tokens = result['input_token_count']
                                
                            if 'generated_token_count' in result:
                                self.output_tokens = result['generated_token_count']
                                
                            # Update span attributes with current token counts
                            self.span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, self.input_tokens)
                            self.span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, self.output_tokens)
                            self.span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, self.input_tokens + self.output_tokens)
                            
                            # Update completion content
                            if self.completion_content:
                                self.span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")
                                self.span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
                                self.span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), self.completion_content)
                except Exception as e:
                    logger.debug(f"Error processing stream chunk: {e}")
                
                yield chunk
        finally:
            # End the span when the stream is exhausted
            if self.span.is_recording():
                self.span.end()

def generate_text_stream_wrapper(wrapped, instance, args, kwargs):
    """Wrapper for the Model.generate_text_stream method.
    
    This wrapper creates spans for tracking stream performance and injects
    a stream wrapper to capture streaming events.
    
    Args:
        wrapped: The original stream method
        instance: The instance the method is bound to
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method
        
    Returns:
        A wrapped stream that captures telemetry data
    """
    tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION)
    span = tracer.start_span(
        "ibm_ml.generate_text_stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.COMPLETION.value},
    )
    
    # Extract prompt and parameters
    prompt = None
    if args and len(args) > 0:
        prompt = args[0]
    elif kwargs and 'prompt' in kwargs:
        prompt = kwargs['prompt']
        
    if prompt:
        span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=0), "user")
        span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=0), prompt)
        span.set_attribute(MessageAttributes.PROMPT_TYPE.format(i=0), "text")
    
    # Extract parameters from args or kwargs
    params = None
    if args and len(args) > 1:
        params = args[1]
    elif kwargs and 'params' in kwargs:
        params = kwargs['params']
        
    if params:
        # Use common attribute extraction
        from agentops.instrumentation.ibm_machine_learning.attributes.common import extract_params_attributes
        span_attributes = extract_params_attributes(params)
        for key, value in span_attributes.items():
            span.set_attribute(key, value)
    
    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)
    
    try:
        stream = wrapped(*args, **kwargs)
        return TracedStream(stream, span)
    except Exception as e:
        span.record_exception(e)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
        span.end()
        raise

class IBMMachineLearningInstrumentor(BaseInstrumentor):
    """An instrumentor for IBM Machine Learning API (deprecated).
    
    This class provides instrumentation for IBM's Machine Learning API by wrapping key methods
    in the client library and capturing telemetry data. It supports both synchronous and
    asynchronous API calls. This is for the legacy IBM Machine Learning SDK - for the new
    WatsonX AI SDK, use the watsonx_ai instrumentor instead.
    
    It captures metrics including token usage, operation duration, and exceptions.
    """
    
    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation.
        
        Returns:
            A collection of package specifications required for this instrumentation.
        """
        return ["ibm-watson-machine-learning"]
    
    def _instrument(self, **kwargs):
        """Instrument the IBM Machine Learning API.
        
        This method wraps key methods in the IBM Machine Learning API to add telemetry.
        It sets up tracing for model operations and token usage tracking.
        """
        # Wrap the generate_text_stream method separately since it needs custom handling
        wrap_function_wrapper(
            "ibm_watson_machine_learning.foundation_models",
            "Model.generate_text_stream",
            generate_text_stream_wrapper
        )
        
        # Wrap other methods using the standard wrapper
        for method in WRAPPED_METHODS:
            if method.method_name != "generate_text_stream":  # Skip since we handled it above
                wrap(method)
                
        logger.debug("Instrumented IBM Machine Learning API")
    
    def _uninstrument(self, **kwargs):
        """Remove instrumentation from the IBM Machine Learning API.
        
        This method removes the telemetry wrappers from the API methods.
        """
        unwrap(
            "ibm_watson_machine_learning.foundation_models",
            "Model.generate_text_stream"
        )
        
        for method in WRAPPED_METHODS:
            if method.method_name != "generate_text_stream":
                unwrap(
                    method.package,
                    f"{method.class_name}.{method.method_name}"
                )
                
        logger.debug("Uninstrumented IBM Machine Learning API") 