from agentops.common.route_config import RouteConfig
from .agent.job import KickoffRunView
from .v1.auth import AccessTokenView
from .v1.projects import ProjectView
from .v1.traces import TraceView, TraceMetricsView
from .v1.spans import SpanView, SpanMetricsView

__all__ = ["route_config"]


route_config: list[RouteConfig] = [
    # auth routes
    RouteConfig(
        name='get_access_token',
        path="/auth/access_token",
        endpoint=AccessTokenView,
        methods=["POST"],
    ),

    # obserability routes
    RouteConfig(
        name='get_project',
        path="/project",
        endpoint=ProjectView,
        methods=["GET"],
    ),
    RouteConfig(
        name='get_trace',
        path="/traces/{trace_id}",
        endpoint=TraceView,
        methods=["GET"],
    ),
    RouteConfig(
        name='get_trace_metrics',
        path="/traces/{trace_id}/metrics",
        endpoint=TraceMetricsView,
        methods=["GET"],
    ),
    RouteConfig(
        name='get_span',
        path="/spans/{span_id}",
        endpoint=SpanView,
        methods=["GET"],
    ),
    RouteConfig(
        name='get_span_metrics',
        path="/spans/{span_id}/metrics",
        endpoint=SpanMetricsView,
        methods=["GET"],
    ),

    # agent routes
    RouteConfig(
        name='kickoff_run',
        path="/agent/run",
        endpoint=KickoffRunView,
        methods=["POST"],
    ),
]
