from typing import Optional, Any
from datetime import datetime
import pydantic

from agentops.common.otel import otel_attributes_to_nested
from agentops.common.freeplan import FreePlanFilteredResponse
from agentops.api.models.span_metrics import (
    SpanMetricsResponse,
    TraceMetricsResponse,
)


class TraceListItem(pydantic.BaseModel):
    freeplan_truncated: bool = False
    trace_id: str
    root_service_name: str
    root_span_name: str
    start_time: str
    end_time: str
    duration: int
    span_count: int
    error_count: int
    tags: Optional[list[str]] = None
    total_cost: Optional[float] = None

    @pydantic.field_validator('start_time', 'end_time', mode='before')
    def format_datetime(cls, v: datetime) -> str:
        """Ensure the start_time and end_time are formatted as ISO strings."""
        return v.isoformat()


class TraceListResponse(pydantic.BaseModel):
    traces: list[TraceListItem]
    metrics: TraceMetricsResponse
    total: int
    limit: int
    offset: int
    freeplan_truncated: bool = False


class SpanItem(FreePlanFilteredResponse):
    _freeplan_exclude = (
        'attributes',
        'resource_attributes',
        'span_attributes',
        'event_timestamps',
        'event_names',
        'event_attributes',
        'link_trace_ids',
        'link_span_ids',
        'link_trace_states',
        'link_attributes',
        # 'metrics',
    )

    span_id: str
    parent_span_id: Optional[str] = None

    span_name: str
    span_kind: str
    span_type: Optional[str] = None  # populated post-init
    service_name: str

    start_time: str
    end_time: str
    duration: int
    status_code: str
    status_message: Optional[str] = None

    attributes: dict[str, Any] = pydantic.Field(default_factory=dict)
    resource_attributes: dict[str, Any] = pydantic.Field(default_factory=dict)
    span_attributes: dict[str, Any] = pydantic.Field(default_factory=dict)

    event_timestamps: list[str] = pydantic.Field(default_factory=list)
    event_names: list[str] = pydantic.Field(default_factory=list)
    event_attributes: list[Any] = pydantic.Field(default_factory=list)

    link_trace_ids: list[str] = pydantic.Field(default_factory=list)
    link_span_ids: list[str] = pydantic.Field(default_factory=list)
    link_trace_states: list[str] = pydantic.Field(default_factory=list)
    link_attributes: list[Any] = pydantic.Field(default_factory=list)

    metrics: Optional[SpanMetricsResponse] = None

    @pydantic.field_validator('start_time', 'end_time', mode='before')
    def format_datetime(cls, v: datetime) -> str:
        """Ensure the start_time and end_time are formatted as ISO strings."""
        return v.isoformat()

    @pydantic.field_validator('event_timestamps', mode='before')
    def format_event_timestamps(cls, v: list[datetime]) -> list[str]:
        """Ensure event timestamps are formatted as ISO strings."""
        return [dt.isoformat() for dt in v]

    @pydantic.model_validator(mode='after')
    def set_span_type(self):
        if self.span_attributes:
            self.span_type = self.format_span_type(self.span_attributes)

        return self

    def format_span_type(self, data: Any, current_path: str = "") -> str:
        """Determine the span type from the span attributes dictionary."""
        # TODO this is LLM slop migrated from the v4 release and needs to be refactored
        SPAN_TYPE_MAP = {
            "gen_ai": "request",
            "agent": "agent",
            "tool": "tool",
        }
        if isinstance(data, dict):
            # Check if current path/key is in SPAN_TYPE_MAP
            for key in data.keys():
                full_path = f"{current_path}.{key}" if current_path else key
                if key in SPAN_TYPE_MAP:
                    return SPAN_TYPE_MAP[key]

                # Recursively check nested dictionaries
                result = self.format_span_type(data[key], full_path)
                if result != "other":
                    return result
        elif isinstance(data, list):
            # Check each item in the list
            for item in data:
                result = self.format_span_type(item, current_path)
                if result != "other":
                    return result

        return "other"

    @pydantic.field_validator('attributes', 'resource_attributes', 'span_attributes', mode='before')
    def format_attributes(cls, v: dict[str, str]) -> dict[str, Any]:
        return otel_attributes_to_nested(v)


class TraceDetailResponse(FreePlanFilteredResponse):
    project_id: str
    trace_id: str
    tags: Optional[list[str]] = pydantic.Field(default_factory=list)
    metrics: TraceMetricsResponse
    spans: list[SpanItem]
