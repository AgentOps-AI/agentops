from typing import Optional
from datetime import datetime
from fastapi import Depends, Query, HTTPException, status
import hashlib
from time import time

from agentops.common.environment import (
    APP_URL,
    FREEPLAN_TRACE_MIN_NUM,
    FREEPLAN_TRACE_DAYS_CUTOFF,
    FREEPLAN_SPANS_LIST_LIMIT,
)
from agentops.common.route_config import BaseView
from agentops.common.views import add_cors_headers
from agentops.common.orm import get_orm_session, Session
from agentops.common.freeplan import freeplan_clamp_datetime

from agentops.opsboard.models import ProjectModel
from agentops.api.models.traces import TraceModel, TraceSummaryModel, TraceListModel
from agentops.api.models.span_metrics import SpanMetricsResponse, TraceMetricsResponse

from .responses import (
    TraceListResponse,
    TraceListItem,
    TraceDetailResponse,
    SpanItem,
)


def has_llm_attributes(span_attributes: dict) -> bool:
    """
    Check if a span has LLM-related attributes that indicate it should have metrics.
    Based on the OpenTelemetry semantic conventions for AI and LLM spans.
    """
    # Check for Gen AI attributes
    gen_ai_attrs = [
        'gen_ai.completion',
        'gen_ai.prompt',
        'gen_ai.usage',
        'gen_ai.usage.prompt_tokens',
        'gen_ai.usage.completion_tokens',
        'gen_ai.usage.total_tokens',
        'gen_ai.usage.prompt_cost',
        'gen_ai.usage.completion_cost',
        'gen_ai.usage.total_cost',
        'gen_ai.usage.cache_read_input_tokens',
        'gen_ai.usage.reasoning_tokens',
    ]

    # Check for legacy LLM attributes
    legacy_attrs = [
        'ai.system',
        'ai.llm',
        'llm.request.model',
        'llm.response.model',
        'llm.system',
    ]

    # Check if any of these attributes exist in the span
    for attr in gen_ai_attrs + legacy_attrs:
        if attr in span_attributes:
            return True

    return False


# Simple in-memory cache for trace lists
class TraceListCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self._cache = {}
        self._ttl = ttl_seconds

    def _make_key(
        self,
        project_id: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        query: Optional[str],
        limit: int,
        offset: int,
        order_by: str,
        sort_order: str,
    ) -> str:
        """Create a cache key from parameters"""
        key_parts = [
            project_id,
            start_time.isoformat() if start_time else "none",
            end_time.isoformat() if end_time else "none",
            query or "none",
            str(limit),
            str(offset),
            order_by,
            sort_order,
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, **kwargs):
        """Get cached value if not expired"""
        key = self._make_key(**kwargs)
        if key in self._cache:
            cached_data, cached_time = self._cache[key]
            if time() - cached_time < self._ttl:
                return cached_data
            else:
                del self._cache[key]
        return None

    def set(self, data, **kwargs):
        """Set cache value with current timestamp"""
        key = self._make_key(**kwargs)
        self._cache[key] = (data, time())

        # Simple cleanup
        if len(self._cache) > 500:
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:50]:
                del self._cache[key]


# Global cache instance
# Reduce cache TTL to 30 seconds to ensure newly ingested traces appear promptly
trace_list_cache = TraceListCache(ttl_seconds=30)  # 30-second cache for trace lists


class BaseTraceView(BaseView):
    """
    Common base class for trace views.
    """

    orm: Session
    project: ProjectModel
    freeplan_truncated: bool = False

    async def get_project(self, project_id: str) -> ProjectModel:
        """
        Retrieves the project by ID and checks if the user has access to it.
        Raises HTTPException if the project is not found or access is denied.
        """
        project = ProjectModel.get_by_id(self.orm, project_id)

        if not project or not project.org.is_user_member(self.request.state.session.user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        return project

    async def get_trace_ids(self, limit: int, offset: int = 0) -> set[str]:
        """
        Retrieves the trace IDs for the project, limited by the specified number and offset.
        """
        traces = await TraceSummaryModel.select(
            # fields=["trace_id"],
            filters={"project_id": self.project.id},
            order_by="start_time DESC",
            limit=limit,
            offset=offset,
        )
        return {trace.trace_id for trace in traces}

    async def trace_is_freeplan_truncated(self, trace: TraceModel) -> bool:
        """
        Determines if a trace is truncated for free plan users.
        """
        if not self.project.is_freeplan:
            return False  # not a freeplan, always allow

        if not hasattr(self, '_freeplan_trace_ids'):  # cache the minimum visible trace IDs
            self._freeplan_trace_ids = await self.get_trace_ids(FREEPLAN_TRACE_MIN_NUM)

        if trace.trace_id in self._freeplan_trace_ids:  # trace is in the minimum visible traces, allow
            return False

        return freeplan_clamp_datetime(trace.end_time, FREEPLAN_TRACE_DAYS_CUTOFF) > trace.end_time


class TraceListView(BaseTraceView):
    """
    TraceListView handles the logic for retrieving a list of traces based on the provided filters.
    It uses the TraceListModel to query the database and formats the response using the
    TraceListResponse model.
    """

    limit: int
    offset: int

    @add_cors_headers(
        origins=[APP_URL],
        methods=["GET", "OPTIONS"],
    )
    async def __call__(
        self,
        *,
        orm: Session = Depends(get_orm_session),
        project_id: str,
        start_time: Optional[datetime] = Query(
            None, description="Filter by timestamp start (ISO 8601 format, e.g., '2023-01-01T00:00:00Z')"
        ),
        end_time: Optional[datetime] = Query(
            None, description="Filter by timestamp end (ISO 8601 format, e.g., '2023-01-01T00:00:00Z')"
        ),
        query: Optional[str] = Query(
            None, description="Search by span name, trace_id, or tags (case insensitive)"
        ),
        limit: int = Query(
            20, ge=1, le=100, description="Maximum number of traces to return (default: 20, max: 100)"
        ),
        offset: int = Query(0, ge=0, description="Offset for pagination (default: 0)"),
        order_by: str = Query("start_time", description="Field to sort by (default: 'timestamp')."),
        sort_order: str = Query(
            # TODO restrict this to an Enum
            "DESC",
            description="Sort order for timestamp (ASC or DESC)",
        ),
    ) -> TraceListResponse:
        """
        Callable method to handle the request and return a JSONResponse. This method
        validates the input parameters, retrieves the trace data, formats the
        response and converts exceptions to responses.
        """
        self.orm = orm
        self.limit = limit
        self.offset = offset
        self.project = await self.get_project(project_id)

        # Check cache first
        # Only use the cache if we're not requesting the very first page (offset == 0) OR
        # if specific filters are provided. The first page is the one that is most sensitive
        # to freshness because it shows the most recent traces. By fetching it live we ensure
        # the newest traces are always visible immediately after page refresh.
        should_use_cache = offset != 0 or query is not None or start_time is not None or end_time is not None

        cache_params = {
            'project_id': project_id,
            'start_time': start_time,
            'end_time': end_time,
            'query': query,
            'limit': limit,
            'offset': offset,
            'order_by': order_by,
            'sort_order': sort_order,
        }

        cached_response = None
        if should_use_cache:
            cached_response = trace_list_cache.get(**cache_params)

        if cached_response is not None:
            # Update freeplan_truncated flag based on current project status
            if self.project.is_freeplan and cached_response.total > FREEPLAN_TRACE_MIN_NUM:
                return TraceListResponse(
                    traces=cached_response.traces,
                    metrics=cached_response.metrics,
                    total=cached_response.total,
                    limit=cached_response.limit,
                    offset=cached_response.offset,
                    freeplan_truncated=True,
                )
            return cached_response

        trace_list = await TraceListModel.select(
            filters={
                "project_id": self.project.id,
                "start_time": start_time,
                "end_time": end_time,
            },
            search=query,
            order_by=f"{order_by} {sort_order}",
            limit=self.limit,
            offset=self.offset,
        )

        if self.project.is_freeplan and trace_list.trace_count > FREEPLAN_TRACE_MIN_NUM:
            # if we're showing more than the minimum number of traces we are truncating
            self.freeplan_truncated = True

        response = await self.get_response(trace_list)

        # Cache the response only if we used cache for this request
        if should_use_cache:
            trace_list_cache.set(response, **cache_params)

        return response

    async def get_response(self, trace_list: TraceListModel) -> TraceListResponse:
        """
        Formats the trace list response from the TraceListModel instance.
        """

        return TraceListResponse(
            traces=[
                TraceListItem(
                    trace_id=trace.trace_id,
                    root_service_name=trace.service_name,
                    root_span_name=trace.span_name,
                    start_time=trace.start_time,
                    end_time=trace.end_time,
                    duration=trace.duration,
                    span_count=trace.span_count,
                    error_count=trace.error_count,
                    tags=trace.tags,
                    total_cost=trace.total_cost,
                    freeplan_truncated=await self.trace_is_freeplan_truncated(trace),
                )
                for trace in trace_list.traces
            ],
            metrics=TraceMetricsResponse.from_trace_with_metrics(trace_list),
            total=trace_list.trace_count,
            limit=self.limit,
            offset=self.offset,
            freeplan_truncated=self.freeplan_truncated,
        )


class TraceDetailView(BaseTraceView):
    """
    TraceDetailView handles the logic for retrieving the details of a specific
    trace based on the trace_id. It uses the TraceModel to query the database and
    formats the response using the TraceDetailResponse model.
    """

    @add_cors_headers(
        origins=[APP_URL],
        methods=["GET", "OPTIONS"],
    )
    async def __call__(
        self,
        *,
        orm: Session = Depends(get_orm_session),
        trace_id: str,
    ) -> TraceDetailResponse:
        """
        Callable method to handle the request and return a JSONResponse. This method
        validates the input parameters, retrieves the trace data, formats the
        response and converts exceptions to responses.
        """
        self.orm = orm

        trace = await TraceModel.select(
            filters={
                "trace_id": trace_id,
            }
        )

        if not trace.spans:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found.")

        self.project = await self.get_project(trace.project_id)
        self.freeplan_truncated = await self.trace_is_freeplan_truncated(trace)

        return await self.get_response(trace)

    async def get_response(self, trace: TraceModel) -> TraceDetailResponse:
        """
        Formats the trace detail response from the TraceModel instance.
        """

        return TraceDetailResponse(
            project_id=trace.project_id,
            trace_id=trace.trace_id,
            tags=trace.tags,
            metrics=TraceMetricsResponse.from_trace_with_metrics(trace),
            spans=[
                SpanItem(
                    span_id=span.span_id,
                    parent_span_id=span.parent_span_id,
                    span_name=span.span_name,
                    span_kind=span.span_kind,
                    # span_type is inferred from span_attributes after init
                    service_name=span.service_name,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    duration=span.duration,
                    status_code=span.status_code,
                    status_message=span.status_message,
                    attributes={},  # TODO remove this
                    span_attributes=span.span_attributes,
                    resource_attributes=span.resource_attributes,
                    event_timestamps=span.event_timestamps,
                    event_names=span.event_names,
                    event_attributes=span.event_attributes,
                    link_trace_ids=span.link_trace_ids,
                    link_span_ids=span.link_span_ids,
                    link_trace_states=span.link_trace_states,
                    link_attributes=span.link_attributes,
                    metrics=SpanMetricsResponse.from_span_with_metrics(span)
                    if has_llm_attributes(span.span_attributes)
                    else None,
                    freeplan_truncated=(
                        # the trace has been identified as truncated and the span is beyond the limit
                        self.freeplan_truncated
                        or (self.freeplan_truncated and trace.spans.index(span) > FREEPLAN_SPANS_LIST_LIMIT)
                    ),
                )
                for span in trace.spans
            ],
            freeplan_truncated=self.freeplan_truncated,
        )
