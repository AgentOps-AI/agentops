from typing import ClassVar, Type, Any, Optional, Literal
from decimal import Decimal
from functools import cached_property
import pydantic
from tokencost import costs  # type: ignore
from agentops.api.db.clickhouse.models import (
    ClickhouseModel,
    ClickhouseAggregatedModel,
    SelectFields,
)

# from .traces import (
#     TRACE_STATUS_OK,
#     TRACE_STATUS_ERROR,
# )
# TODO circ import
TRACE_STATUS_OK = "OK"
TRACE_STATUS_ERROR = "ERROR"

# hax to relate model names to their entries in `tokencost`
MODEL_LOOKUP_ALIASES = {
    "sonar-pro": "perplexity/sonar-pro",
    "sonar": "perplexity/sonar",
}


def _format_cost(value: Decimal) -> str:
    """Helper function to format a Decimal cost to a string with 7 decimal places."""
    # 7 decimal places has been observed to be adequately precise.
    return f"{float(value):.7f}"


class SpanMetricsResponse(pydantic.BaseModel):
    """
    Shared metrics response type for spans.
    """

    total_tokens: int

    prompt_tokens: int
    completion_tokens: int
    cache_read_input_tokens: int
    reasoning_tokens: int

    success_tokens: int
    fail_tokens: int
    indeterminate_tokens: int

    prompt_cost: str
    completion_cost: str
    total_cost: str

    @pydantic.field_validator('prompt_cost', 'completion_cost', 'total_cost', mode='before')
    @classmethod
    def format_cost(cls, v: Decimal) -> str:
        return _format_cost(v)

    @classmethod
    def from_span_with_metrics(
        cls: Type['SpanMetricsResponse'],
        span: 'SpanMetricsMixin',
    ) -> 'SpanMetricsResponse':
        """
        Create a SpanMetricsResponse from a SpanMetricsMixin instance.
        """
        return cls(
            total_tokens=span.total_tokens,
            prompt_tokens=span.prompt_tokens,
            completion_tokens=span.completion_tokens,
            cache_read_input_tokens=span.cache_read_input_tokens,
            reasoning_tokens=span.reasoning_tokens,
            success_tokens=span.success_tokens,
            fail_tokens=span.fail_tokens,
            indeterminate_tokens=span.indeterminate_tokens,
            # ignore these type errors because a conversion happens with field_validator
            prompt_cost=span.prompt_cost,  # type: ignore
            completion_cost=span.completion_cost,  # type: ignore
            total_cost=span.total_cost,  # type: ignore
        )


class SpanMetricsMixin(ClickhouseModel):
    status_code: str  # base models must populate status_code
    trace_id: str  # required for trace identification

    request_model: Optional[str]
    response_model: Optional[str]

    prompt_tokens: int
    completion_tokens: int
    cache_read_input_tokens: int
    reasoning_tokens: int
    cached_total_tokens: Optional[int] = None

    cached_prompt_cost: Optional[Decimal] = None
    cached_completion_cost: Optional[Decimal] = None
    cached_total_cost: Optional[Decimal] = None

    @classmethod
    def _get_select_clause(
        cls: Type['SpanMetricsMixin'],
        *,
        fields: Optional[SelectFields] = None,
    ) -> str:
        """Append additional metrics to the base model's selects."""
        select_clause = super(SpanMetricsMixin, cls)._get_select_clause(fields=fields)
        select_clause = f"{select_clause}, " if select_clause else ""

        # NOTE previously we queried `llm.model` and `gent_ai.model` but it didn't
        # seems like we had any data that actually contained that so it has been removed.
        return f"""
        {select_clause}
        ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], 0) as prompt_tokens,
        ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], 0) as completion_tokens,
        ifNull(SpanAttributes['gen_ai.usage.cache_read_input_tokens'], 0) as cache_read_input_tokens,
        ifNull(SpanAttributes['gen_ai.usage.reasoning_tokens'], 0) as reasoning_tokens,
        SpanAttributes['gen_ai.usage.total_tokens'] as cached_total_tokens,
        SpanAttributes['gen_ai.request.model'] as request_model,
        SpanAttributes['gen_ai.response.model'] as response_model,
        SpanAttributes['gen_ai.usage.prompt_cost'] as cached_prompt_cost,
        SpanAttributes['gen_ai.usage.completion_cost'] as cached_completion_cost,
        SpanAttributes['gen_ai.usage.total_cost'] as cached_total_cost
        """

    @pydantic.field_validator(
        'prompt_tokens',
        'completion_tokens',
        'cache_read_input_tokens',
        'reasoning_tokens',
        mode='before',
    )
    @classmethod
    def ensure_int(cls, v: Any) -> int:
        """Ensure that all token counts are always an integer."""
        return int(v or 0)

    @pydantic.field_validator('cached_total_tokens', mode='before')
    @classmethod
    def ensure_int_or_none(cls, v: Any) -> Optional[int]:
        """Ensure token counts are int when present."""
        if v is None or v == "":
            return None

        return int(v)

    @pydantic.field_validator(
        'cached_prompt_cost',
        'cached_completion_cost',
        'cached_total_cost',
        mode='before',
    )
    @classmethod
    def ensure_decimal(cls, v: Any) -> Optional[Decimal]:
        """Ensure that cached costs are always a Decimal."""
        if v is None:
            return None

        if isinstance(v, Decimal):
            return v  # Already a Decimal, return as-is

        if isinstance(v, str) and v:  # filter empty strings
            return Decimal(v)

        if isinstance(v, (int, float)):
            return Decimal(str(v))  # convert to string to avoid float precision issues

        return None

    @pydantic.field_validator('trace_id', 'status_code', mode='before')
    @classmethod
    def ensure_required(cls, v: Any) -> Any:
        """Ensure that the trace_id and status_code are always present."""
        if not v:
            raise ValueError(f"Required field cannot be empty: {cls.__name__}.{v}")
        return v

    @property
    def success(self) -> bool:
        """Indicates whether the trace was successful based on its status code."""
        return self.status_code == TRACE_STATUS_OK

    @property
    def fail(self) -> bool:
        """Indicates whether the trace failed based on its status code."""
        return self.status_code == TRACE_STATUS_ERROR

    @property
    def indeterminate(self) -> bool:
        """Indicates whether the trace is indeterminate (i.e., not successful or failed)."""
        return self.status_code not in (TRACE_STATUS_OK, TRACE_STATUS_ERROR)

    @cached_property  # this might actually be slower
    def total_tokens(self) -> int:
        """
        Returns the total tokens used in the span. This is the sum of all token types.
        """
        if self.cached_total_tokens is not None:
            # if the SDK has populated this value, assume it's correct.
            return self.cached_total_tokens

        return (
            self.prompt_tokens + self.completion_tokens + self.cache_read_input_tokens + self.reasoning_tokens
        )

    @property
    def success_tokens(self) -> int:
        """Number of successful tokens."""
        return self.total_tokens if self.success else 0

    @property
    def fail_tokens(self) -> int:
        """Number of failed tokens."""
        return self.total_tokens if self.fail else 0

    @property
    def indeterminate_tokens(self) -> int:
        """Number of indeterminate tokens."""
        return self.total_tokens if self.indeterminate else 0

    @property
    def model_for_cost(self) -> Optional[str]:
        """Get the best available model for calculating costs."""
        model_name: Optional[str] = None

        if self.response_model:
            # often we have both a request and a response model set, in this case
            # the response model will have been converted by the provider SDK to
            # include specifics about it's release version.
            model_name = self.response_model
        else:
            # otherwise return the request model which is essentially user input,
            # or `None` if there is no model information.
            model_name = self.request_model

        # sometimes we have see model names that don't correspond to the records
        # in `tokencost` so we convert them here.
        if model_name in MODEL_LOOKUP_ALIASES:
            model_name = MODEL_LOOKUP_ALIASES[model_name]

        return model_name

    @cached_property
    def prompt_cost(self) -> Decimal:
        """The cost of the prompt based on the tokens and model used."""
        # TODO we need to incorporate cached tokens where they apply.
        if self.cached_prompt_cost is not None:
            # precalculated cost from the collector
            return self.cached_prompt_cost

        return self._calculate_cost(self.prompt_tokens, "input")

    @cached_property
    def completion_cost(self) -> Decimal:
        """The cost of the completion based on the tokens and model used."""
        # TODO we need to incorporate reasoning tokens where they apply.
        if self.cached_completion_cost is not None:
            # precalculated cost from the collector
            return self.cached_completion_cost

        return self._calculate_cost(self.completion_tokens, "output")

    @property
    def total_cost(self) -> Decimal:
        """Returns the total cost of the trace, which is the sum of the prompt and completion costs."""
        if self.cached_total_cost is not None:
            # precalculated cost from the SDK
            return self.cached_total_cost

        return self.prompt_cost + self.completion_cost

    def _calculate_cost(self, tokens: int, direction: Literal["input", "output"]) -> Decimal:
        """Calculate the cost of the input or output tokens for the span's model."""
        if not self.model_for_cost:
            return Decimal(0)

        try:
            completion_cost = costs.calculate_cost_by_tokens(tokens, self.model_for_cost, direction)
        except Exception:
            return Decimal(0)

        if not completion_cost:
            return Decimal(0)

        return completion_cost


class TraceMetricsResponse(pydantic.BaseModel):
    """
    Trace metrics response model used in trace detail responses.
    """

    span_count: int
    trace_count: int
    success_count: int
    fail_count: int
    indeterminate_count: int

    prompt_tokens: int
    completion_tokens: int
    cache_read_input_tokens: int
    reasoning_tokens: int
    total_tokens: int

    prompt_cost: str
    completion_cost: str
    average_cost_per_trace: str
    total_cost: str

    @pydantic.field_validator(
        'prompt_cost', 'completion_cost', 'average_cost_per_trace', 'total_cost', mode='before'
    )
    @classmethod
    def format_cost(cls, v: Decimal) -> str:
        return _format_cost(v)

    @classmethod
    def from_trace_with_metrics(
        cls: Type['TraceMetricsResponse'],
        trace: 'TraceMetricsMixin',
    ) -> 'TraceMetricsResponse':
        """
        Create a TraceMetricsResponse from a TraceMetricsMixin instance.
        """
        return cls(
            span_count=trace.span_count,
            trace_count=trace.trace_count,
            success_count=trace.success_count,
            fail_count=trace.fail_count,
            indeterminate_count=trace.indeterminate_count,
            prompt_tokens=trace.prompt_tokens,
            completion_tokens=trace.completion_tokens,
            cache_read_input_tokens=trace.cache_read_input_tokens,
            reasoning_tokens=trace.reasoning_tokens,
            total_tokens=trace.total_tokens,
            # ignore these type errors because a conversion happens with field_validator
            prompt_cost=trace.prompt_cost,  # type: ignore
            completion_cost=trace.completion_cost,  # type: ignore
            average_cost_per_trace=trace.average_cost_per_trace,  # type: ignore
            total_cost=trace.total_cost,  # type: ignore
        )


class TraceMetricsMixin(ClickhouseAggregatedModel):
    trace_metrics_field_name: ClassVar[str] = "traces"

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

    def model_post_init(self, __context) -> None:
        """Compute all trace metrics once during initialization to avoid repeated loops"""
        traces = getattr(self, self.trace_metrics_field_name)
        trace_ids: set[str] = set()

        for trace in traces:
            if not isinstance(trace, SpanMetricsMixin):
                raise ValueError(f"Provided trace object {trace} does not implement SpanMetricsMixin.")

            trace_ids.add(trace.trace_id)

            if trace.success:
                self.success_count += 1
            elif trace.fail:
                self.fail_count += 1
            else:
                self.indeterminate_count += 1

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

        self.span_count = len(traces)
        self.trace_count = len(trace_ids)

    def _trace_metrics_additions(self, trace: Any) -> None:
        """
        Helper method to add a single trace's metrics to the current instance.
        This prevents us from having to repeat the loop.
        """
        pass

    @property
    def avg_tokens(self) -> float:
        """Returns the average tokens per trace"""
        return self.total_tokens / self.span_count if self.span_count > 0 else 0.0

    @property
    def avg_success_tokens(self) -> float:
        """Returns the average tokens for successful traces"""
        return self.success_tokens / self.success_count if self.success_count > 0 else 0.0

    @property
    def avg_fail_tokens(self) -> float:
        """Returns the average tokens for failed traces"""
        return self.fail_tokens / self.fail_count if self.fail_count > 0 else 0.0

    @property
    def average_cost_per_trace(self) -> Decimal:
        """Returns the average cost per trace"""
        return self.total_cost / self.trace_count if self.trace_count > 0 else Decimal(0)
