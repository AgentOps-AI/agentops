from typing import Any, Dict, List, Optional

from opentelemetry import attributes
from opentelemetry.context import attach, detach
from opentelemetry.trace import SpanContext, set_span_in_context
from opentelemetry.sdk.trace import Span as SDKSpan

from agentops.logging import logger
from agentops.sdk.core import tracer
from agentops.semconv import AgentOpsSpanKindValues, SpanAttributes

from dspy.utils.callback import BaseCallback
import dspy

# compile todo!
#
# fix terminal logs (unable to load logs)
# fix api/mcp (request failed, 404)
# semconv ... 🤢
# try/except
# caching
# farm attributes 🧑‍🌾

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
        self.active_spans: Dict[str, SDKSpan] = {}
        self.api_key = api_key
        self.tags = tags or []
        self.session_span = None
        self.session_token = None
        self.context_tokens = {}
        self.token_counts = {}

        if auto_session:
            self._initialize_agentops()

    # not entirely sure if this works
    def _initialize_agentops(self):
        """Initialize AgentOps"""
        # enable cache, figure out how to denoted cached operations
        # or figure out how to find cache data -> attach to session
        dspy.configure_cache(
            enable_disk_cache=False,
            enable_memory_cache=False,
        )

        import agentops

        if not tracer.initialized:
            init_kwargs = {
                "auto_start_session": False,
                "instrument_llm_calls": True,
                "api_key": Optional[str]
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
        self.session_span = otel_tracer.start_span(span_name, attributes=attributes)

        # Attach session span to current context
        self.session_token = attach(set_span_in_context(self.session_span))

        logger.debug("Created trace as root span for DSPy")

    # def utility for determining module/etc type and mapping it to agentops semconv equivalent
    def _create_span(
        self,
        operation_name: str,
        span_kind: str,
        run_id: Any = None,
        attributes: dict[str, Any] | None = None,
        parent_run_id: str | None = None,
        inputs: dict[str, Any] | None = None,
    ):
        """
        Create a span for the operation.

        Args:
            operation_name: Name of the operation
            span_kind: Type of span
            run_id: Unique identifier for the operation
            attributes: Additional attributes for the span
            parent_run_id: The run_id of the parent span if this is a child span
            inputs: The DSPy input dictionary

        Returns:
            The created span
        """
        if not tracer.initialized:
            logger.warning("AgentOps not initialized, spans will not be created")
            return trace.NonRecordingSpan(SpanContext.INVALID)  # type: ignore

        otel_tracer = tracer.get_tracer()

        span_name = f"{operation_name}.{span_kind}"

        if attributes is None:
            logger.warning("no attributes")
            attributes = {}

        if inputs is None:
            logger.warning("no inputs")
            inputs = {}

        inputs = {f"inputs.{key}": value for key, value in inputs.items()}

        # only these explicit attributes (kind and name) are being recorded
        attributes = {**attributes, **inputs}
        attributes["agentops.span.kind"] = span_kind # avoid deprecated semconv
        attributes["agentops.operation.name"] = operation_name
        logger.warning(f"Attributes: {attributes}")

        if run_id is None:
            run_id = id(attributes)

        # parent_span = None
        if parent_run_id is not None and parent_run_id is self.active_spans:
            # Get parent span from active spans
            parent_span = self.active_spans[parent_run_id]
            # Create context with parent span
            parent_ctx = set_span_in_context(parent_span)
            # Start span with parent context
            span = otel_tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
            logger.debug(f"Start span: {span_name} with parent: {parent_run_id}")
        else:
            if not self.session_span:
                logger.warning(f"Root session span not set. Starting {span_name} as root span.")
                self.session_span = otel_tracer.start_span(span_name, attributes=attributes)
            parent_ctx = set_span_in_context(self.session_span)
            # Start span with session as parent context
            span = otel_tracer.start_span(span_name, context=parent_ctx, attributes=attributes)
            logger.debug(f"Started span: {span_name} with session as parent")

        if isinstance(span, SDKSpan):
            self.active_spans[run_id] = span
        else:
            logger.warning(f"Span type warning: generated {type(span)}")

        # Store token to detach later
        token = attach(set_span_in_context(span))
        self.context_tokens[run_id] = token

        return span

    def _end_span(
        self,
        run_id: str,
        outputs: Any | None,
        exception: Exception | None = None,
    ):
        """
        End the span associated with the run_id.

        Args:
            run_id: Unique identifier for the operation
            outputs: The DSPy output
            exception: The DSPy exception
        """
        # deal with exceptions
        # deal with outputs, span attributes <- output
        if run_id not in self.active_spans:
            logger.warning(f"No span found for call {run_id}")
            return

        span: SDKSpan = self.active_spans.pop(run_id)
        token = self.context_tokens.pop(run_id, None)


        if exception:
            logger.warning(f"Exception {str(exception)}")
            span.add_event(
                name="exception",
                attributes={
                    "exception.type": exception.__class__.__name__,
                    "exception.message": str(exception)
                },
            )

        attributes = {}
        if span.attributes:
            attributes = {key: value for key, value in span.attributes.items()}

        if isinstance(outputs, Dict):
            attributes = {**attributes, **outputs}
            span.set_attributes(attributes)

        if token is not None:
            detach(token)

        try:
            span.end()
            logger.debug(f"Ended span: {span.update_name('test')}") # ugh
        except Exception as e:
            logger.warning(f"Error ending span: {e}")

        # Clean up token counts if present
        if run_id in self.token_counts:
            del self.token_counts[run_id]

    # modules, adapters, evaluate, tool, lm

    # maybe a better way to do this?
    # includes:
        #   multiple inheritance in python?
        # BestOfN, ChainOfThought, ChainOfThoughtWithHint
        # MultiChainComparison, Predict
        # ProgramOfThought, ReAct, Refine, SmartSearch
        # RulesInductionProgram
    # modules also include teleprompt (non lm ... what)
    def _get_span_kind(self, instance: dspy.Module) -> str:
        if isinstance(instance, (dspy.ReAct, dspy.ProgramOfThought)):
            return AgentOpsSpanKindValues.AGENT.value
        elif isinstance(instance, (dspy.ChainOfThought, dspy.MultiChainComparison, dspy.BestOfN, dspy.Refine)):
            return AgentOpsSpanKindValues.WORKFLOW.value
        elif isinstance(instance, dspy.Predict):
            return AgentOpsSpanKindValues.CHAIN.value
        elif isinstance(instance, dspy.LM):
            return AgentOpsSpanKindValues.LLM.value
        else:
            logger.warning(f"Instance's span type not found: {instance}")
            return AgentOpsSpanKindValues.UNKNOWN.value

    # might have to make it on a per-class basis
    # this sucks cuz it only unpacks lm basically
    def _get_span_attributes(self, instance: Any) -> dict:
        attributes = {}
        attributes = {**attributes, **instance.__dict__}  # append dict, should probably delete some, organize/name
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
        span_kind = self._get_span_kind(instance)  # make it check for various types
        span_attributes = self._get_span_attributes(instance)

        logger.warning(f"module start, {instance.__class__.__name__}, {instance}, {inputs}") # delete

        # avoid recording empty "args" key
        if "args" in inputs and not inputs["args"]:
            inputs.pop("args")

        self._create_span(
            operation_name=f"{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes,
        )

    def on_module_end(
        self,
        call_id: str,
        outputs: Any | None,
        exception: Exception | None = None,
    ):
        # not collecting?
        # why was it collecting on the other one?
        """A handler triggered after forward() method of a module (subclass of dspy.Module) is executed.

        Args:
            call_id: A unique identifier for the call. Can be used to connect start/end handlers.
            outputs: The outputs of the module's forward() method. If the method is interrupted by
                an exception, this will be None.
            exception: If an exception is raised during the execution, it will be stored here.
        """
        if isinstance(outputs, dspy.Prediction):
            outputs = outputs.toDict()

        self._end_span(call_id, outputs, exception)

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
        _instance: dspy.LM = instance
        _instance.cache # (cache_in_memory is deprecated)
        _instance.model # might be redundant
        _instance.provider # def redundant?
        _instance.finetuning_model

        p_instance: dspy.Predict = instance
        dspy.ReAct

        # duck type to collect?

        span_kind = self._get_span_kind(instance)
        span_attributes = self._get_span_attributes(instance)

        logger.warning(f"lm start, {instance.__class__.__name__}, {instance}, {inputs}")

        attributes = {
            **instance.kwargs,
        }

        self._create_span(
            operation_name=f"{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes,
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
        logger.warning("ending")
        self._end_span(call_id, outputs, exception)

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
        span_kind = AgentOpsSpanKindValues.OPERATION.value # custom semconv?
        span_attributes = {"lm_instance": instance.__class__.__name__}
        # semconv for parser

        logger.warning(f"adapter format start, {instance.__class__.__name__}, {instance}, {inputs}")

        self._create_span(
            operation_name=f"lm_call_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes,
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
        self._end_span(call_id, outputs, exception)

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
        span_kind = "adapter_parse"
        span_attributes = {"adapter": instance.__class__.__name__}

        logger.warning(f"adapter parser start, {instance.__class__.__name__}, {instance}, {inputs}")

        self._create_span(
            operation_name=f"adapter_parser_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes,
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
        self._end_span(call_id, outputs, exception)

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
        span_kind = "tool"
        span_attributes = {"tool": instance.__class__.__name__}

        logger.warning(f"tool start, {instance.__class__.__name__}, {instance}, {inputs}")

        self._create_span(
            operation_name=f"tool_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes,
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
        self._end_span(call_id, outputs, exception)

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
        span_kind = "evalute"
        span_attributes = {"evalute": instance.__class__.__name__}

        _instance: dspy.Evaluate = instance

        self._create_span(
            operation_name=f"evaluate_{instance.__class__.__name__}",
            span_kind=span_kind,
            run_id=call_id,
            inputs=inputs,
            attributes=span_attributes,
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
        self._end_span(call_id, outputs, exception)
