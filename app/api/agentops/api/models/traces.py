from typing import Any, Optional, Type
from datetime import datetime, timedelta, timezone
import json
import pydantic
from decimal import Decimal

from agentops.api.db.clickhouse.models import (
    ClickhouseModel,
    TClickhouseModel,
    ClickhouseAggregatedModel,
    SelectFields,
    FilterFields,
    WithinListOperation,
)

from .span_metrics import SpanMetricsMixin, TraceMetricsMixin


TRACE_STATUS_OK = "OK"
TRACE_STATUS_ERROR = "ERROR"


def nanosecond_timedelta(ns: int) -> timedelta:
    """Return a timedelta object from nanoseconds."""
    seconds = ns // 1_000_000_000
    microseconds = (ns % 1_000_000_000) // 1000  # Convert remaining ns to μs
    return timedelta(seconds=seconds, microseconds=microseconds)


class BaseTraceModel(ClickhouseModel):
    """
    BaseTraceModel is a base model for the trace data in Clickhouse.

    This model defines the structure of the trace data and is used to interact with
    the `otel_traces` table in Clickhouse.

    This class is inherited from by other models that interact with the `otel_traces`
    table, so it is kept free of attributes to allow them to be defined for each use case.

    Field lookups and filters are common to all models that interact with this table,
    so they are shared here in this base class.
    """

    table_name = "otel_traces"
    selectable_fields = {
        'Timestamp': "timestamp",
        'project_id': "project_id",
        'TraceId': "trace_id",
        'SpanId': "span_id",
        'ParentSpanId': "parent_span_id",
        'TraceState': "trace_state",
        'SpanName': "span_name",
        'SpanKind': "span_kind",
        'ServiceName': "service_name",
        'ResourceAttributes': "resource_attributes",
        'ScopeName': "scope_name",
        'ScopeVersion': "scope_version",
        'SpanAttributes': "span_attributes",
        "SpanAttributes['agentops.tags']": "tags",
        'Duration': "duration",
        'StatusCode': "status_code",
        'StatusMessage': "status_message",
        'Events.Timestamp': "event_timestamps",
        'Events.Name': "event_names",
        'Events.Attributes': "event_attributes",
        'Links.TraceId': "link_trace_ids",
        'Links.SpanId': "link_span_ids",
        'Links.TraceState': "link_trace_states",
        'Links.Attributes': "link_attributes",
    }
    filterable_fields = {
        "trace_id": ("=", "TraceId"),
        "span_id": ("=", "SpanId"),
        "parent_span_id": ("=", "ParentSpanId"),
        "project_id": ("=", "project_id"),
        "project_ids": (WithinListOperation, "project_id"),
        "start_time": (">=", "Timestamp"),
        "end_time": ("<=", "Timestamp"),
    }

    @pydantic.field_validator('status_code', check_fields=False, mode='before')
    @classmethod
    def uppercase_status(cls, v: str) -> str:
        """Ensure status_code is always uppercase (if it is present)."""
        return v.upper()

    @pydantic.field_validator('tags', check_fields=False, mode='before')
    @classmethod
    def parse_tags_json(cls, value: str) -> list[str]:
        """Parse the tags JSON string into a list of tags."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []


class SpanModel(SpanMetricsMixin, BaseTraceModel):
    """
    SpanModel represents a single span within a trace. This model is used to retrieve
    span data from the `otel_traces` table in Clickhouse.

    Incorporates `SpanMetricsMixin` to handle token calculations.
    """

    project_id: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None

    timestamp: datetime
    duration: int
    status_code: str
    status_message: Optional[str] = None

    trace_state: Optional[str] = None
    span_name: Optional[str] = None
    span_kind: Optional[str] = None
    service_name: Optional[str] = None
    scope_name: Optional[str] = None
    scope_version: Optional[str] = None
    tags: Optional[list[str]] = pydantic.Field(default_factory=list)

    resource_attributes: dict[str, Any]
    span_attributes: dict[str, Any]

    event_timestamps: list[datetime] = pydantic.Field(default_factory=list)
    event_names: list[str] = pydantic.Field(default_factory=list)
    event_attributes: list[Any] = pydantic.Field(default_factory=list)

    link_trace_ids: list[str] = pydantic.Field(default_factory=list)
    link_span_ids: list[str] = pydantic.Field(default_factory=list)
    link_trace_states: list[str] = pydantic.Field(default_factory=list)
    link_attributes: list[Any] = pydantic.Field(default_factory=list)

    @property
    def start_time(self) -> datetime:
        """start_time property returns the timestamp of the span."""
        return self.timestamp.astimezone(timezone.utc)

    @property
    def end_time(self) -> datetime:
        """Determine the end time of the span based on the start time and duration."""
        return self.start_time + nanosecond_timedelta(self.duration)


class TraceModel(TraceMetricsMixin, ClickhouseAggregatedModel):
    """
    TraceModel is an aggregate model that actually only queries one model, but
    having the aggregate as a parent gives us a place to store the trace metrics.
    """

    aggregated_models = (SpanModel,)

    trace_metrics_field_name = "spans"

    spans: list[SpanModel] = pydantic.Field(default_factory=list)

    def __init__(self, spans: list[SpanModel]) -> None:
        super().__init__(
            spans=spans,
        )

    @property
    def trace_id(self) -> str:
        """
        Get the trace ID for this group of spans.
        Validates that all spans in the trace have the same trace ID (they always
        should) and returns it.
        """
        trace_ids = {span.trace_id for span in self.spans}
        assert len(trace_ids) == 1, "All spans in a trace are expected to have the same trace_id"
        return trace_ids.pop()

    @property
    def project_id(self) -> str:
        """
        Get the project ID for this group of spans.

        Validates that all spans in the trace have the same project ID (they
        always should) and returns it.
        """
        project_ids = {span.project_id for span in self.spans}
        assert len(project_ids) == 1, "All spans in a trace are expected to have the same project_id"
        return project_ids.pop()

    @property
    def start_time(self) -> datetime:
        """Get the start time of the trace from the first span."""
        return min(span.start_time for span in self.spans)

    @property
    def end_time(self) -> datetime:
        """Get the end time of the trace from the last span."""
        return max(span.end_time for span in self.spans)

    @property
    def tags(self) -> list[str]:
        """Get tags from the root span."""
        # the SDK currently only sets tags on the root span and we always have at least one span
        return self.spans[0].tags


class TraceSummaryModel(BaseTraceModel):
    """
    TraceListModel represents a summary of traces in Clickhouse grouped by `trace_id`.

    This model is used to interact with the `otel_traces` table in Clickhouse to retrieve
    a list of traces with summary information suitable for use in a list view.
    """

    filterable_fields = {
        "project_id": ("=", "project_id"),
        "start_time": (">=", "Timestamp"),
        "end_time": ("<=", "Timestamp"),
    }
    searchable_fields = {
        # searchable field should reference the alias we create in the sub-select
        "trace_id": ("ILIKE", "trace_id"),
        "span_name": ("ILIKE", "span_name"),
        "tags": ("ILIKE", "tags"),
    }

    trace_id: str
    service_name: Optional[str] = None
    span_name: Optional[str] = None
    start_time: datetime
    duration: int
    span_count: int
    error_count: int
    tags: Optional[list[str]] = pydantic.Field(default_factory=list)
    total_cost: Optional[float] = None

    @pydantic.field_validator('start_time', mode='before')
    def datetime_with_timezone(cls, v: datetime) -> datetime:
        """Ensure the start_time is formatted as ISO strings."""
        return v.astimezone(timezone.utc)

    @property
    def end_time(self) -> datetime:
        """Determine the end time of the span based on the start time and duration."""
        return self.start_time + nanosecond_timedelta(self.duration)

    @classmethod
    def _get_select_query(
        cls: Type[TClickhouseModel],
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: str = "start_time ASC",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[str, dict[str, Any]]:
        if fields:
            raise NotImplementedError("`TraceListModel.select` does not support `fields`")

        where_clause, where_params = cls._get_where_clause(**(filters or {}))
        having_clause, having_params = cls._get_search_clause(search)
        params = {**where_params, **having_params}

        # we use `argMin` on the aggregation because we can assume that the oldest
        # span is the root span
        query = f"""
        WITH traces AS
        (
            SELECT
                TraceId as trace_id,
                any(ServiceName) AS service_name,
                argMin(SpanName, Timestamp) AS span_name,
                argMin(SpanAttributes['agentops.tags'], Timestamp) AS tags,
                -- Calculate wall-clock duration instead of summing individual span durations
                min(Timestamp) AS start_time,
                -- Use the difference between the earliest span start and the latest span start to approximate total elapsed time in nanoseconds
                dateDiff('nanosecond', min(Timestamp), max(Timestamp)) AS duration,
                count() AS span_count,
                countIf(upper(StatusCode) = '{TRACE_STATUS_ERROR}') AS error_count,
                -- Sum up total cost from all spans in the trace
                -- Use hybrid approach: stored costs when available, calculated costs otherwise
                sum(
                    if(
                        SpanAttributes['gen_ai.usage.total_cost'] != '',
                        toFloat64OrZero(SpanAttributes['gen_ai.usage.total_cost']),
                        toFloat64(
                            calculate_prompt_cost(
                                toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0')),
                                coalesce(
                                    nullIf(SpanAttributes['gen_ai.response.model'], ''),
                                    nullIf(SpanAttributes['gen_ai.request.model'], '')
                                )
                            ) + calculate_completion_cost(
                                toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0')),
                                coalesce(
                                    nullIf(SpanAttributes['gen_ai.response.model'], ''),
                                    nullIf(SpanAttributes['gen_ai.request.model'], '')
                                )
                            )
                        )
                    )
                ) AS total_cost
            FROM {cls.table_name}
            {f"WHERE {where_clause}" if where_clause else ""}
            GROUP BY trace_id
        )
        SELECT *
        FROM traces
        {f"HAVING {having_clause}" if having_clause else ""}
        ORDER BY {order_by}
        LIMIT {limit}
        OFFSET {offset}
        """
        return query, params


class TraceListMetricsModel(SpanMetricsMixin, BaseTraceModel):
    """
    Returns statistics related to trace counts for a given project. This model is used to
    interact with the `otel_traces` table in Clickhouse to retrieve aggregate trace counts
    for use in supporting a trace list view.

    Note that while the `TraceSummaryModel` this is paired with returns a subset of the
    available traces, this model references all applicable traces (based on the shared
    filters) and can be used to display the metrics for the entire dataset.

    Implements hybrid cost calculation: uses stored costs when available, calculates
    on-the-fly for historical data. This approach was inspired by FoxyAI's needs.
    """

    selectable_fields = {
        "TraceId": "trace_id",
        'StatusCode': "status_code",
    }
    filterable_fields = {
        "project_id": ("=", "project_id"),
        "start_time": (">=", "Timestamp"),
        "end_time": ("<=", "Timestamp"),
        "span_name": ("ILIKE", "SpanName"),
    }
    searchable_fields = {
        # searchable field should reference the columns in the table
        "trace_id": ("ILIKE", "TraceId"),
        "span_name": ("ILIKE", "SpanName"),
        "tags": ("ILIKE", "SpanAttributes['agentops.tags']"),
    }

    # Add aggregated fields
    trace_id: str
    status_code: str
    span_count: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_input_tokens: int = 0
    reasoning_tokens: int = 0
    cached_total_cost: Decimal = Decimal(0)

    @pydantic.field_validator(
        'span_count',
        'prompt_tokens',
        'completion_tokens',
        'cache_read_input_tokens',
        'reasoning_tokens',
        mode='before',
    )
    @classmethod
    def ensure_int(cls, v: Any) -> int:
        """Ensure that all counts are always an integer."""
        return int(v or 0)

    @pydantic.field_validator('cached_total_cost', mode='before')
    @classmethod
    def ensure_decimal(cls, v: Any) -> Decimal:
        """Ensure that cost is always a Decimal."""
        if isinstance(v, str):
            return Decimal(v) if v else Decimal(0)
        return Decimal(str(v)) if v else Decimal(0)

    @classmethod
    def _get_select_query(
        cls: Type[TClickhouseModel],
        *,
        fields: Optional[SelectFields] = None,
        filters: Optional[FilterFields] = None,
        search: Optional[str] = None,
        order_by: str = "start_time ASC",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[str, dict[str, Any]]:
        """
        Aggregate trace metrics at the database level for performance.

        For costs: Uses stored total_cost when available, calculates on-the-fly for missing data.
        This preserves 100% accurate costs for new data while fixing historical gaps.
        """
        if fields:
            raise NotImplementedError("`TraceListMetricsModel.select` does not support `fields`")

        # Get the where clause from parent
        where_clause, params = cls._get_where_clause(**(filters or {}))

        # Apply search conditions if provided
        if search:
            search_conditions = []
            search_value = f"%{search}%"
            for field, (operator, column) in cls.searchable_fields.items():
                if operator == "ILIKE":
                    search_conditions.append(f"{column} ILIKE %(search_{field})s")
                    params[f"search_{field}"] = search_value

            if search_conditions:
                search_clause = f"({' OR '.join(search_conditions)})"
                where_clause = f"{where_clause} AND {search_clause}" if where_clause else search_clause

        # Aggregate by trace at the database level - this is the key optimization
        query = f"""
        SELECT
            TraceId as trace_id,
            argMax(StatusCode, Timestamp) as status_code,
            count() as span_count,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0'))) as prompt_tokens,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0'))) as completion_tokens,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.cache_read_input_tokens'], '0'))) as cache_read_input_tokens,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.reasoning_tokens'], '0'))) as reasoning_tokens,
            any(SpanAttributes['gen_ai.request.model']) as request_model,
            any(SpanAttributes['gen_ai.response.model']) as response_model,
            sum(
                if(
                    SpanAttributes['gen_ai.usage.total_cost'] != '',
                    toDecimal64OrZero(SpanAttributes['gen_ai.usage.total_cost'], 9),
                    toDecimal64(
                        calculate_prompt_cost(
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0')),
                            coalesce(
                                nullIf(SpanAttributes['gen_ai.response.model'], ''),
                                nullIf(SpanAttributes['gen_ai.request.model'], '')
                            )
                        ) + calculate_completion_cost(
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0')),
                            coalesce(
                                nullIf(SpanAttributes['gen_ai.response.model'], ''),
                                nullIf(SpanAttributes['gen_ai.request.model'], '')
                            )
                        ),
                        9
                    )
                )
            ) as cached_total_cost
        FROM {cls.table_name}
        {f"WHERE {where_clause}" if where_clause else ""}
        GROUP BY TraceId
        """

        return query, params


class TraceListModel(TraceMetricsMixin, ClickhouseAggregatedModel):
    """
    TraceListModel is an aggregate model that combines the results of `TraceSummaryModel`
    and `TraceListMetricsModel` to provide a list of traces matching the user query
    for a subset of traces, along with aggregate metrics for the entire trace set.
    """

    aggregated_models = (
        TraceSummaryModel,
        TraceListMetricsModel,
    )

    trace_metrics_field_name = "metrics_traces"

    traces: list[TraceSummaryModel] = pydantic.Field(default_factory=list)
    metrics_traces: list[TraceListMetricsModel] = pydantic.Field(default_factory=list)

    def __init__(self, traces: list[TraceSummaryModel], metrics_traces: list[TraceListMetricsModel]) -> None:
        super().__init__(
            traces=traces,
            metrics_traces=metrics_traces,
        )
