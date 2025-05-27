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
from opentelemetry.trace import SpanKind as OtelSpanKind  # Renamed to avoid conflict
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore
import wrapt  # For wrapping
# Remove local contextvars import, will import from .context
# import contextvars

from agentops.logging import logger
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter
from .context import full_prompt_contextvar, agent_name_contextvar, agent_handoffs_contextvar  # Import from .context
from agentops.instrumentation.common.wrappers import WrapConfig  # Keep WrapConfig

# Remove wrap, unwrap from common.wrappers as we'll use wrapt directly for custom wrapper
# from agentops.instrumentation.common.wrappers import wrap, unwrap
from agentops.helpers import safe_serialize

# Semantic conventions from AgentOps (Copied from runner_wrappers.py for use in new handler logic)
from agentops.semconv import (
    AgentOpsSpanKindValues,
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

    def _prepare_and_set_agent_contextvars(
        self,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
    ) -> None:
        """
        Helper to extract agent information and set context variables for later use by the exporter.
        This method does NOT create or modify OTel spans directly.
        """
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
        extracted_agent_name: Optional[str] = None
        extracted_handoffs: Optional[list[str]] = None

        if agent_obj:
            if hasattr(agent_obj, "name") and agent_obj.name:
                extracted_agent_name = str(agent_obj.name)
            if hasattr(agent_obj, "instructions") and agent_obj.instructions:
                instructions = str(agent_obj.instructions)
                current_full_prompt_for_llm.append({"role": "system", "content": instructions})
            if hasattr(agent_obj, "handoffs") and agent_obj.handoffs:
                processed_handoffs = []
                for h_item in agent_obj.handoffs:
                    if isinstance(h_item, str):
                        processed_handoffs.append(h_item)
                    elif hasattr(h_item, "agent_name") and h_item.agent_name:  # For Handoff callable wrapper
                        processed_handoffs.append(str(h_item.agent_name))
                    elif hasattr(h_item, "name") and h_item.name:  # For Agent objects
                        processed_handoffs.append(str(h_item.name))
                    else:
                        processed_handoffs.append(str(h_item))  # Fallback
                extracted_handoffs = processed_handoffs

        if sdk_input:
            if isinstance(sdk_input, str):
                current_full_prompt_for_llm.append({"role": "user", "content": sdk_input})
            elif isinstance(sdk_input, list):
                for i, msg in enumerate(sdk_input):  # msg is already a dict from sdk_input list
                    if isinstance(msg, dict):
                        role = msg.get("role")
                        content = msg.get("content")
                        if role and content is not None:
                            current_full_prompt_for_llm.append({"role": str(role), "content": safe_serialize(content)})

        # Set context variables for the exporter to pick up
        if extracted_agent_name:
            agent_name_contextvar.set(extracted_agent_name)
            logger.debug(f"[_prepare_and_set_agent_contextvars] Set agent_name_contextvar to: {extracted_agent_name}")
        else:  # Ensure it's set to None if no agent_name
            agent_name_contextvar.set(None)

        if extracted_handoffs:
            agent_handoffs_contextvar.set(extracted_handoffs)
            logger.debug(
                f"[_prepare_and_set_agent_contextvars] Set agent_handoffs_contextvar to: {safe_serialize(extracted_handoffs)}"
            )
        else:  # Ensure it's set to None if no handoffs
            agent_handoffs_contextvar.set(None)

        if current_full_prompt_for_llm:
            full_prompt_contextvar.set(current_full_prompt_for_llm)
            logger.debug(
                f"[_prepare_and_set_agent_contextvars] Set full_prompt_contextvar to: {safe_serialize(current_full_prompt_for_llm)}"
            )
        else:
            full_prompt_contextvar.set(None)

    def _create_agent_runner_wrapper(
        self, wrapped_method_to_call, is_async: bool
    ):  # trace_name and span_kind no longer needed
        """
        Creates a wrapper for an OpenAI Agents Runner method (run, run_sync, run_streamed).
        This wrapper NO LONGER starts an OTel span. It only prepares and sets context variables.
        """
        # otel_tracer = self._tracer # No longer creating spans here

        if is_async:

            @functools.wraps(wrapped_method_to_call)
            async def wrapper_async(wrapped, instance, args, kwargs):
                # Initialize context var tokens to their current values before setting new ones
                token_full_prompt = full_prompt_contextvar.set(None)
                token_agent_name = agent_name_contextvar.set(None)
                token_agent_handoffs = agent_handoffs_contextvar.set(None)
                res = None
                try:
                    self._prepare_and_set_agent_contextvars(args=args, kwargs=kwargs)
                    res = await wrapped(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Exception in wrapped async agent call: {e}", exc_info=True)
                    raise
                finally:
                    # Reset context variables to their state before this wrapper ran
                    if token_full_prompt is not None:
                        full_prompt_contextvar.reset(token_full_prompt)
                    if token_agent_name is not None:
                        agent_name_contextvar.reset(token_agent_name)
                    if token_agent_handoffs is not None:
                        agent_handoffs_contextvar.reset(token_agent_handoffs)
                return res

            return wrapper_async
        else:  # Synchronous wrapper

            @functools.wraps(wrapped_method_to_call)
            def wrapper_sync(wrapped, instance, args, kwargs):
                token_full_prompt = full_prompt_contextvar.set(None)
                token_agent_name = agent_name_contextvar.set(None)
                token_agent_handoffs = agent_handoffs_contextvar.set(None)
                res = None
                try:
                    self._prepare_and_set_agent_contextvars(args=args, kwargs=kwargs)
                    res = wrapped(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Exception in wrapped sync agent call: {e}", exc_info=True)
                    raise
                finally:
                    if token_full_prompt is not None:
                        full_prompt_contextvar.reset(token_full_prompt)
                    if token_agent_name is not None:
                        agent_name_contextvar.reset(token_agent_name)
                    if token_agent_handoffs is not None:
                        agent_handoffs_contextvar.reset(token_agent_handoffs)
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
                        # trace_name and span_kind are no longer passed
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
