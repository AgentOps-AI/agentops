from typing import Any, Optional
from functools import cached_property
from decimal import Decimal
from datetime import datetime, date
import pydantic

from agentops.api.db.clickhouse.models import ClickhouseAggregatedModel, SelectFields, FilterFields
from agentops.api.models.traces import BaseTraceModel

from .span_metrics import SpanMetricsMixin, TraceMetricsMixin


class TraceCountsModel(BaseTraceModel):
    """
    Model representing the metrics for all of a user's projects.
    This model is used to generate aggregated metrics for projects.
    """

    project_id: str
    span_count: int
    trace_count: int

    @pydantic.model_validator(mode='before')
    @classmethod
    def fix_project_id(cls, values: dict[str, Any]) -> dict[str, Any]:
        """project_id_ comes from the query, but we want to use project_id."""
        values['project_id'] = values.get('project_id_')
        return values

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
        if fields or order_by or offset or limit or search:
            raise NotImplementedError("Custom fields, search, order_by, offset or limit are not supported.")

        where_clause, params = cls._get_where_clause(**(filters or {}))
        query = f"""
        SELECT
            any(project_id) as project_id_,  -- cannot reassign project_id
            count() as span_count,
            count(DISTINCT TraceId) as trace_count
        FROM {cls.table_name}
        {f"WHERE {where_clause}" if where_clause else ""}
        GROUP BY project_id
        """
        return query, params


class ProjectMetricsTraceModel(SpanMetricsMixin, BaseTraceModel):
    """
    Model representing a single span in the project metrics.

    This model extends the base TraceModel to include additional properties and methods
    for calculating token costs and other trace-related metrics.

    Incorporates SpanMetricsMixin to handle token calculations.
    """

    selectable_fields = {
        "TraceId": "trace_id",
        "Timestamp": "timestamp",
        "StatusCode": "status_code",
    }

    trace_id: str
    timestamp: datetime
    status_code: str

    # Add span count fields for aggregated metrics
    span_count: int = 1  # Number of spans in this trace
    success_span_count: int = 0
    fail_span_count: int = 0
    indeterminate_span_count: int = 0

    # Track if we have costs (either stored or calculable via model info)
    has_cached_costs: int = 0

    @pydantic.field_validator(
        'span_count',
        'success_span_count',
        'fail_span_count',
        'indeterminate_span_count',
        'has_cached_costs',
        mode='before',
    )
    @classmethod
    def ensure_span_counts_int(cls, v: Any) -> int:
        """Ensure that all counts are always an integer."""
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
        """
        Override to aggregate metrics at the database level instead of fetching all rows.
        This dramatically reduces data transfer and processing time.

        For costs: Uses stored costs when available, calculates on-the-fly for missing data.
        This preserves 100% accurate costs for new data while fixing historical gaps.
        """
        where_clause, params = cls._get_where_clause(**(filters or {}))

        # Instead of selecting individual rows, aggregate by trace
        # This processes ALL spans matching the filters but returns one row per trace
        query = f"""
        SELECT
            TraceId as trace_id,
            max(Timestamp) as timestamp,
            argMax(StatusCode, Timestamp) as status_code,
            count() as span_count,
            countIf(upper(StatusCode) = 'OK') as success_span_count,
            countIf(upper(StatusCode) = 'ERROR') as fail_span_count,
            countIf(upper(StatusCode) NOT IN ('OK', 'ERROR')) as indeterminate_span_count,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0'))) as prompt_tokens,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0'))) as completion_tokens,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.cache_read_input_tokens'], '0'))) as cache_read_input_tokens,
            sum(toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.reasoning_tokens'], '0'))) as reasoning_tokens,
            sum(
                if(
                    SpanAttributes['gen_ai.usage.total_tokens'] != '',
                    toUInt64OrZero(SpanAttributes['gen_ai.usage.total_tokens']),
                    toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0')) +
                    toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0')) +
                    toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.cache_read_input_tokens'], '0')) +
                    toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.reasoning_tokens'], '0'))
                )
            ) as cached_total_tokens,
            any(SpanAttributes['gen_ai.request.model']) as request_model,
            any(SpanAttributes['gen_ai.response.model']) as response_model,
            sum(
                if(
                    SpanAttributes['gen_ai.usage.prompt_cost'] != '',
                    toDecimal64OrZero(SpanAttributes['gen_ai.usage.prompt_cost'], 9),
                    toDecimal64(
                        calculate_prompt_cost(
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], '0')),
                            coalesce(
                                nullIf(SpanAttributes['gen_ai.response.model'], ''),
                                nullIf(SpanAttributes['gen_ai.request.model'], '')
                            )
                        ),
                        9
                    )
                )
            ) as cached_prompt_cost,
            sum(
                if(
                    SpanAttributes['gen_ai.usage.completion_cost'] != '',
                    toDecimal64OrZero(SpanAttributes['gen_ai.usage.completion_cost'], 9),
                    toDecimal64(
                        calculate_completion_cost(
                            toUInt64OrZero(ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], '0')),
                            coalesce(
                                nullIf(SpanAttributes['gen_ai.response.model'], ''),
                                nullIf(SpanAttributes['gen_ai.request.model'], '')
                            )
                        ),
                        9
                    )
                )
            ) as cached_completion_cost,
            cached_prompt_cost + cached_completion_cost as cached_total_cost,
            countIf(
                SpanAttributes['gen_ai.usage.prompt_cost'] != '' 
                OR SpanAttributes['gen_ai.usage.completion_cost'] != ''
                OR coalesce(
                    nullIf(SpanAttributes['gen_ai.response.model'], ''),
                    nullIf(SpanAttributes['gen_ai.request.model'], '')
                ) != ''
            ) as has_cached_costs
        FROM {cls.table_name}
        {f"WHERE {where_clause}" if where_clause else ""}
        GROUP BY TraceId
        ORDER BY timestamp DESC
        """

        return query, params


class ProjectMetricsDurationModel(BaseTraceModel):
    """
    Model representing the duration metrics for a project.

    This model is used to generate aggregated duration metrics for traces in a project.
    """

    min_duration: int
    max_duration: int
    avg_duration: int
    total_duration: int
    span_count: int
    trace_count: int
    start_time: datetime
    end_time: datetime

    @pydantic.field_validator(
        'min_duration',
        'max_duration',
        'avg_duration',
        'total_duration',
        'span_count',
        'trace_count',
        mode='before',
    )
    @classmethod
    def ensure_int(cls, v: Any) -> int:
        """Ensure that all token counts are always an integer."""
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
        query = f"""
        SELECT
            min(if(Duration > 0, Duration, null)) as min_duration,
            max(if(Duration > 0, Duration, null)) as max_duration,
            avg(if(Duration > 0, Duration, null)) as avg_duration,
            sum(if(Duration > 0, Duration, null)) as total_duration,
            count() as span_count,
            count(DISTINCT TraceId) as trace_count,
            min(Timestamp) as start_time,
            max(Timestamp) as end_time
        FROM {cls.table_name}
        {f"WHERE {where_clause}" if where_clause else ""}
        """
        return query, params


class ProjectMetricsTraceDurationsModel(BaseTraceModel):
    """
    Model representing the trace durations for a project.

    This is used for generating the graph that shows the duration of each trace.
    """

    trace_id: str
    trace_duration: int

    @pydantic.field_validator('trace_duration', mode='before')
    @classmethod
    def ensure_int(cls, v):
        """Ensure that trace_duration is always an integer."""
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
        query = f"""
        SELECT
            TraceId as trace_id,
            sum(Duration) as trace_duration
        FROM {cls.table_name}
        {f"WHERE {where_clause}" if where_clause else ""}
        GROUP BY TraceId
        ORDER BY trace_duration ASC
        """
        return query, params


class ProjectMetricsModel(TraceMetricsMixin, ClickhouseAggregatedModel):
    """
    Model representing aggregated project metrics, combining multiple Clickhouse models.

    This model aggregates trace metrics, duration metrics, and trace durations into a single
    response. It computes various summary statistics and provides properties for easy access to
    common metrics like average tokens and cost calculations.
    """

    aggregated_models = (
        ProjectMetricsTraceModel,
        ProjectMetricsDurationModel,
        ProjectMetricsTraceDurationsModel,
    )

    trace_metrics_field_name = "traces"

    traces: list[ProjectMetricsTraceModel] = pydantic.Field(default_factory=list)
    duration: ProjectMetricsDurationModel
    trace_durations: list[ProjectMetricsTraceDurationsModel] = pydantic.Field(default_factory=list)

    trace_cost_dates: dict[date, Decimal] = pydantic.Field(default_factory=dict)
    success_dates: list[datetime] = pydantic.Field(default_factory=list)
    fail_dates: list[datetime] = pydantic.Field(default_factory=list)
    indeterminate_dates: list[datetime] = pydantic.Field(default_factory=list)

    # Track if we have any cost data (stored or calculable) for proper display
    has_any_cached_costs: bool = False

    # Initialize parent class attributes
    span_count: int = 0
    trace_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    indeterminate_count: int = 0

    total_tokens: int = 0
    success_tokens: int = 0
    fail_tokens: int = 0

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_input_tokens: int = 0
    reasoning_tokens: int = 0

    prompt_cost: Decimal = Decimal(0)
    completion_cost: Decimal = Decimal(0)
    total_cost: Decimal = Decimal(0)

    def __init__(
        self,
        traces: list[ProjectMetricsTraceModel],
        durations: list[ProjectMetricsDurationModel],
        trace_durations: list[ProjectMetricsTraceDurationsModel],
    ) -> None:
        super().__init__(traces=traces, duration=durations[0], trace_durations=trace_durations)

    def model_post_init(self, __context) -> None:
        """Override to properly aggregate span counts from the aggregated trace data"""
        traces = getattr(self, self.trace_metrics_field_name)
        trace_ids: set[str] = set()

        # Reset counters
        self.span_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.indeterminate_count = 0

        for trace in traces:
            if not isinstance(trace, SpanMetricsMixin):
                raise ValueError(f"Provided trace object {trace} does not implement SpanMetricsMixin.")

            trace_ids.add(trace.trace_id)

            # Aggregate span counts from the pre-aggregated data
            self.span_count += trace.span_count
            self.success_count += trace.success_span_count
            self.fail_count += trace.fail_span_count
            self.indeterminate_count += trace.indeterminate_span_count

            # Check if any trace has cost data (stored or calculable)
            if hasattr(trace, 'has_cached_costs') and trace.has_cached_costs > 0:
                self.has_any_cached_costs = True

            # Token aggregation remains the same
            self.total_tokens += trace.total_tokens
            self.success_tokens += trace.success_tokens
            self.fail_tokens += trace.fail_tokens

            self.prompt_tokens += trace.prompt_tokens
            self.completion_tokens += trace.completion_tokens
            self.cache_read_input_tokens += trace.cache_read_input_tokens
            self.reasoning_tokens += trace.reasoning_tokens

            self.prompt_cost += trace.prompt_cost
            self.completion_cost += trace.completion_cost
            self.total_cost += trace.total_cost

            self._trace_metrics_additions(trace)

        self.trace_count = len(trace_ids)

    def _trace_metrics_additions(self, trace: ProjectMetricsTraceModel) -> None:
        """Compute additional trace metrics for a single trace instance."""
        if trace.success:
            self.success_dates.append(trace.timestamp)
            # TODO should trace_cost_dates only be on success?
            date_cost = self.trace_cost_dates.get(trace.timestamp.date(), Decimal(0.0))
            self.trace_cost_dates[trace.timestamp.date()] = date_cost + trace.total_cost
        elif trace.fail:
            self.fail_dates.append(trace.timestamp)
        else:
            self.indeterminate_dates.append(trace.timestamp)

    @cached_property
    def spans_per_trace(self) -> dict[int, int]:
        """Returns a distribution of the number of spans per trace."""
        spans_per_trace: dict[int, int] = {}
        trace_span_counts: dict[int, int] = {}

        # Use the span_count from each trace
        for trace in self.traces:
            count = trace.span_count
            trace_span_counts[count] = trace_span_counts.get(count, 0) + 1

        # Find max count for bucket creation
        if trace_span_counts:
            max_count = max(trace_span_counts.keys())
            increment = max(1, max_count // 10)

            for bucket_start in range(0, max_count + increment, increment):
                bucket_count = sum(
                    count
                    for span_count, count in trace_span_counts.items()
                    if bucket_start <= span_count < bucket_start + increment
                )
                if bucket_count:
                    spans_per_trace[bucket_start] = bucket_count

        return spans_per_trace
