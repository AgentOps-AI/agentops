"""OpenAI Agents SDK Instrumentation for AgentOps

This module provides instrumentation for the OpenAI Agents SDK, leveraging its built-in
tracing API for observability. It captures detailed information about agent execution,
tool usage, LLM requests, and token metrics.

The implementation uses a clean separation between exporters and processors. The exporter
translates Agent spans into OpenTelemetry spans with appropriate semantic conventions.
The processor implements the tracing interface, collects metrics, and manages timing data.

We use the built-in add_trace_processor hook for all functionality. Streaming support
would require monkey-patching the run method of `Runner`, but doesn't really get us
more data than we already have, since the `Response` object is always passed to us
from the `agents.tracing` module.

TODO Calls to the OpenAI API are not available in this tracing context, so we may
need to monkey-patch the `openai` from here to get that data. While we do have
separate instrumentation for the OpenAI API, in order to get it to nest with the
spans we create here, it's probably easier (or even required) that we incorporate
that here as well.
"""

from typing import Collection, Tuple, Dict, Any, Optional
import functools  # For functools.wraps

from opentelemetry import trace  # Needed for tracer
from opentelemetry.trace import SpanKind as OtelSpanKind, Status, StatusCode  # Renamed to avoid conflict
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore
import wrapt  # For wrapping
# Remove local contextvars import, will import from .context
# import contextvars

from agentops.logging import logger
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter
from .context import full_prompt_contextvar  # Import from .context
from agentops.instrumentation.common.wrappers import WrapConfig  # Keep WrapConfig

# Remove wrap, unwrap from common.wrappers as we'll use wrapt directly for custom wrapper
# from agentops.instrumentation.common.wrappers import wrap, unwrap
from agentops.instrumentation.common.attributes import AttributeMap  # For type hinting
from agentops.helpers import safe_serialize

# Semantic conventions from AgentOps (Copied from runner_wrappers.py for use in new handler logic)
from agentops.semconv import (
    AgentAttributes,
    MessageAttributes,
    SpanAttributes,
    CoreAttributes,
    AgentOpsSpanKindValues,
    WorkflowAttributes,
)

# Removed local definition of full_prompt_contextvar

# Define AGENT_RUNNER_WRAP_CONFIGS locally (adapted from runner_wrappers.py)
# Handler field is removed as the new wrapper incorporates this logic.
_OPENAI_AGENTS_RUNNER_MODULE = "agents.run"
_OPENAI_AGENTS_RUNNER_CLASS = "Runner"

AGENT_RUNNER_WRAP_CONFIGS = [
    WrapConfig(
        trace_name=AgentOpsSpanKindValues.AGENT.value,  # This will be the OTel span name
        package=_OPENAI_AGENTS_RUNNER_MODULE,
        class_name=_OPENAI_AGENTS_RUNNER_CLASS,
        method_name="run",
        handler=None,
        is_async=True,
        span_kind=OtelSpanKind.INTERNAL,
    ),
    WrapConfig(
        trace_name=AgentOpsSpanKindValues.AGENT.value,
        package=_OPENAI_AGENTS_RUNNER_MODULE,
        class_name=_OPENAI_AGENTS_RUNNER_CLASS,
        method_name="run_sync",
        handler=None,
        is_async=False,
        span_kind=OtelSpanKind.INTERNAL,
    ),
    WrapConfig(
        trace_name=AgentOpsSpanKindValues.AGENT.value,
        package=_OPENAI_AGENTS_RUNNER_MODULE,
        class_name=_OPENAI_AGENTS_RUNNER_CLASS,
        method_name="run_streamed",
        handler=None,
        is_async=True,
        span_kind=OtelSpanKind.INTERNAL,
    ),
]


class OpenAIAgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI Agents SDK that primarily uses the built-in tracing API."""

    _processor = None
    _exporter = None
    _default_processor = None
    # _is_instrumented_flag_for_instance = {} # Using instance member instead

    def __init__(self):  # OTel BaseInstrumentor __init__ takes no args
        super().__init__()
        self._tracer = None  # Ensure _tracer is initialized
        self._is_instrumented_instance_flag = False  # Instance-specific flag
        logger.debug(
            f"OpenAIAgentsInstrumentor (id: {id(self)}) created. Initial _is_instrumented_instance_flag: {self._is_instrumented_instance_flag}"
        )

    # Removed property for _is_instrumented, will use direct instance member _is_instrumented_instance_flag

    def _extract_agent_runner_attributes_and_set_contextvar(
        self,
        otel_span: trace.Span,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        return_value: Optional[Any] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """
        Helper to extract attributes for an 'Agent Run/Turn' span and manage contextvar.
        Logic is derived from the original agent_run_turn_attribute_handler.
        Sets attributes directly on the provided otel_span.
        """
        attributes: AttributeMap = {}
        attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKindValues.AGENT.value
        otel_span_id_for_log = "unknown"
        if otel_span and hasattr(otel_span, "get_span_context"):
            span_ctx = otel_span.get_span_context()
            if span_ctx and hasattr(span_ctx, "span_id"):
                otel_span_id_for_log = f"{span_ctx.span_id:016x}"
        logger.debug(
            f"[_extract_agent_runner_attributes_and_set_contextvar] Set AGENTOPS_SPAN_KIND to '{AgentOpsSpanKindValues.AGENT.value}' for OTel span ID: {otel_span_id_for_log}"
        )

        agent_obj: Any = None
        sdk_input: Any = None

        # The `args` passed to this function are the direct *args of the wrapped method (e.g., Runner.run),
        # so args[0] is 'agent', args[1] is 'input'.
        # `kwargs` are the direct **kwargs of the wrapped method.
        if args:
            if len(args) > 0:
                agent_obj = args[0]
            if len(args) > 1:
                sdk_input = args[1]

        # Allow kwargs to override or provide if not in args
        if kwargs:
            if "agent" in kwargs and kwargs["agent"] is not None:  # Check for None explicitly
                agent_obj = kwargs["agent"]
            if "input" in kwargs and kwargs["input"] is not None:  # Check for None explicitly
                sdk_input = kwargs["input"]

        current_full_prompt_for_llm = []

        if agent_obj:
            if hasattr(agent_obj, "name") and agent_obj.name:
                attributes[AgentAttributes.AGENT_NAME] = str(agent_obj.name)
            if hasattr(agent_obj, "model") and agent_obj.model:
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = str(agent_obj.model)
            if hasattr(agent_obj, "instructions") and agent_obj.instructions:
                instructions = str(agent_obj.instructions)
                attributes[SpanAttributes.LLM_REQUEST_INSTRUCTIONS] = instructions
                current_full_prompt_for_llm.append({"role": "system", "content": instructions})
            if hasattr(agent_obj, "tools") and agent_obj.tools:
                attributes[AgentAttributes.AGENT_TOOLS] = [str(getattr(t, "name", t)) for t in agent_obj.tools]
            if hasattr(agent_obj, "handoffs") and agent_obj.handoffs:
                attributes[AgentAttributes.HANDOFFS] = [str(getattr(h, "name", h)) for h in agent_obj.handoffs]
            if hasattr(agent_obj, "output_type") and agent_obj.output_type:
                attributes["gen_ai.output.type"] = str(agent_obj.output_type)

        if sdk_input:
            if isinstance(sdk_input, str):
                attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = sdk_input
                attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
                current_full_prompt_for_llm.append({"role": "user", "content": sdk_input})
            elif isinstance(sdk_input, list):
                for i, msg in enumerate(sdk_input):
                    if isinstance(msg, dict):
                        role = msg.get("role")
                        content = msg.get("content")
                        if role:
                            attributes[MessageAttributes.PROMPT_ROLE.format(i=i)] = str(role)
                        if content is not None:  # Allow empty string for content
                            serialized_content = safe_serialize(content)
                            attributes[MessageAttributes.PROMPT_CONTENT.format(i=i)] = serialized_content
                            if role:  # Add to full_prompt only if role and content exist
                                current_full_prompt_for_llm.append({"role": str(role), "content": serialized_content})
            else:
                attributes[WorkflowAttributes.WORKFLOW_INPUT] = safe_serialize(sdk_input)

        if current_full_prompt_for_llm:
            full_prompt_contextvar.set(current_full_prompt_for_llm)
        else:
            full_prompt_contextvar.set(None)  # Ensure reset if no prompt

        if return_value:
            if type(return_value).__name__ == "RunResultStreaming":
                attributes[SpanAttributes.LLM_REQUEST_STREAMING] = True

        if exception:
            attributes[CoreAttributes.ERROR_TYPE] = type(exception).__name__
            # Contextvar is reset in the finally block of the main wrapper

        # Log all collected attributes before filtering
        logger.debug(
            f"[_extract_agent_runner_attributes_and_set_contextvar] All collected attributes before filtering for OTel span ID {otel_span_id_for_log}: {safe_serialize(attributes)}"
        )

        # Define filter conditions and log them
        # For gen_ai.prompt.* attributes (e.g., gen_ai.prompt.0.content, gen_ai.prompt.0.role)
        prompt_attr_prefix_to_exclude = "gen_ai.prompt."

        # For gen_ai.request.instructions
        # SpanAttributes.LLM_REQUEST_INSTRUCTIONS should resolve to "gen_ai.request.instructions"
        instructions_attr_key_to_exclude = SpanAttributes.LLM_REQUEST_INSTRUCTIONS

        logger.debug(
            f"[_extract_agent_runner_attributes_and_set_contextvar] Filter: Excluding keys starting with '{prompt_attr_prefix_to_exclude}' for OTel span ID {otel_span_id_for_log}"
        )
        logger.debug(
            f"[_extract_agent_runner_attributes_and_set_contextvar] Filter: Excluding key equal to '{instructions_attr_key_to_exclude}' (actual value of SpanAttributes.LLM_REQUEST_INSTRUCTIONS) for OTel span ID {otel_span_id_for_log}"
        )

        attributes_for_agent_span = {}
        for key, value in attributes.items():
            excluded_by_prompt_filter = key.startswith(prompt_attr_prefix_to_exclude)
            excluded_by_instructions_filter = key == instructions_attr_key_to_exclude

            if excluded_by_prompt_filter:
                logger.debug(
                    f"[_extract_agent_runner_attributes_and_set_contextvar] Filtering out key '{key}' for OTel span ID {otel_span_id_for_log} (matched prompt_prefix_to_exclude: '{prompt_attr_prefix_to_exclude}')"
                )
                continue
            if excluded_by_instructions_filter:
                logger.debug(
                    f"[_extract_agent_runner_attributes_and_set_contextvar] Filtering out key '{key}' for OTel span ID {otel_span_id_for_log} (matched instructions_attr_key_to_exclude: '{instructions_attr_key_to_exclude}')"
                )
                continue

            attributes_for_agent_span[key] = value

        logger.debug(
            f"[_extract_agent_runner_attributes_and_set_contextvar] Attributes for AGENT span (OTel span ID {otel_span_id_for_log}) after filtering: {safe_serialize(attributes_for_agent_span)}"
        )
        for key, value in attributes_for_agent_span.items():
            otel_span.set_attribute(key, value)

    def _create_agent_runner_wrapper(
        self, wrapped_method_to_call, is_async: bool, trace_name: str, span_kind: OtelSpanKind
    ):  # Renamed original_method for clarity
        """
        Creates a wrapper for an OpenAI Agents Runner method (run, run_sync, run_streamed).
        This wrapper starts an OTel span, extracts attributes, manages contextvar for full prompt,
        calls the original method, and ensures the span is ended and contextvar is reset.
        """
        otel_tracer = self._tracer  # Use the instrumentor's tracer

        if is_async:
            # Corrected wrapper signature for wrapt: (wrapped, instance, args, kwargs)
            @functools.wraps(wrapped_method_to_call)  # Use the passed original method for functools.wraps
            async def wrapper_async(wrapped, instance, args, kwargs):
                # 'wrapped' is the original unbound method (e.g., Runner.run)
                # 'instance' is the Runner class (if called as Runner.run) or Runner instance
                # 'args' and 'kwargs' are the arguments passed to Runner.run

                span_attributes_args = args  # These are the direct args to Runner.run
                span_attributes_kwargs = kwargs

                otel_span = otel_tracer.start_span(name=trace_name, kind=span_kind)
                with trace.use_span(otel_span, end_on_exit=False):
                    exception_obj = None
                    res = None
                    try:
                        # _extract_agent_runner_attributes_and_set_contextvar expects args and kwargs
                        # as they are passed to the *original method call*.
                        self._extract_agent_runner_attributes_and_set_contextvar(otel_span, args=args, kwargs=kwargs)
                        logger.debug(
                            f"wrapper_async: About to call wrapped method. instance type: {type(instance)}, args: {safe_serialize(args)}, kwargs: {safe_serialize(kwargs)}"
                        )

                        # How to call 'wrapped' depends on whether 'instance' is None (e.g. staticmethod called on class)
                        # or if 'instance' is the class itself (e.g. classmethod or instance method called on class)
                        # or if 'instance' is an actual object instance.
                        # Given the example call `Runner.run(agent, input, ...)` and `Runner.run` being an instance method,
                        # `instance` will be the `Runner` class. `wrapped` is the unbound method.
                        # We need to call it as `wrapped(instance, *args, **kwargs)` if it's an instance method
                        # and `instance` is the actual instance.
                        # If `instance` is the class, and `wrapped` is an instance method, this is like `Runner.run(Runner, agent, input, ...)`
                        # which was causing "5 arguments" error.
                        # The example `Runner.run(agent, input, ...)` implies the SDK handles this.
                        # So, the call should likely be `wrapped(*args, **kwargs)` if `instance` is the class and `wrapped` is a static/class method
                        # or if the SDK's `run` method descriptor handles being called from the class.
                        # If `wrapped` is an instance method, it needs an instance.
                        # The `main.py` calls `Runner.run(current_agent, input_items, context=context)`
                        # This means `args` = (current_agent, input_items), `kwargs` = {context: ...}
                        # The `Runner.run` signature is `run(self, agent, input, ...)`
                        # The most direct way to replicate the call from main.py is `wrapped(*args, **kwargs)`
                        # assuming `wrapped` is what `Runner.run` resolves to.

                        # If `wrapped` is the unbound instance method `run(self, agent, input, ...)`
                        # and `instance` is the class `Runner`, then `wrapped(instance, *args, **kwargs)`
                        # becomes `run(Runner, agent_arg, input_arg, ...)`. This is 3 positional.
                        # The error "5 were given" for this call is the core puzzle.

                        # The error "4 were given" for `wrapped(*args, **kwargs)` means `run(agent_arg, input_arg, ...)`
                        # was missing `self`.

                        # Let's stick to the wrapt convention: the `wrapped` callable should be invoked
                        # appropriately based on `instance`.
                        # If `instance` is not None, it's typically `wrapped(instance, *args, **kwargs)`.
                        # If `instance` is None (e.g. for a static method called via class), it's `wrapped(*args, **kwargs)`.
                        # Since `Runner.run` is an instance method, and `instance` is `Runner` (the class)
                        # when called as `Runner.run()`, this is an unbound call.
                        # The correct way to call an unbound instance method is `MethodType(wrapped, instance_obj)(*args, **kwargs)`
                        # OR `wrapped(instance_obj, *args, **kwargs)`.
                        # Here, `instance` is the class. The SDK must handle `Runner.run(agent, input)` by creating an instance.
                        # So, we should call `wrapped` as it was called in the user's code.
                        # The `args` and `kwargs` are what the user supplied to `Runner.run`.
                        # `wrapped` is `Runner.run`. So, `wrapped(*args, **kwargs)` is `Runner.run(*args, **kwargs)`.

                        res = await wrapped(*args, **kwargs)  # This replicates the original call structure

                        self._extract_agent_runner_attributes_and_set_contextvar(otel_span, return_value=res)
                        otel_span.set_status(Status(StatusCode.OK))
                    except Exception as e:
                        exception_obj = e
                        self._extract_agent_runner_attributes_and_set_contextvar(otel_span, exception=e)
                        otel_span.set_status(Status(StatusCode.ERROR, description=str(e)))
                        otel_span.record_exception(e)
                        raise  # Re-raise the exception
                    finally:
                        full_prompt_contextvar.set(None)  # Reset contextvar
                        otel_span.end()
                    return res

            return wrapper_async
        else:  # Synchronous wrapper
            # Corrected wrapper signature for wrapt: (wrapped, instance, args, kwargs)
            @functools.wraps(wrapped_method_to_call)  # Use the passed original method for functools.wraps
            def wrapper_sync(wrapped, instance, args, kwargs):
                span_attributes_args = args
                span_attributes_kwargs = kwargs

                otel_span = otel_tracer.start_span(name=trace_name, kind=span_kind)
                with trace.use_span(otel_span, end_on_exit=False):
                    exception_obj = None
                    res = None
                    try:
                        self._extract_agent_runner_attributes_and_set_contextvar(otel_span, args=args, kwargs=kwargs)
                        logger.debug(
                            f"wrapper_sync: About to call wrapped method. instance type: {type(instance)}, args: {safe_serialize(args)}, kwargs: {safe_serialize(kwargs)}"
                        )

                        res = wrapped(*args, **kwargs)  # Replicates original call structure

                        self._extract_agent_runner_attributes_and_set_contextvar(otel_span, return_value=res)
                        otel_span.set_status(Status(StatusCode.OK))
                    except Exception as e:
                        exception_obj = e
                        self._extract_agent_runner_attributes_and_set_contextvar(otel_span, exception=e)
                        otel_span.set_status(Status(StatusCode.ERROR, description=str(e)))
                        otel_span.record_exception(e)
                        raise
                    finally:
                        full_prompt_contextvar.set(None)
                        otel_span.end()
                    return res

            return wrapper_sync

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["openai-agents >= 0.0.1"]

    def _instrument(self, **kwargs):
        """Instrument the OpenAI Agents SDK."""
        logger.debug(
            f"OpenAIAgentsInstrumentor (id: {id(self)}) _instrument START. Current _is_instrumented_instance_flag: {self._is_instrumented_instance_flag}"
        )
        if self._is_instrumented_instance_flag:
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) already instrumented. Skipping.")
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _instrument END (skipped)")
            return

        tracer_provider = kwargs.get("tracer_provider")
        if self._tracer is None:
            self._tracer = trace.get_tracer("agentops.instrumentation.openai_agents", "0.1.0")
        logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) using tracer: {self._tracer}")

        try:
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) creating exporter and processor.")
            self._exporter = OpenAIAgentsExporter(tracer_provider=tracer_provider)
            self._processor = OpenAIAgentsProcessor(
                exporter=self._exporter,
            )
            from agents import set_trace_processors
            from agents.tracing.processors import default_processor

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) getting default processor...")
            if getattr(self, "_default_processor", None) is None:  # Check if already stored by this instance
                self._default_processor = default_processor()
                logger.debug(
                    f"OpenAIAgentsInstrumentor (id: {id(self)}) Stored original default processor: {self._default_processor}"
                )

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) setting trace processors to: {self._processor}")
            set_trace_processors([self._processor])
            logger.debug(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) Replaced default processor with OpenAIAgentsProcessor."
            )

            logger.debug(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) Applying Runner method wrappers using new custom wrapper..."
            )
            for config in AGENT_RUNNER_WRAP_CONFIGS:
                try:
                    module_path, class_name, method_name = config.package, config.class_name, config.method_name
                    # Ensure the module is imported correctly to find the class
                    # __import__ returns the top-level package, so need to getattr down
                    # For "agents.run", __import__("agents.run", fromlist=["Runner"])
                    # module = __import__(module_path, fromlist=[class_name]) # This might not work for nested modules correctly

                    # A more robust way to get the class
                    parts = module_path.split(".")
                    current_module = __import__(parts[0])
                    for part in parts[1:]:
                        current_module = getattr(current_module, part)

                    cls_to_wrap = getattr(current_module, class_name)
                    original_method = getattr(cls_to_wrap, method_name)

                    # Create the specific wrapper for this method
                    custom_wrapper = self._create_agent_runner_wrapper(
                        original_method,
                        is_async=config.is_async,
                        trace_name=config.trace_name,
                        span_kind=config.span_kind,
                    )

                    # Apply the wrapper using wrapt
                    # wrapt.wrap_function_wrapper expects module as string, name as string
                    # For class methods, name is 'ClassName.method_name'
                    wrapt.wrap_function_wrapper(
                        module_path,  # Module name as string
                        f"{class_name}.{method_name}",  # 'ClassName.method_name'
                        custom_wrapper,
                    )
                    logger.info(
                        f"OpenAIAgentsInstrumentor (id: {id(self)}) Applied custom wrapper for {class_name}.{method_name}"
                    )
                except Exception as e_wrap:
                    logger.error(
                        f"OpenAIAgentsInstrumentor (id: {id(self)}) Failed to apply custom wrapper for {config.method_name}: {e_wrap}",
                        exc_info=True,
                    )

            self._is_instrumented_instance_flag = True
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) set _is_instrumented_instance_flag to True.")

        except Exception as e:
            logger.warning(f"OpenAIAgentsInstrumentor (id: {id(self)}) Failed to instrument: {e}", exc_info=True)
        logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _instrument END")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI Agents SDK."""
        logger.debug(
            f"OpenAIAgentsInstrumentor (id: {id(self)}) _uninstrument START. Current _is_instrumented_instance_flag: {self._is_instrumented_instance_flag}"
        )
        if not self._is_instrumented_instance_flag:
            logger.debug(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) not currently instrumented. Skipping uninstrument."
            )
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _uninstrument END (skipped)")
            return
        try:
            if hasattr(self, "_exporter") and self._exporter:
                logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) Cleaning up exporter.")
                if hasattr(self._exporter, "cleanup"):
                    self._exporter.cleanup()

            from agents import set_trace_processors

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) Attempting to restore default processor.")
            if hasattr(self, "_default_processor") and self._default_processor:
                logger.debug(
                    f"OpenAIAgentsInstrumentor (id: {id(self)}) Restoring default processor: {self._default_processor}"
                )
                set_trace_processors([self._default_processor])
                self._default_processor = None
            else:
                logger.warning(f"OpenAIAgentsInstrumentor (id: {id(self)}) No default_processor to restore.")
            self._processor = None
            self._exporter = None

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) Removing Runner method wrappers...")
            for config in AGENT_RUNNER_WRAP_CONFIGS:
                try:
                    module_path, class_name, method_name = config.package, config.class_name, config.method_name

                    parts = module_path.split(".")
                    current_module = __import__(parts[0])
                    for part in parts[1:]:
                        current_module = getattr(current_module, part)

                    cls_to_wrap = getattr(current_module, class_name)

                    # Get the potentially wrapped method
                    method_to_unwrap = getattr(cls_to_wrap, method_name, None)

                    if hasattr(method_to_unwrap, "__wrapped__"):
                        # If it's a wrapt proxy, __wrapped__ gives the original
                        original = method_to_unwrap.__wrapped__
                        setattr(cls_to_wrap, method_name, original)
                        logger.info(
                            f"OpenAIAgentsInstrumentor (id: {id(self)}) Removed custom wrapper for {class_name}.{method_name}"
                        )
                    elif isinstance(method_to_unwrap, functools.partial) and hasattr(
                        method_to_unwrap.func, "__wrapped__"
                    ):
                        # Handle cases where it might be a partial of a wrapper (less common here but good to check)
                        original = method_to_unwrap.func.__wrapped__
                        setattr(cls_to_wrap, method_name, original)  # This might be tricky if partial had specific args
                        logger.info(
                            f"OpenAIAgentsInstrumentor (id: {id(self)}) Removed custom wrapper (from partial) for {class_name}.{method_name}"
                        )
                    else:
                        logger.warning(
                            f"OpenAIAgentsInstrumentor (id: {id(self)}) Wrapper not found or not a recognized wrapt wrapper for {class_name}.{method_name}. Current type: {type(method_to_unwrap)}"
                        )

                except Exception as e_unwrap:
                    logger.error(
                        f"OpenAIAgentsInstrumentor (id: {id(self)}) Failed to remove custom wrapper for {config.method_name}: {e_unwrap}",
                        exc_info=True,
                    )

            self._is_instrumented_instance_flag = False
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) set _is_instrumented_instance_flag to False.")

            logger.info(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) Successfully removed OpenAI Agents SDK instrumentation"
            )
        except Exception as e:
            logger.warning(f"OpenAIAgentsInstrumentor (id: {id(self)}) Failed to uninstrument: {e}", exc_info=True)
        logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _uninstrument END")
