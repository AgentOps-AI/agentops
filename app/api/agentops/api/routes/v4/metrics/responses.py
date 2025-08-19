from typing import Optional, Any
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
import pydantic


class SpanCount(pydantic.BaseModel):
    total: int
    success: int
    fail: int
    unknown: int
    indeterminate: int


class TotalTokens(pydantic.BaseModel):
    all: int
    success: int
    fail: int


class AverageTokens(pydantic.BaseModel):
    all: float
    success: float
    fail: float

    @pydantic.field_validator('all', 'success', 'fail', mode='before')
    @classmethod
    def round_float(cls, v: float) -> float:
        """Round all values to 2 decimal places."""
        return round(v, 2)


class TokenMetrics(pydantic.BaseModel):
    total_cost: str
    average_cost_per_session: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: TotalTokens
    avg_tokens: AverageTokens

    @pydantic.field_validator('total_cost', 'average_cost_per_session', mode='before')
    @classmethod
    def format_cost(cls, v: Decimal) -> str:
        """Ensure the cost is formatted as a string with 5 decimal places."""
        return f"{float(v):.5f}"


class DurationMetrics(pydantic.BaseModel):
    min_duration_ns: Optional[int] = None
    max_duration_ns: Optional[int] = None
    avg_duration_ns: int
    total_duration_ns: Optional[int] = None
    trace_durations: list[Any]


class ProjectMetricsResponse(pydantic.BaseModel):
    project_id: str
    trace_count: int
    span_count: SpanCount
    token_metrics: TokenMetrics
    duration_metrics: DurationMetrics
    success_datetime: list[str]
    fail_datetime: list[str]
    indeterminate_datetime: list[str]
    spans_per_trace: dict[int, int]
    trace_durations: list[int]
    trace_cost_dates: dict[str, float]
    start_time: str
    end_time: str
    freeplan_truncated: bool = False

    @pydantic.field_validator('project_id', mode='before')
    @classmethod
    def format_uuid(cls, v: UUID) -> str:
        """Ensure the project_id is formatted as a string."""
        return str(v)

    @pydantic.field_validator('trace_cost_dates', mode='before')
    @classmethod
    def format_date_keys_float_values(cls, v: dict[date, Decimal]) -> dict[str, float]:
        """Ensure the trace_cost_dates are able to be serialized properly."""
        return {date.isoformat(): float(cost) for date, cost in v.items()}

    @pydantic.field_validator('success_datetime', 'fail_datetime', 'indeterminate_datetime', mode='before')
    @classmethod
    def format_datetime_list(cls, v: list[datetime]) -> list[str]:
        """Ensure the datetime lists are formatted as ISO strings."""
        return [d.isoformat() for d in v]

    @pydantic.field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def format_datetime(cls, v: datetime) -> str:
        """Ensure the start_time and end_time are formatted as ISO strings."""
        return v.isoformat()
