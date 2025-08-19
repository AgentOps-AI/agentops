from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import Depends, Query, HTTPException
import hashlib

from agentops.common.environment import APP_URL, FREEPLAN_METRICS_DAYS_CUTOFF
from agentops.common.route_config import BaseView
from agentops.common.views import add_cors_headers
from agentops.common.orm import get_orm_session, Session
from agentops.common.freeplan import freeplan_clamp_start_time, freeplan_clamp_end_time

from agentops.opsboard.models import ProjectModel
from agentops.api.models.metrics import ProjectMetricsModel

from .responses import (
    ProjectMetricsResponse,
    SpanCount,
    TotalTokens,
    AverageTokens,
    TokenMetrics,
    DurationMetrics,
)


# Simple in-memory cache with TTL
from time import time


class MetricsCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self._cache = {}
        self._ttl = ttl_seconds

    def _make_key(self, project_id: str, start_time: Optional[datetime], end_time: Optional[datetime]) -> str:
        """Create a cache key from parameters"""
        key_parts = [
            project_id,
            start_time.isoformat() if start_time else "none",
            end_time.isoformat() if end_time else "none",
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, project_id: str, start_time: Optional[datetime], end_time: Optional[datetime]):
        """Get cached value if not expired"""
        key = self._make_key(project_id, start_time, end_time)
        if key in self._cache:
            cached_data, cached_time = self._cache[key]
            if time() - cached_time < self._ttl:
                return cached_data
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None

    def set(self, project_id: str, start_time: Optional[datetime], end_time: Optional[datetime], data):
        """Set cache value with current timestamp"""
        key = self._make_key(project_id, start_time, end_time)
        self._cache[key] = (data, time())

        # Simple cleanup - remove old entries if cache gets too large
        if len(self._cache) > 1000:
            # Remove oldest 100 entries
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:100]:
                del self._cache[key]


# Global cache instance
metrics_cache = MetricsCache(ttl_seconds=300)  # 5 minute cache


class ProjectMetricsView(BaseView):
    """
    View class for handling the project metrics endpoint. This class encapsulates
    the logic for retrieving and formatting project metrics data.
    """

    orm: Session
    project: ProjectModel
    freeplan_truncated: bool = False

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
            None,
            description="Filter by start time (ISO 8601 format, e.g., '2023-01-01T00:00:00Z')",
        ),
        end_time: Optional[datetime] = Query(
            None,
            description="Filter by end time (ISO 8601 format, e.g., '2023-01-01T00:00:00Z')",
        ),
    ) -> ProjectMetricsResponse:
        """
        Callable method to handle the request and return a JSONResponse. This method
        validates the input parameters, retrieves the metrics data, formats the
        response and converts exceptions to responses.
        """
        self.orm = orm
        self.project = await self.get_project(project_id)

        # Normalize time parameters for caching
        normalized_start = self.get_start_time(start_time)
        normalized_end = self.get_end_time(end_time)

        # Check cache first
        cached_response = metrics_cache.get(project_id, normalized_start, normalized_end)
        if cached_response is not None:
            # Return cached response with freeplan_truncated flag
            cached_response.freeplan_truncated = self.freeplan_truncated
            return cached_response

        metrics = await ProjectMetricsModel.select(
            filters={
                'project_id': self.project.id,
                'start_time': normalized_start,
                'end_time': normalized_end,
            }
        )

        # TODO handle empty response
        response = await self.get_response(metrics)

        # Cache the response
        metrics_cache.set(project_id, normalized_start, normalized_end, response)

        return response

    def get_start_time(self, start_time: Optional[datetime]) -> Optional[datetime]:
        """Validates and formats the start_time parameter with freeplan handling."""
        if self.project.is_freeplan:
            start_time, modified = freeplan_clamp_start_time(start_time, FREEPLAN_METRICS_DAYS_CUTOFF)
            self.freeplan_truncated |= modified

        return start_time

    def get_end_time(self, end_time: Optional[datetime]) -> Optional[datetime]:
        """Validates and formats the end_time parameter with freeplan handling."""
        if self.project.is_freeplan:
            end_time, modified = freeplan_clamp_end_time(end_time, FREEPLAN_METRICS_DAYS_CUTOFF)
            self.freeplan_truncated |= modified

        return end_time

    async def get_project(self, project_id: str | UUID) -> ProjectModel:
        project = ProjectModel.get_by_id(self.orm, project_id)

        if not project or not project.org.is_user_member(self.request.state.session.user_id):
            raise HTTPException(status_code=404, detail="Project not found")

        return project

    async def get_response(self, metrics: ProjectMetricsModel) -> ProjectMetricsResponse:
        """
        Loads an aggregated collection of trace metrics data for a given project.

        `ProjectMetricsModel` handles retrieving and aggregating the data from the
        databases, as well as performing calculations and normalizing the data
        (normalizing meaning it will always return the expected types).

        The response types format the data in a suitable format for the frontend
        and handle all serialization.
        """

        return ProjectMetricsResponse(
            project_id=self.project.id,
            trace_count=metrics.duration.trace_count,
            start_time=metrics.duration.start_time,
            end_time=metrics.duration.end_time,
            span_count=SpanCount(
                total=metrics.span_count,
                success=metrics.success_count,
                fail=metrics.fail_count,
                unknown=metrics.indeterminate_count,
                indeterminate=metrics.indeterminate_count,
            ),
            token_metrics=TokenMetrics(
                total_cost=metrics.total_cost,
                average_cost_per_session=metrics.average_cost_per_trace,
                prompt_tokens=metrics.prompt_tokens,
                completion_tokens=metrics.completion_tokens,
                cache_read_input_tokens=metrics.cache_read_input_tokens,
                reasoning_tokens=metrics.reasoning_tokens,
                total_tokens=TotalTokens(
                    all=metrics.total_tokens,
                    success=metrics.success_tokens,
                    fail=metrics.fail_tokens,
                ),
                avg_tokens=AverageTokens(
                    all=metrics.avg_tokens,
                    success=metrics.avg_success_tokens,
                    fail=metrics.avg_fail_tokens,
                ),
            ),
            duration_metrics=DurationMetrics(
                min_duration_ns=metrics.duration.min_duration,
                max_duration_ns=metrics.duration.max_duration,
                avg_duration_ns=metrics.duration.avg_duration,
                total_duration_ns=metrics.duration.total_duration,
                trace_durations=[td.trace_duration for td in metrics.trace_durations],
            ),
            success_datetime=metrics.success_dates,
            fail_datetime=metrics.fail_dates,
            indeterminate_datetime=metrics.indeterminate_dates,
            trace_durations=[td.trace_duration for td in metrics.trace_durations],
            spans_per_trace=metrics.spans_per_trace,
            trace_cost_dates=metrics.trace_cost_dates,
            freeplan_truncated=self.freeplan_truncated,
        )
