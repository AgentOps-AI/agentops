from typing import Optional
from datetime import datetime
import pydantic
from fastapi import HTTPException
from agentops.api.models.traces import TraceModel
from agentops.api.models.span_metrics import TraceMetricsResponse
from .base import AuthenticatedPublicAPIView, BaseResponse


class BaseTraceView(AuthenticatedPublicAPIView):
    """
    Base view for trace-related API endpoints.
    This class can be extended to create specific views for different trace endpoints.
    """

    async def get_trace(self, trace_id: str) -> TraceModel:
        project = await self.get_sparse_project()

        if not trace_id:
            raise HTTPException(status_code=400, detail="trace_id is required")

        trace = await TraceModel.select(
            filters={
                "trace_id": trace_id,
            }
        )

        if not trace or not len(trace.spans):
            raise HTTPException(status_code=404, detail="Trace not found")

        if not trace.project_id == str(project.id):
            raise HTTPException(status_code=404, detail="Trace not found")

        return trace


class TraceResponse(BaseResponse):
    class SpanSummaryResponse(BaseResponse):
        span_id: str
        parent_span_id: Optional[str]
        span_name: str
        span_kind: str
        start_time: str
        end_time: str
        duration: int
        status_code: str
        status_message: str

        @pydantic.field_validator('start_time', 'end_time', mode='before')
        @classmethod
        def format_datetime(cls, v: datetime) -> str:
            return v.isoformat()

    trace_id: str
    project_id: str
    tags: list[str]
    spans: list[SpanSummaryResponse]


class TraceView(BaseTraceView):
    __name__ = "Get Trace"
    __doc__ = """
    Get details about a trace with summarized information about its spans.
    """

    async def __call__(self, trace_id: str) -> TraceResponse:
        trace = await self.get_trace(trace_id)
        return TraceResponse.model_validate(trace)


class TraceMetricsView(BaseTraceView):
    __name__ = "Get Trace Metrics"
    __doc__ = """
    Get aggregated metrics data for a trace.
    """

    async def __call__(self, trace_id: str) -> TraceMetricsResponse:
        # use the internal trace metrics cuz it's easier.
        trace = await self.get_trace(trace_id)
        return TraceMetricsResponse.from_trace_with_metrics(trace)
