"""NoOp Tracer and Span classes for disabling autogen-core's telemetry.

This module provides no-operation telemetry classes that prevent autogen-core
from creating duplicate spans while allowing AgentOps to have full control
over telemetry data.

"""
import sys
import logging
from contextlib import contextmanager
from autogen_core.tools._base import BaseTool, BaseStreamTool
from autogen_core._telemetry import _genai
import autogen_core
import autogen_agentchat.agents._base_chat_agent as base_chat_module
from autogen_core._telemetry import _tracing as _autogen_tracing
import contextlib

logger = logging.getLogger(__name__)


class NoOpSpan:
    """A no-op span that does nothing to disable autogen-core's telemetry."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Properly handle context exit to avoid detachment errors
        return False

    def is_recording(self):
        return False


class NoOpTracer:
    """A tracer that creates no-op spans to prevent autogen-core from creating real spans."""

    def start_as_current_span(self, *args, **kwargs):
        """Return a no-op context manager."""
        return self._noop_context_manager()

    def start_span(self, *args, **kwargs):
        """Return a no-op span."""
        return NoOpSpan()

    def use_span(self, *args, **kwargs):
        """Return a no-op context manager."""
        return self._noop_context_manager()

    def get_tracer(self, *args, **kwargs):
        """Return self to handle nested tracer calls."""
        return self

    @contextmanager
    def _noop_context_manager(self):
        """A proper context manager that doesn't interfere with OpenTelemetry context."""
        try:
            yield NoOpSpan()
        except Exception as e:
            logger.debug(f"[NoOp DEBUG] Exception in _noop_context_manager: {e}")
            raise
        finally:
            logger.debug("[NoOp DEBUG] NoOpTracer._noop_context_manager exiting")


def disable_autogen_telemetry():
    """Disable autogen-core's telemetry by patching BaseTool methods directly."""
    try:
        # Direct approach: Patch the BaseTool.run_json method to remove trace_tool_span usage
        try:
            # Store original methods
            if not hasattr(BaseTool, "_original_run_json"):
                setattr(BaseTool, "_original_run_json", BaseTool.run_json)
            if not hasattr(BaseStreamTool, "_original_run_json_stream"):
                setattr(BaseStreamTool, "_original_run_json_stream", BaseStreamTool.run_json_stream)

            # Create patched version of run_json without trace_tool_span
            async def patched_run_json(self, args, cancellation_token, call_id=None):
                """Patched run_json that skips trace_tool_span to prevent duplicate spans."""
                # Execute the tool's run method directly (skip tracing)
                return_value = await self.run(self._args_type.model_validate(args), cancellation_token)

                return return_value

            # Create patched version of run_json_stream without trace_tool_span
            async def patched_run_json_stream(self, args, cancellation_token, call_id=None):
                """Patched run_json_stream that skips trace_tool_span to prevent duplicate spans."""
                return_value = None

                # Execute the tool's run_stream method directly (skip tracing)
                async for result in self.run_stream(self._args_type.model_validate(args), cancellation_token):
                    return_value = result
                    yield result

                assert return_value is not None, "The tool must yield a final return value at the end of the stream."
                if not isinstance(return_value, self._return_type):
                    raise TypeError(
                        f"Expected return value of type {self._return_type.__name__}, but got {type(return_value).__name__}"
                    )

            # Replace the methods
            BaseTool.run_json = patched_run_json
            BaseStreamTool.run_json_stream = patched_run_json_stream

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch BaseTool methods: {e}")

        # Disable agent creation telemetry by patching trace_create_agent_span
        try:
            # Store original function
            if not hasattr(_genai, "_original_trace_create_agent_span"):
                setattr(_genai, "_original_trace_create_agent_span", _genai.trace_create_agent_span)

            # Create no-op replacement for trace_create_agent_span
            @contextmanager
            def noop_trace_create_agent_span(*args, **kwargs):
                """No-op replacement for trace_create_agent_span to prevent duplicate create_agent spans."""
                try:
                    yield NoOpSpan()
                except Exception as e:
                    logger.debug(f"[AutoGen DEBUG] Exception in noop_trace_create_agent_span: {e}")
                    raise

            # Replace the function
            _genai.trace_create_agent_span = noop_trace_create_agent_span

            # Also patch it in autogen_core module namespace if it's imported there
            try:
                if hasattr(autogen_core, "trace_create_agent_span"):
                    if not hasattr(autogen_core, "_original_trace_create_agent_span"):
                        setattr(autogen_core, "_original_trace_create_agent_span", autogen_core.trace_create_agent_span)
                    autogen_core.trace_create_agent_span = noop_trace_create_agent_span
            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Failed to patch autogen_core.trace_create_agent_span: {e}")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch trace_create_agent_span: {e}")

        # NEW: Disable agent invocation telemetry by patching trace_invoke_agent_span
        try:
            # Store original function
            if not hasattr(_genai, "_original_trace_invoke_agent_span"):
                setattr(_genai, "_original_trace_invoke_agent_span", _genai.trace_invoke_agent_span)

            # Create no-op replacement for trace_invoke_agent_span
            @contextmanager
            def noop_trace_invoke_agent_span(*args, **kwargs):
                """No-op replacement for trace_invoke_agent_span to prevent duplicate invoke_agent spans."""
                try:
                    yield NoOpSpan()
                except Exception as e:
                    logger.debug(f"[AutoGen DEBUG] Exception in noop_trace_invoke_agent_span: {e}")
                    raise
                finally:
                    logger.debug("[AutoGen DEBUG] noop_trace_invoke_agent_span exiting")

            # Replace the function
            _genai.trace_invoke_agent_span = noop_trace_invoke_agent_span

            # Also patch it in autogen_core module namespace if it's imported there
            try:
                if hasattr(autogen_core, "trace_invoke_agent_span"):
                    if not hasattr(autogen_core, "_original_trace_invoke_agent_span"):
                        setattr(autogen_core, "_original_trace_invoke_agent_span", autogen_core.trace_invoke_agent_span)
                    autogen_core.trace_invoke_agent_span = noop_trace_invoke_agent_span
            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Failed to patch autogen_core.trace_invoke_agent_span: {e}")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch trace_invoke_agent_span: {e}")

        # NEW: Disable tool telemetry by patching trace_tool_span
        try:
            # Store original function
            if not hasattr(_genai, "_original_trace_tool_span"):
                setattr(_genai, "_original_trace_tool_span", _genai.trace_tool_span)

            # Create no-op replacement for trace_tool_span
            @contextmanager
            def noop_trace_tool_span(*args, **kwargs):
                """No-op replacement for trace_tool_span to prevent tool tracing context issues."""
                try:
                    yield NoOpSpan()
                except Exception as e:
                    logger.debug(f"[AutoGen DEBUG] Exception in noop_trace_tool_span: {e}")
                    raise
                finally:
                    logger.debug("[AutoGen DEBUG] noop_trace_tool_span exiting")

            # Replace the function
            _genai.trace_tool_span = noop_trace_tool_span

            # Also patch it in autogen_core module namespace if it's imported there
            try:
                if hasattr(autogen_core, "trace_tool_span"):
                    if not hasattr(autogen_core, "_original_trace_tool_span"):
                        setattr(autogen_core, "_original_trace_tool_span", autogen_core.trace_tool_span)
                    autogen_core.trace_tool_span = noop_trace_tool_span
            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Failed to patch autogen_core.trace_tool_span: {e}")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch trace_tool_span: {e}")

        try:
            # Patch TraceHelper.trace_block to be a no-op context manager
            if hasattr(_autogen_tracing.TraceHelper, "trace_block") and not hasattr(
                _autogen_tracing.TraceHelper, "_original_trace_block"
            ):
                setattr(
                    _autogen_tracing.TraceHelper,
                    "_original_trace_block",
                    _autogen_tracing.TraceHelper.trace_block,
                )

                def _noop_trace_block(self, *args, **kwargs):  # type: ignore[override]
                    @contextlib.contextmanager
                    def _cm():
                        yield NoOpSpan()

                    # Return the context manager so callers can use `with` as usual
                    return _cm()

                _autogen_tracing.TraceHelper.trace_block = _noop_trace_block  # type: ignore[assignment]

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch TraceHelper.trace_block: {e}")

        # Also patch any existing tracer instances in autogen modules

        modules_to_check = [
            "autogen_core.tools._base",
            "autogen_core._telemetry._genai",
            "autogen_agentchat.agents._assistant_agent",
            "autogen_agentchat.agents._base_chat_agent",
        ]

        noop_tracer = NoOpTracer()
        for module_name in modules_to_check:
            if module_name in sys.modules:
                try:
                    module = sys.modules[module_name]
                    # Look for tracer attributes and replace them
                    if hasattr(module, "tracer"):
                        setattr(module, "tracer", noop_tracer)
                except Exception as e:
                    logger.debug(f"[AutoGen DEBUG] Failed to replace tracer in {module_name}: {e}")

        # CRITICAL: Patch the specific modules that import and use trace_create_agent_span
        try:
            # Patch the base chat agent module which directly imports and uses trace_create_agent_span

            # Store original function if not already stored and if it exists
            if hasattr(base_chat_module, "trace_create_agent_span"):
                if not hasattr(base_chat_module, "_original_trace_create_agent_span"):
                    original_func = getattr(base_chat_module, "trace_create_agent_span")
                    setattr(base_chat_module, "_original_trace_create_agent_span", original_func)

                # Create no-op replacement
                @contextmanager
                def noop_trace_create_agent_span_local(*args, **kwargs):
                    """No-op replacement for trace_create_agent_span in base chat agent module."""
                    try:
                        yield NoOpSpan()
                    except Exception as e:
                        logger.debug(f"[AutoGen DEBUG] Exception in noop_trace_create_agent_span_local: {e}")
                        raise

                # Replace the imported function in the module
                setattr(base_chat_module, "trace_create_agent_span", noop_trace_create_agent_span_local)
            else:
                logger.debug("[AutoGen DEBUG] trace_create_agent_span not found in base chat agent module")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch base chat agent module: {e}")

        # Also patch the invoke agent span in the same module
        try:
            # Store original function if not already stored and if it exists
            if hasattr(base_chat_module, "trace_invoke_agent_span"):
                if not hasattr(base_chat_module, "_original_trace_invoke_agent_span"):
                    original_func = getattr(base_chat_module, "trace_invoke_agent_span")
                    setattr(base_chat_module, "_original_trace_invoke_agent_span", original_func)

                # Create no-op replacement
                @contextmanager
                def noop_trace_invoke_agent_span_local(*args, **kwargs):
                    """No-op replacement for trace_invoke_agent_span in base chat agent module."""
                    try:
                        yield NoOpSpan()
                    except Exception as e:
                        logger.debug(f"[AutoGen DEBUG] Exception in noop_trace_invoke_agent_span_local: {e}")
                        raise
                    finally:
                        logger.debug("[AutoGen DEBUG] noop_trace_invoke_agent_span_local exiting")

                # Replace the imported function in the module
                setattr(base_chat_module, "trace_invoke_agent_span", noop_trace_invoke_agent_span_local)
            else:
                logger.debug("[AutoGen DEBUG] trace_invoke_agent_span not found in base chat agent module")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to patch invoke agent span in base chat agent module: {e}")

        logger.debug("[AutoGen DEBUG] Successfully disabled autogen-core telemetry")
        return True

    except Exception as e:
        logger.debug(f"[AutoGen DEBUG] Failed to disable autogen-core telemetry: {e}")
        return False


def restore_autogen_telemetry():
    """Restore autogen-core's original telemetry (for cleanup/unwrapping)."""
    try:
        # Restore original BaseTool methods
        try:
            # Restore original methods if they were saved
            if hasattr(BaseTool, "_original_run_json"):
                original_method = getattr(BaseTool, "_original_run_json")
                BaseTool.run_json = original_method
                delattr(BaseTool, "_original_run_json")

            if hasattr(BaseStreamTool, "_original_run_json_stream"):
                original_method = getattr(BaseStreamTool, "_original_run_json_stream")
                BaseStreamTool.run_json_stream = original_method
                delattr(BaseStreamTool, "_original_run_json_stream")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to restore BaseTool methods: {e}")

        # NEW: Restore original trace_create_agent_span function
        try:
            # Restore original function if it was saved
            if hasattr(_genai, "_original_trace_create_agent_span"):
                original_function = getattr(_genai, "_original_trace_create_agent_span")
                _genai.trace_create_agent_span = original_function
                delattr(_genai, "_original_trace_create_agent_span")

            # Also restore in autogen_core module namespace if it was patched
            try:
                if hasattr(autogen_core, "_original_trace_create_agent_span"):
                    original_function = getattr(autogen_core, "_original_trace_create_agent_span")
                    autogen_core.trace_create_agent_span = original_function
                    delattr(autogen_core, "_original_trace_create_agent_span")
            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Failed to restore autogen_core.trace_create_agent_span: {e}")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to restore trace_create_agent_span: {e}")

        # NEW: Restore original trace_invoke_agent_span function
        try:
            # Restore original function if it was saved
            if hasattr(_genai, "_original_trace_invoke_agent_span"):
                original_function = getattr(_genai, "_original_trace_invoke_agent_span")
                _genai.trace_invoke_agent_span = original_function
                delattr(_genai, "_original_trace_invoke_agent_span")

            # Also restore in autogen_core module namespace if it was patched
            try:
                if hasattr(autogen_core, "_original_trace_invoke_agent_span"):
                    original_function = getattr(autogen_core, "_original_trace_invoke_agent_span")
                    autogen_core.trace_invoke_agent_span = original_function
                    delattr(autogen_core, "_original_trace_invoke_agent_span")
            except Exception as e:
                logger.debug(f"[AutoGen DEBUG] Failed to restore autogen_core.trace_invoke_agent_span: {e}")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to restore trace_invoke_agent_span: {e}")

        # NEW: Restore original trace_tool_span function
        try:
            # Restore original function if it was saved
            if hasattr(_genai, "_original_trace_tool_span"):
                original_function = getattr(_genai, "_original_trace_tool_span")
                _genai.trace_tool_span = original_function
                delattr(_genai, "_original_trace_tool_span")

            # Also restore in autogen_core module namespace if it was patched

            if hasattr(autogen_core, "_original_trace_tool_span"):
                original_function = getattr(autogen_core, "_original_trace_tool_span")
                autogen_core.trace_tool_span = original_function
                delattr(autogen_core, "_original_trace_tool_span")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to restore trace_tool_span: {e}")

        # NEW: Restore original functions in base chat agent module
        try:
            # Restore trace_create_agent_span if it was patched
            if hasattr(base_chat_module, "_original_trace_create_agent_span"):
                original_function = getattr(base_chat_module, "_original_trace_create_agent_span")
                setattr(base_chat_module, "trace_create_agent_span", original_function)
                delattr(base_chat_module, "_original_trace_create_agent_span")
                logger.debug("[AutoGen DEBUG] Restored trace_create_agent_span in base chat agent module")

            # Restore trace_invoke_agent_span if it was patched
            if hasattr(base_chat_module, "_original_trace_invoke_agent_span"):
                original_function = getattr(base_chat_module, "_original_trace_invoke_agent_span")
                setattr(base_chat_module, "trace_invoke_agent_span", original_function)
                delattr(base_chat_module, "_original_trace_invoke_agent_span")
        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to restore functions in base chat agent module: {e}")

        try:
            if hasattr(_autogen_tracing.TraceHelper, "_original_trace_block"):
                original_func = getattr(_autogen_tracing.TraceHelper, "_original_trace_block")
                _autogen_tracing.TraceHelper.trace_block = original_func  # type: ignore[assignment]
                delattr(_autogen_tracing.TraceHelper, "_original_trace_block")

        except Exception as e:
            logger.debug(f"[AutoGen DEBUG] Failed to restore TraceHelper.trace_block: {e}")

        return True

    except Exception as e:
        logger.debug(f"[AutoGen DEBUG] Failed to restore autogen-core telemetry: {e}")
        return False
