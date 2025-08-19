"""
API for receiving log files from the AgentOps SDK.

Authorized by JWT.
Accept a body of content to store.
Returns the public URL where the data can be accessed.

Uses Supabase Bucket storage (via the AWS S3 interface).
"""

import re
from fastapi import Depends, HTTPException, Request, status

from agentops.common.environment import APP_URL, FREEPLAN_LOGS_LINE_LIMIT
from agentops.common.views import add_cors_headers
from agentops.common.orm import Session, get_orm_session
from agentops.common.freeplan import FreePlanFilteredResponse
from agentops.auth.views import public_route
from agentops.opsboard.models import ProjectModel
from agentops.api.environment import SUPABASE_S3_LOGS_BUCKET
from agentops.api.storage import get_s3_client
from agentops.api.storage import BaseObjectUploadView
from agentops.api.models.traces import TraceModel


@public_route
class LogsUploadView(BaseObjectUploadView):
    bucket_name: str = SUPABASE_S3_LOGS_BUCKET

    @property
    def filename(self) -> str:
        """Generate a unique filename for the object"""
        trace_id = self.request.headers.get("Trace-Id")

        if not trace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No trace ID provided",
            )

        # only allow alphanumeric characters, underscores, dashes, and dots
        if re.search(r"[^a-zA-Z0-9_.-]", trace_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trace ID contains invalid characters",
            )

        return f'{trace_id}.log'


class LogContentResponse(FreePlanFilteredResponse):
    _freeplan_maxlines = {
        "content": FREEPLAN_LOGS_LINE_LIMIT,
    }

    content: str
    trace_id: str


def convert_trace_id(trace_id: str) -> str:
    """Convert hex trace_id to int if in hex format (contains at least one letter a-f)."""
    try:
        # Only convert if string contains hex letters and is valid hex
        if any(c in 'abcdefABCDEF' for c in trace_id) and all(
            c in '0123456789abcdefABCDEF' for c in trace_id
        ):
            return str(int(trace_id, 16))
        return trace_id
    except ValueError:
        return trace_id


@add_cors_headers(
    origins=[APP_URL],
    methods=["GET", "OPTIONS"],
)
async def get_trace_logs(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
    trace_id: str,
) -> LogContentResponse:
    """
    Retrieve logs for a specific trace ID.
    Verifies that the user has access to the trace before returning the logs.
    """
    trace_id_int = convert_trace_id(trace_id)

    trace = await TraceModel.select(
        filters={
            "trace_id": trace_id,
        }
    )
    if not trace.spans:  # trace does not exist
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trace",
        )

    project = ProjectModel.get_by_id(orm, trace.project_id)
    if not project or not project.org.is_user_member(request.state.session.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trace",
        )

    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=SUPABASE_S3_LOGS_BUCKET,
            Key=f"{trace_id_int}.log",
        )
        content = response['Body'].read().decode('utf-8')

        return LogContentResponse(
            content=content,
            trace_id=trace_id,
            freeplan_truncated=project.is_freeplan,
        )

    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No logs found for trace ID: {trace_id}",
        )
