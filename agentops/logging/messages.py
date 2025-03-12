from termcolor import colored

from agentops.logging import logger
from agentops.client.http import HttpClient



import functools
from typing import Optional, Any, Callable, TypeVar, cast
from contextlib import contextmanager

from opentelemetry import trace, context
from opentelemetry.trace import Span

from agentops.logging import logger
from agentops.sdk.converters import trace_id_to_uuid

F = TypeVar('F', bound=Callable[..., Any])


def get_trace_id(span: Optional[Span] = None) -> str:
    """
    Get the trace ID from the current span or a provided span.
    
    Args:
        span: Optional span to get the trace ID from. If None, uses the current span.
        
    Returns:
        String representation of the trace ID, or "unknown" if no span is available.
    """
    if span is None:
        span = trace.get_current_span()

    if span and hasattr(span, 'get_span_context') and span.get_span_context().trace_id != 0:
        return str(span.get_span_context().trace_id)

    return "unknown"


def get_session_url(span: Optional[Span] = None) -> str:
    """
    Generate a session URL from the current span or a provided span.
    
    Args:
        span: Optional span to get the trace ID from. If None, uses the current span.
        
    Returns:
        Session URL for the AgentOps dashboard, or an empty string if no span is available.
    """
    trace_id = get_trace_id(span)

    if trace_id == "unknown":
        return ""

    # Convert trace ID to UUID format
    session_id = trace_id_to_uuid(int(trace_id))

    # Return the session URL
    return f"https://app.agentops.ai/drilldown?session_id={session_id}"


@contextmanager
def use_span_context(span: Span):
    """
    Context manager for using a span's context.
    
    Args:
        span: The span whose context to use.
    """
    # Get the current context
    current_context = context.get_current()

    # Set the span in the context
    ctx = trace.set_span_in_context(span, current_context)

    # Attach the context
    token = context.attach(ctx)

    try:
        # Log the trace ID for debugging
        logger.debug(f"Span context attached: {get_trace_id(span)}")

        # Yield control back to the caller
        yield
    finally:
        # Detach the context
        context.detach(token)
        logger.debug(f"Span context detached: {get_trace_id(span)}")


def with_span_context(func: F) -> F:
    """
    Decorator for using a span's context.
    
    This decorator is intended for methods of classes that have a `span` attribute.
    
    Args:
        func: The function to decorate.
        
    Returns:
        Decorated function that uses the span's context.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'span'):
            return func(self, *args, **kwargs)

        with use_span_context(self.span):
            return func(self, *args, **kwargs)

    return cast(F, wrapper)


# if operation_type == SpanKind.SESSION:
#     from agentops.sdk.decorators.context_utils import get_session_url

#     session_url = get_session_url(span)
#     if session_url:
#         logger.info(f"\x1b[34m🖇 AgentOps: Session Replay: {session_url}\x1b[0m")

# if operation_type == SpanKind.SESSION:
#     from agentops.sdk.decorators.context_utils import get_session_url

#     session_url = get_session_url(span)
#     if session_url:
#         logger.info(f"\x1b[34m🖇 AgentOps: Session Replay: {session_url}\x1b[0m")

# span, ctx, token = _make_span(operation_name, operation_type, version)

# if operation_type == SpanKind.SESSION:
#     from agentops.sdk.decorators.context_utils import get_session_url

#     session_url = get_session_url(span)
#     if session_url:
#         logger.info(f"\x1b[34m🖇 AgentOps: Session Replay: {session_url}\x1b[0m")

# instrumented_method = instrument_operation(span_kind=span_kind, name=operation_name, version=version)(
#     target_method
# )


class MessageHydrator:
    DASHBOARD_URL = "https://app.agentops.com"
    
    def _get_response(self) -> Optional[Response]:
        payload = {"session": self.__dict__}
        try:
            response = HttpClient.post(
                f"{self.config.endpoint}/v2/update_session",
                json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                api_key=self.config.api_key,
                jwt=self.jwt,
            )
        except ApiServerException as e:
            return logger.error(f"Could not end session - {e}")

        logger.debug(response.body)
        return response

    def _format_duration(self, start_time, end_time) -> str:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = end - start

        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{int(hours)}h")
        if minutes > 0:
            parts.append(f"{int(minutes)}m")
        parts.append(f"{seconds:.1f}s")

        return " ".join(parts)

    def _get_token_cost(self, response: Response) -> Decimal:
        token_cost = response.body.get("token_cost", "unknown")
        if token_cost == "unknown" or token_cost is None:
            return Decimal(0)
        return Decimal(token_cost)

    def _format_token_cost(self, token_cost: Decimal) -> str:
        return (
            "{:.2f}".format(token_cost)
            if token_cost == 0
            else "{:.6f}".format(token_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
        )

    def get_analytics(self) -> Optional[Dict[str, Any]]:
        if not self.end_timestamp:
            self.end_timestamp = get_ISO_time()

        formatted_duration = self._format_duration(self.init_timestamp, self.end_timestamp)

        if (response := self._get_response()) is None:
            return None

        self.token_cost = self._get_token_cost(response)

        return {
            "LLM calls": self.event_counts["llms"],
            "Tool calls": self.event_counts["tools"],
            "Actions": self.event_counts["actions"],
            "Errors": self.event_counts["errors"],
            "Duration": formatted_duration,
            "Cost": self._format_token_cost(self.token_cost),
        }

    @property
    def session_url(self) -> str:
        """Returns the URL for this session in the AgentOps dashboard."""
        assert self.session_id, "Session ID is required to generate a session URL"
        return f"https://app.agentops.ai/drilldown?session_id={self.session_id}"


def log_startup_message(self):
    """Log a startup message."""
    project_id = ""  # TODO
    dashboard_url = f"{DASHBOARD_URL}/{project_id}"
    logger.info(
        colored(
            f"\x1b[34mSession Replay: {dashboard_url}\x1b[0m",
            "blue",
        )
    )


def log_shutdown_message(self):
    """Log a shutdown message."""
    if analytics_stats := self.get_analytics():
        analytics = (
            f"Session Stats - "
            f"{colored('Duration:', attrs=['bold'])} {analytics_stats['Duration']} | "
            f"{colored('Cost:', attrs=['bold'])} ${analytics_stats['Cost']} | "
            f"{colored('LLMs:', attrs=['bold'])} {analytics_stats['LLM calls']} | "
            f"{colored('Tools:', attrs=['bold'])} {analytics_stats['Tool calls']} | "
            f"{colored('Actions:', attrs=['bold'])} {analytics_stats['Actions']} | "
            f"{colored('Errors:', attrs=['bold'])} {analytics_stats['Errors']}"
        )
        logger.info(analytics)


def _get_analytics(project_id: str) -> dict:
    """Get analytics for the project."""
    pass