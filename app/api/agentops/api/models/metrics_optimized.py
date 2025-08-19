from typing import Any, Optional
from functools import cached_property
from decimal import Decimal
from datetime import datetime, date
import pydantic

from agentops.api.db.clickhouse.models import ClickhouseAggregatedModel, SelectFields, FilterFields
from agentops.api.models.traces import BaseTraceModel
from agentops.api.models.metrics import (
    ProjectMetricsTraceModel,
    ProjectMetricsDurationModel,
)

from .span_metrics import TraceMetricsMixin


class TraceDurationWrapper(pydantic.BaseModel):
    """Simple wrapper to maintain compatibility with existing code expecting objects with trace_duration attribute"""

    trace_duration: int


class ProjectMetricsTraceDurationBucketsModel(BaseTraceModel):
    """
    Model representing trace duration histogram buckets for a project.
    Returns pre-aggregated histogram data instead of individual trace durations.
    """

    duration_bucket_ns: int
    bucket_count: int

    @pydantic.field_validator('duration_bucket_ns', 'bucket_count', mode='before')
    @classmethod
    def ensure_int(cls, v):
        """Ensure that values are always integers."""
        return int(v or 0)

    @classmethod
    def _get_select_query(
        cls,
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, dict[str, Any]]:
        if fields or search or order_by or offset or limit:
            raise NotImplementedError("Custom fields, search, order_by, offset or limit are not supported.")

        where_clause, params = cls._get_where_clause(**(filters or {}))

        # This query creates histogram buckets for trace durations
        # We use 20 logarithmic buckets for better distribution visualization
        query = f"""
        WITH trace_durations AS (
            SELECT 
                TraceId,
                toUInt64(sum(Duration)) as trace_duration
            FROM {cls.table_name}
            {f"WHERE {where_clause}" if where_clause else ""}
            GROUP BY TraceId
        ),
        duration_stats AS (
            SELECT 
                toUInt64(min(trace_duration)) as min_duration,
                toUInt64(max(trace_duration)) as max_duration,
                toUInt64(count()) as total_count
            FROM trace_durations
        )
        SELECT 
            CASE
                WHEN total_count = 0 THEN toUInt64(0)
                WHEN min_duration = max_duration THEN min_duration
                ELSE toUInt64(floor(
                    min_duration + (toFloat64(number) * toFloat64(max_duration - min_duration) / 20.0)
                ))
            END as duration_bucket_ns,
            toUInt64(countIf(
                trace_duration >= CASE
                    WHEN total_count = 0 THEN toUInt64(0)
                    WHEN min_duration = max_duration THEN min_duration
                    ELSE toUInt64(floor(min_duration + (toFloat64(number) * toFloat64(max_duration - min_duration) / 20.0)))
                END
                AND trace_duration < CASE
                    WHEN total_count = 0 THEN toUInt64(1)
                    WHEN min_duration = max_duration THEN min_duration + toUInt64(1)
                    ELSE toUInt64(floor(min_duration + (toFloat64(number + 1) * toFloat64(max_duration - min_duration) / 20.0)))
                END
            )) as bucket_count
        FROM 
            trace_durations,
            duration_stats,
            numbers(20) as number
        GROUP BY number, min_duration, max_duration, total_count
        ORDER BY duration_bucket_ns
        """
        return query, params


class ProjectMetricsDateAggregatedModel(BaseTraceModel):
    """
    Model representing date-aggregated success/fail/indeterminate counts.
    Returns counts by date instead of individual timestamps.
    """

    date: date
    success_count: int
    fail_count: int
    indeterminate_count: int
    total_cost: Decimal

    @pydantic.field_validator('success_count', 'fail_count', 'indeterminate_count', mode='before')
    @classmethod
    def ensure_int(cls, v):
        """Ensure that counts are always integers."""
        return int(v or 0)

    @pydantic.field_validator('total_cost', mode='before')
    @classmethod
    def ensure_decimal(cls, v):
        """Ensure that cost is always a Decimal."""
        if isinstance(v, str):
            return Decimal(v) if v else Decimal(0)
        return Decimal(str(v)) if v else Decimal(0)

    @classmethod
    def _get_select_query(
        cls,
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, dict[str, Any]]:
        if fields or search or order_by or offset or limit:
            raise NotImplementedError("Custom fields, search, order_by, offset or limit are not supported.")

        where_clause, params = cls._get_where_clause(**(filters or {}))

        # Aggregate by trace first, then by date
        query = f"""
        WITH trace_aggregates AS (
            SELECT 
                TraceId,
                toDate(max(Timestamp)) as trace_date,
                argMax(StatusCode, Timestamp) as trace_status,
                sum(toDecimal64OrZero(ifNull(SpanAttributes['gen_ai.usage.total_cost'], '0'), 9)) as trace_cost
            FROM {cls.table_name}
            {f"WHERE {where_clause}" if where_clause else ""}
            GROUP BY TraceId
        )
        SELECT 
            trace_date as date,
            countIf(upper(trace_status) = 'OK') as success_count,
            countIf(upper(trace_status) = 'ERROR') as fail_count,
            countIf(upper(trace_status) NOT IN ('OK', 'ERROR')) as indeterminate_count,
            sum(trace_cost) as total_cost
        FROM trace_aggregates
        GROUP BY trace_date
        ORDER BY trace_date
        """
        return query, params


class ProjectMetricsOptimizedModel(TraceMetricsMixin, ClickhouseAggregatedModel):
    """
    Optimized model for project metrics that reduces data transfer by aggregating at the database level.
    """

    aggregated_models = (
        ProjectMetricsTraceModel,  # Keep existing trace model for token metrics
        ProjectMetricsDurationModel,  # Keep existing duration model
        ProjectMetricsTraceDurationBucketsModel,  # New: histogram buckets instead of all durations
        ProjectMetricsDateAggregatedModel,  # New: date aggregated counts instead of timestamps
    )

    trace_metrics_field_name = "traces"

    traces: list[ProjectMetricsTraceModel] = pydantic.Field(default_factory=list)
    duration: ProjectMetricsDurationModel
    trace_duration_buckets: list[ProjectMetricsTraceDurationBucketsModel] = pydantic.Field(
        default_factory=list
    )
    date_aggregates: list[ProjectMetricsDateAggregatedModel] = pydantic.Field(default_factory=list)

    # Keep these for compatibility but they'll be populated differently
    trace_cost_dates: dict[date, Decimal] = pydantic.Field(default_factory=dict)
    success_dates: list[datetime] = pydantic.Field(default_factory=list)
    fail_dates: list[datetime] = pydantic.Field(default_factory=list)
    indeterminate_dates: list[datetime] = pydantic.Field(default_factory=list)
    trace_durations: list[TraceDurationWrapper] = pydantic.Field(default_factory=list)

    def __init__(
        self,
        traces: list[ProjectMetricsTraceModel],
        durations: list[ProjectMetricsDurationModel],
        trace_duration_buckets: list[ProjectMetricsTraceDurationBucketsModel],
        date_aggregates: list[ProjectMetricsDateAggregatedModel],
    ) -> None:
        # Call parent with modified signature
        super(ClickhouseAggregatedModel, self).__init__(
            traces=traces,
            duration=durations[0],
            trace_duration_buckets=trace_duration_buckets,
            date_aggregates=date_aggregates,
        )

    def model_post_init(self, __context) -> None:
        """Override to use aggregated data instead of computing from individual traces"""
        # Call parent to handle token aggregation from traces
        super().model_post_init(__context)

        # Process date aggregates to populate date arrays
        for agg in self.date_aggregates:
            # Create datetime objects for each occurrence
            dt = datetime.combine(agg.date, datetime.min.time())

            # Add timestamps for each count
            for _ in range(agg.success_count):
                self.success_dates.append(dt)
            for _ in range(agg.fail_count):
                self.fail_dates.append(dt)
            for _ in range(agg.indeterminate_count):
                self.indeterminate_dates.append(dt)

            # Add to trace cost dates
            if agg.total_cost > 0:
                self.trace_cost_dates[agg.date] = agg.total_cost

        # Convert histogram buckets to trace durations list
        # This maintains compatibility with the frontend
        for bucket in self.trace_duration_buckets:
            # Add representative durations for each bucket
            for _ in range(bucket.bucket_count):
                self.trace_durations.append(TraceDurationWrapper(trace_duration=bucket.duration_bucket_ns))

    @cached_property
    def spans_per_trace(self) -> dict[int, int]:
        """Returns a distribution of the number of spans per trace."""
        # This can be optimized further in a future iteration
        # For now, use the existing implementation
        spans_per_trace: dict[int, int] = {}
        trace_spans: dict[str, int] = {}

        for trace in self.traces:
            trace_spans[trace.trace_id] = trace_spans.get(trace.trace_id, 0) + 1

        trace_counts = trace_spans.values()
        max_count = max(trace_counts) if trace_counts else 0

        if max_count > 0:
            increment = max_count // 10
            if increment < 1:
                increment = 1
            for index in range(0, max_count + increment, increment):
                count = sum(
                    1 for count in trace_spans.values() if count >= index and count < index + increment
                )
                if count:
                    spans_per_trace[index] = count

        return spans_per_trace
