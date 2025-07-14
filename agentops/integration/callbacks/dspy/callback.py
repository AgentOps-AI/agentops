from typing import Any, Dict, List, Optional, Union

from agents.agent import Agent
from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.trace import Span, SpanContext, set_span_in_context

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger
from agentops.sdk.core import tracer
from agentops.semconv import AgentOpsSpanKindValues, SpanAttributes, CoreAttributes, agent
from agentops.integration.callbacks.langchain.utils import get_model_info

from dspy.utils.callback import BaseCallback
import dspy

# adding inputs as a dict, align with semconv?
# grabbing attributes so annoying

# farm everything from dspy.module
# instance: Module

# check dwij thing for how to test/debug the callbacks for langchain/dspy
# no kwargs except WITHIN input dict from dspy

class DSPyCallbackHandler(BaseCallback):
    """
    AgentOps callback handler for DSPy.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        auto_session: bool = True,
    ):
        self.active_spans = {}
        self.api_key = api_key
        self.tags = tags or []
        self.trace = None # 'trace' replaces 'session'
        self.trace_token = None
        self.context_tokens = {}
        self.token_counts = {}

        self.active_spans.pop("test").add_event

        if auto_session:
            self._initialize_agentops()

    # not entirely sure if this works
    def _initialize_agentops(self):
        """Initialize AgentOps"""
        import agentops

        if not tracer.initialized:
            init_kwargs = {
                "auto_start_session": False,
                "instrument_llm_calls": True,
                "api_key": Optional[str] # ? fix
            }

            if self.api_key:
                init_kwargs["api_key"] = self.api_key

            agentops.init(**init_kwargs)
            logger.debug("AgentOps initialized from DSPy callback handler")

        if not tracer.initialized:
            logger.warning("AgentOps not initialized, session span will not be created")
            return

        otel_tracer = tracer.get_tracer()

        span_name = f"session.{AgentOpsSpanKindValues.SESSION.value}"

        attributes = {
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.SESSION.value,
            "session.tags": self.tags,
            "agentops.operation.name": "session",
            "span.kind": AgentOpsSpanKindValues.SESSION.value,
        }

        # Create a root session span
        self.trace = otel_tracer.start_span(span_name, attributes=attributes)

        # Attach session span to current context
        self.trace_token = attach(set_span_in_context(self.trace))

        logger.debug("Created trace as root span for DSPy")

    # def utility for determining module/etc type and mapping it to agentops semconv equivalent
    def _create_span(
        self,
        operation_name: str,
        span_kind: str,
        run_id: Any = None,
        attributes: dict[str, Any] | None = None,
        parent_run_id: str | None = None, # any to str
        inputs: dict[str, Any] | None = None,
    ):
        if not tracer.initialized:
            logger.warning("AgentOps not initialized, spans will not be created")
            return trace.NonRecordingSpan(SpanContext.INVALID) # type: ignore # doesn't exist in otel??

        otel_tracer = tracer.get_tracer()

        span_name = f"{operation_name}.{span_kind}"

        if attributes is None:
            attributes = {}

        if inputs is None:
            inputs = {}

        attributes = {**attributes, **inputs} # combine inputs and attributes
        attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = span_kind
        attributes["agentops.operation.name"] = operation_name # make a span attribute in semconv?

        if run_id is None:
            run_id = id(attributes) # not sure if this applies to call_id or is the fallback?

        parent_span = None
        if parent_run_id is not None and parent_run_id is self.active_spans:
            # Get parent span from active spans
            parent_span = self.active_spans[parent_run_id]
            # Create context with parent span
            parent_ctx = set_span_in_context(parent_span)
            # Start span with parent context
            span = otel_tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
            logger.debug(f"Start span: {span_name} with parent: {parent_run_id}")
        else:
            parent_ctx = set_span_in_context(self.trace) # assign span earlier, should be fine, ensure types # type: ignore
            span = otel_tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
            logger.debug(f"Started span: {span_name} with session as parent")

            # Check what is available/needed and abstract out to utillities?
            # Think it is callback/framework/etc specific since they surface different data

        # Store span in active_spans
        self.active_spans[run_id] = span

        # Store token to detach later
        token = attach(set_span_in_context(span))
        self.context_tokens[run_id] = token

        return span

    def _end_span(self, run_id: Any):
        if run_id not in self.active_spans:
            logger.warning(f"No span found for call {run_id}")
            return

        span = self.active_spans.pop(run_id)
        token = self.context_tokens.pop(run_id, None)

        if token is not None:
            detach(token)

        try:
            span.end()
            logger.debug(f"Ended span: {span.name}")
        except Exception as e:
            logger.warning(f"Error ending span: {e}")

        # Clean up token counts if present
        if run_id in self.token_counts:
            del self.token_counts[run_id]

    # modules, adapters, evaluate, tool, lm
    # what are adapters?

    def _get_span_kind(self, instance: dspy.Module) -> str:
        if isinstance(instance, (dspy.ReAct, dspy.ProgramOfThought)):
            return AgentOpsSpanKindValues.AGENT.value
        elif isinstance(instance, (
            dspy.ChainOfThought,
            dspy.MultiChainComparison,
            dspy.BestOfN,
            dspy.Refine
        )):
            return AgentOpsSpanKindValues.WORKFLOW.value
        elif isinstance(instance, dspy.Predict):
            return AgentOpsSpanKindValues.CHAIN.value
        else:
            logger.warning(f"Instance's span type not found: {instance}")
            return AgentOpsSpanKindValues.UNKNOWN.value

    def _get_span_attributes(self, instance: dspy.Module) -> dict: # add self
        attributes = {}
        attributes = {**attributes, **instance.__dict__} # append dict, should probably delete some, organize/name
        return attributes

    def on_module_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """A handler triggered when forward() method of a module (subclass of dspy.Module) is called.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            instance: The Module instance.
            inputs: The inputs to the module's forward() method. Each arguments is stored as
                a key-value pair in a dictionary.
        """

        span_kind = self._get_span_kind(instance) # make it check for various types
        span_attributes = self._get_span_attributes(instance)

        # unpack instance for more data
        # how does mlflow deal with parent? implementaiton is brief
            # deals with parent as current active span which is also how we do it here

        # if isinstance(instance, dspy.Module):
        #     instance.__class__.__name__

        self._create_span(
            operation_name=f"{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes
        )

    def on_module_end(
        self,
        call_id: str,
        outputs: Any | None,
        exception: Exception | None = None,
    ):
        """A handler triggered after forward() method of a module (subclass of dspy.Module) is executed.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the module's forward() method. If the method is interrupted by
                an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """

        # build in some way to add on end span, either modify the function
        # OR add here, depending on whether it is applicable in other
        # callback functions
        self._end_span(call_id)

    def on_lm_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """A handler triggered when __call__ method of dspy.LM instance is called.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            instance: The LM instance.
            inputs: The inputs to the LM's __call__ method. Each arguments is stored as
                a key-value pair in a dictionary.
        """
        # use import types to exhaust all the data we can find
        # take notes on it, probably gets quite messy
        span_kind = self._get_span_kind(instance)
        span_attributes = self._get_span_attributes(instance)

        self._create_span(
            operation_name=f"{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes
        )

    def on_lm_end(
        self,
        call_id: str,
        outputs: Dict[str, Any] | None,
        exception: Exception | None = None,
    ):
        """A handler triggered after __call__ method of dspy.LM instance is executed.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the LM's __call__ method. If the method is interrupted by
                an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """
        self._end_span(call_id)

    def on_adapter_format_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """A handler triggered when format() method of an adapter (subclass of dspy.Adapter) is called.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            instance: The Adapter instance.
            inputs: The inputs to the Adapter's format() method. Each arguments is stored as
                a key-value pair in a dictionary.
        """
        span_kind = "lm_call"
        span_attributes = {"lm_instance": instance.__class__.__name__}

        self._create_span(
            operation_name=f"lm_call_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes
        )

    def on_adapter_format_end(
        self,
        call_id: str,
        outputs: Dict[str, Any] | None,
        exception: Exception | None = None,
    ):
        """A handler triggered after format() method of an adapter (subclass of dspy.Adapter) is called..

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the Adapter's format() method. If the method is interrupted
                by an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """
        self._end_span(call_id)

    def on_adapter_parse_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """A handler triggered when parse() method of an adapter (subclass of dspy.Adapter) is called.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            instance: The Adapter instance.
            inputs: The inputs to the Adapter's parse() method. Each arguments is stored as
                a key-value pair in a dictionary.
        """
        span_kind = "adapter_format"
        span_attributes = {"adapter": instance.__class__.__name__}

        self._create_span(
            operation_name=f"adapter_format_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes
        )

    def on_adapter_parse_end(
        self,
        call_id: str,
        outputs: Dict[str, Any] | None,
        exception: Exception | None = None,
    ):
        """A handler triggered after parse() method of an adapter (subclass of dspy.Adapter) is called.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the Adapter's parse() method. If the method is interrupted
                by an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """
        self._end_span(call_id)

    def on_tool_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """A handler triggered when a tool is called.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            instance: The Tool instance.
            inputs: The inputs to the Tool's __call__ method. Each arguments is stored as
                a key-value pair in a dictionary.
        """
        span_kind = "adapter_parse"
        span_attributes = {"adapter": instance.__class__.__name__}

        self._create_span(
            operation_name=f"adapter_parse_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes
        )

    def on_tool_end(
        self,
        call_id: str,
        outputs: Dict[str, Any] | None,
        exception: Exception | None = None,
    ):
        """A handler triggered after a tool is executed.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the Tool's __call__ method. If the method is interrupted by
                an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """
        self._end_span(call_id)

    def on_evaluate_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """A handler triggered when evaluation is started.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            instance: The Evaluate instance.
            inputs: The inputs to the Evaluate's __call__ method. Each arguments is stored as
                a key-value pair in a dictionary.
        """
        span_kind = "tool_call"
        span_attributes = {"tool": instance.__class__.__name__}

        self._create_span(
            operation_name=f"tool_call_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes
        )

    def on_evaluate_end(
        self,
        call_id: str,
        outputs: Any | None,
        exception: Exception | None = None,
    ):
        """A handler triggered after evaluation is executed.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the Evaluate's __call__ method. If the method is interrupted by
                an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """
        self._end_span(call_id)
