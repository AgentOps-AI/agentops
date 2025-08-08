from typing import Optional, Any
from datetime import datetime
import pydantic
from fastapi import HTTPException
from agentops.common.otel import otel_attributes_to_nested
from agentops.api.models.traces import SpanModel
from agentops.api.models.span_metrics import SpanMetricsResponse
from .base import AuthenticatedPublicAPIView, BaseResponse


class BaseSpanView(AuthenticatedPublicAPIView):
    """
    Base view for span-related API endpoints.
    This class can be extended to create specific views for different span endpoints.
    """

    async def get_span(self, span_id: str) -> SpanModel:
        project = await self.get_sparse_project()

        if not span_id:
            raise HTTPException(status_code=400, detail="span_id is required")

        spans = await SpanModel.select(
            filters={
                "span_id": span_id,
            }
        )

        if not len(spans):
            raise HTTPException(status_code=404, detail="Span not found")

        span = spans[0]
        if not span.project_id == str(project.id):
            raise HTTPException(status_code=404, detail="Span not found")

        return span


class SpanResponse(BaseResponse):
    span_id: str
    parent_span_id: Optional[str] = None

    span_name: str
    span_kind: str
    service_name: str

    start_time: str
    end_time: str
    duration: int
    status_code: str
    status_message: Optional[str] = None

    attributes: dict[str, Any] = pydantic.Field(default_factory=dict)
    resource_attributes: dict[str, Any] = pydantic.Field(default_factory=dict)
    span_attributes: dict[str, Any] = pydantic.Field(default_factory=dict)

    @pydantic.field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def format_datetime(cls, v: datetime) -> str:
        return v.isoformat()

    @pydantic.field_validator('attributes', 'resource_attributes', 'span_attributes', mode='before')
    @classmethod
    def format_attributes(cls, v: dict[str, str]) -> dict[str, Any]:
        return otel_attributes_to_nested(v)


class SpanView(BaseSpanView):
    __name__ = "Get Span"
    __doc__ = """
    Get all details about a span, including the full attribute payloads.
    """

    async def __call__(self, span_id: str) -> SpanResponse:
        span = await self.get_span(span_id)
        return SpanResponse.model_validate(span)


class SpanMetricsView(BaseSpanView):
    __name__ = "Get Span Metrics"
    __doc__ = """
    Get metrics for a span.
    """

    async def __call__(self, span_id: str) -> SpanMetricsResponse:
        # use the internal trace metrics cuz it's easier.
        span = await self.get_span(span_id)
        return SpanMetricsResponse.from_span_with_metrics(span)
