import logging
import time
from opentelemetry import context as context_api
from opentelemetry.context import attach, set_value
from opentelemetry.instrumentation.utils import (
    _SUPPRESS_INSTRUMENTATION_KEY,
)
from opentelemetry.instrumentation.haystack.utils import (
    with_tracer_wrapper,
    process_request,
    process_response,
)
from opentelemetry.instrumentation.haystack.config import Config
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues

logger = logging.getLogger(__name__)


@with_tracer_wrapper
def wrap(tracer, to_wrap, wrapped, instance, args, kwargs):
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)
    
    name = "haystack_pipeline"
    pipeline_name = getattr(instance, "name", name)
    start_time = time.time()
    
    attach(set_value("workflow_name", name))
    with tracer.start_as_current_span(f"{name}.workflow") as span:
        span.set_attribute(
            SpanAttributes.AGENTOPS_SPAN_KIND,
            AgentOpsSpanKindValues.WORKFLOW.value,
        )
        span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_NAME, pipeline_name)
        process_request(span, args, kwargs)
        
        try:
            response = wrapped(*args, **kwargs)
            process_response(span, response)
            
            # Record pipeline duration
            if Config.pipeline_duration_histogram:
                duration = (time.time() - start_time) * 1000  # Convert to ms
                Config.pipeline_duration_histogram.record(
                    duration,
                    {
                        "pipeline_name": pipeline_name,
                    }
                )
                
            return response
        except Exception as e:
            span.record_exception(e)
            raise
