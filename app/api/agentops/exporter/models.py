from typing import Any
import json
from uuid import UUID, uuid4
from typing import Optional, Union
import pydantic
from datetime import datetime, timezone
from opentelemetry.trace import SpanKind


DEFAULT_SERVICE_NAME = "agentops"
DEFAULT_SCOPE_NAME = DEFAULT_SERVICE_NAME
DEFAULT_VERSION = "0.3.x"


def datetime_to_ns(dt: Optional[Union[datetime, int, float]]) -> Optional[int]:
    """Convert datetime or timestamp to nanoseconds"""
    if dt is None:
        return None

    if isinstance(dt, datetime):
        return int(dt.timestamp() * 1_000_000_000)

    # `int` is probably a millisecond timestamp
    return int(dt) * 1_000_000


def ns_to_datetime(ns: Optional[int]) -> Optional[datetime]:
    """Convert nanoseconds to `datetime`"""
    if not ns:
        return None
    return datetime.fromtimestamp(ns / 1_000_000_000, timezone.utc)


class Trace(pydantic.BaseModel):
    id: UUID
    spans: list["Span"] = pydantic.Field(default_factory=list)

    def __repr__(self) -> str:
        return f"Trace(id={self.id})"


class Span(pydantic.BaseModel):
    """
    Span is a representation of a single operation within a trace.
    It can be a root span or a child span.
    """

    name: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: str
    parent_span_id: Optional[str] = None
    kind: Union[SpanKind, str] = SpanKind.INTERNAL
    start_time: int = 0
    end_time: Optional[int] = None
    project_id: Optional[str] = None
    service_name: str = DEFAULT_SERVICE_NAME
    scope_name: str = DEFAULT_SCOPE_NAME
    scope_version: str = DEFAULT_VERSION
    resource_attributes: dict[str, str] = pydantic.Field(default_factory=dict)
    span_attributes: dict[str, str] = pydantic.Field(default_factory=dict)
    status_code: str = "OK"
    status_message: str = ""
    events: list[dict[str, Any]] = pydantic.Field(default_factory=list)
    links: list[dict[str, Any]] = pydantic.Field(default_factory=list)

    model_config = {
        'arbitrary_types_allowed': True,
    }

    def __repr__(self) -> str:
        return f"Span(span_id={self.span_id}, parent_span_id={self.parent_span_id})"

    def model_post_init(self, __context) -> None:
        if self.end_time is None:
            self.end_time = self.start_time

    @property
    def duration(self) -> int:
        """Calculate duration in nanoseconds"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0

    def to_clickhouse_dict(self) -> dict[str, Any]:
        """Convert to a dictionary ready for ClickHouse insertion"""

        if self.start_time:
            timestamp = ns_to_datetime(self.start_time)
        else:
            timestamp = datetime.now(timezone.utc)

        # otel_context = SpanContext(
        #     trace_id=trace_id,
        #     span_id=span_id,
        #     is_remote=False,
        #     trace_flags=TraceFlags(0x1),  # SAMPLED
        #     trace_state=TraceState()
        # )

        events_timestamps = []
        events_names = []
        events_attributes = []

        for event in self.events:
            try:
                event_timestamp = event.get('timestamp', 0)
                events_timestamps.append(
                    datetime.fromtimestamp(event_timestamp / 1_000_000_000, timezone.utc)
                )
            except (TypeError, ValueError, OverflowError):
                # Fallback if timestamp is invalid
                events_timestamps.append(timestamp)

            events_names.append(event.get('name', ''))
            events_attributes.append(event.get('attributes', {}))

        links_trace_ids = []
        links_span_ids = []
        links_trace_states = []
        links_attributes = []

        for link in self.links:
            links_trace_ids.append(link.get('trace_id', ''))
            links_span_ids.append(link.get('span_id', ''))
            links_trace_states.append(link.get('trace_state', ''))
            links_attributes.append(link.get('attributes', {}))

        if not isinstance(self.resource_attributes, dict):
            self.resource_attributes = {}
        self.resource_attributes["agentops.project.id"] = self.project_id

        # Schema from ClickHouse via `DESCRIBE` otel_traces;
        # Timestamp	DateTime64(9)
        # TraceId	String
        # SpanId	String
        # ParentSpanId	String
        # TraceState	String
        # SpanName	LowCardinality(String)
        # SpanKind	LowCardinality(String)
        # ServiceName	LowCardinality(String)
        # ResourceAttributes	Map(LowCardinality(String), String)
        # ScopeName	String
        # ScopeVersion	String
        # SpanAttributes	Map(LowCardinality(String), String)
        # Duration	Int64
        # StatusCode	LowCardinality(String)
        # StatusMessage	String
        # Events.Timestamp	Array(DateTime64(9))
        # Events.Name	Array(LowCardinality(String))
        # Events.Attributes	Array(Map(LowCardinality(String), String))
        # Links.TraceId	Array(String)
        # Links.SpanId	Array(String)
        # Links.TraceState	Array(String)
        # Links.Attributes	Array(Map(LowCardinality(String), String))
        # ProjectId	String
        return {
            "Timestamp": timestamp,
            "TraceId": self.trace_id,
            "SpanId": self.span_id,
            "ParentSpanId": self.parent_span_id,
            "TraceState": "",
            "SpanName": self.name,
            "SpanKind": self.kind.name if isinstance(self.kind, SpanKind) else self.kind,
            "ServiceName": self.service_name,
            "ResourceAttributes": self.resource_attributes,
            "ScopeName": self.scope_name,
            "ScopeVersion": self.scope_version,
            "SpanAttributes": self.span_attributes,
            "Duration": self.duration,
            "StatusCode": self.status_code,
            "StatusMessage": self.status_message,
            "Events.Timestamp": events_timestamps,
            "Events.Name": events_names,
            "Events.Attributes": events_attributes,
            "Links.TraceId": links_trace_ids,
            "Links.SpanId": links_span_ids,
            "Links.TraceState": links_trace_states,
            "Links.Attributes": links_attributes,
        }


class BaseModel(pydantic.BaseModel):
    model_config = {
        'arbitrary_types_allowed': True,
    }


class Session(BaseModel):
    """
    Session renamed to Trace
    """

    id: UUID
    project_id: Optional[UUID] = None
    init_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    tags: Optional[Union[str, list]] = None
    end_state: Optional[str] = None
    end_state_reason: Optional[str] = None
    video: Optional[str] = None
    host_env: Optional[dict] = None
    project_id_secondary: Optional[dict] = None

    async def to_trace(self) -> Trace:
        """Convert a Session to a Trace with spans"""
        span = Span(
            name="session",
            trace_id=str(self.id),
            span_id=str(self.id),  # TODO this is the same as trace_id
            parent_span_id=None,  # parent span has no parent
            kind=SpanKind.SERVER,
            start_time=datetime_to_ns(self.init_timestamp),
            end_time=datetime_to_ns(self.end_timestamp),
            project_id=str(self.project_id),
            service_name=DEFAULT_SERVICE_NAME,
            scope_name=f"{DEFAULT_SCOPE_NAME}.session",
            scope_version=DEFAULT_VERSION,
            resource_attributes={
                "host.name": str(self.host_env) if self.host_env else "unknown",
                "service.name": DEFAULT_SERVICE_NAME,
            },
            span_attributes={
                "session.id": str(self.id),
                "session.end_state": self.end_state or "",
                "session.end_state_reason": self.end_state_reason or "",
            },
        )

        try:
            if self.tags:
                if not isinstance(self.tags, list):
                    self.tags = [self.tags]
                for i, value in enumerate(self.tags):
                    span.span_attributes[f"session.tag.{i}"] = str(value)
        except Exception:
            pass

        trace = Trace(id=self.id)
        trace.spans.append(span)
        return trace


class Agent(BaseModel):
    """
    Agent becomes a (parent) Span
    """

    id: UUID
    session_id: Optional[UUID] = None
    name: Optional[str] = None
    logs: Optional[str] = None

    async def to_span(
        self,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Span:
        """Convert an Agent to a Span"""
        span_attributes = {
            "agent.id": str(self.id),
            "agent.name": self.name or "",
            "session.id": str(self.session_id),
        }

        events = []
        if self.logs:
            events.append(
                {
                    "timestamp": 0,  # we don't have a timestamp
                    "name": "logs",
                    "attributes": {"log.message": self.logs},
                }
            )

        return Span(
            name=f"agent:{self.name}" if self.name else f"agent:{self.id}",
            trace_id=trace_id,
            span_id=str(self.id),
            parent_span_id=parent_span_id,
            kind=SpanKind.INTERNAL,
            project_id=project_id,
            service_name=DEFAULT_SERVICE_NAME,
            scope_name=f"{DEFAULT_SCOPE_NAME}.agent",
            scope_version=DEFAULT_VERSION,
            resource_attributes={},
            span_attributes=span_attributes,
            events=events,
        )


class ActionEvent(BaseModel):
    """
    Action becomes a (child) Span
    """

    id: UUID
    session_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    action_type: Optional[str] = None
    logs: Optional[str] = None
    screenshot: Optional[str] = None
    params: Optional[str] = None
    returns: Optional[str] = None
    init_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None

    async def to_span(
        self,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Span:
        """Convert an ActionEvent to a Span"""
        span_attributes = {
            "action.id": str(self.id),
            "action.type": self.action_type or "",
            "session.id": str(self.session_id),
            "agent.id": str(self.agent_id),
        }

        if self.params:
            if isinstance(self.params, dict):
                span_attributes["action.params"] = json.dumps(self.params)
            else:
                span_attributes["action.params"] = str(self.params)

        if self.returns:
            if isinstance(self.returns, dict):
                span_attributes["action.returns"] = json.dumps(self.returns)
            else:
                span_attributes["action.returns"] = str(self.returns)

        if self.screenshot:
            span_attributes["action.screenshot"] = self.screenshot

        init_timestamp_ns = datetime_to_ns(self.init_timestamp)
        events = []
        if self.logs:
            events.append(
                {"timestamp": init_timestamp_ns, "name": "logs", "attributes": {"log.message": self.logs}}
            )

        return Span(
            name=f"action:{self.action_type or 'unknown'}",
            trace_id=trace_id,
            span_id=str(self.id),
            parent_span_id=parent_span_id,
            kind=SpanKind.INTERNAL,
            start_time=init_timestamp_ns,
            end_time=datetime_to_ns(self.end_timestamp),
            project_id=project_id,
            service_name=DEFAULT_SERVICE_NAME,
            scope_name=f"{DEFAULT_SCOPE_NAME}.action",
            scope_version=DEFAULT_VERSION,
            resource_attributes={},
            span_attributes=span_attributes,
            events=events,
        )


class LLMEvent(BaseModel):
    """
    LLMEvent becomes a (child) Span
    """

    id: UUID
    session_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    thread_id: Optional[UUID] = None
    prompt: Optional[dict] = None
    completion: Optional[dict] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost: Optional[float] = None
    promptarmor_flag: Optional[bool] = None
    params: Optional[Union[str, dict]] = None
    returns: Optional[Union[str, dict]] = None
    init_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None

    async def to_span(
        self,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Span:
        """Convert an LLMEvent to a Span with GenAI semantic conventions"""

        # Use GenAI semantic conventions for span attributes
        # See: https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai.md

        # {
        # "gen_ai.completion.0.content": "Why couldn't the bicycle stand up by itself? It was two tired.",
        # "gen_ai.completion.0.finish_reason": "stop",
        # "gen_ai.completion.0.role": "assistant",
        # "gen_ai.openai.api_base": "https://api.openai.com/v1/",
        # "gen_ai.prompt.0.content": "Write a one-line joke",
        # "gen_ai.prompt.0.role": "user",
        # "gen_ai.request.model": "gpt-3.5-turbo",
        # "gen_ai.response.id": "chatcmpl-B9ekm6iX1GDInqhtj5XlmIqFHamFf",
        # "gen_ai.response.model": "gpt-3.5-turbo-0125",
        # "gen_ai.system": "OpenAI",
        # "gen_ai.usage.completion_tokens": "16",
        # "gen_ai.usage.prompt_tokens": "12",
        # "llm.headers": "None",
        # "llm.is_streaming": "false",
        # "llm.request.type": "chat",
        # "llm.usage.total_tokens": "28"
        # }

        span_attributes = {
            "llm.id": str(self.id),
            "llm.model": self.model if self.model else "",
            "llm.prompt_tokens": str(self.prompt_tokens),
            "llm.completion_tokens": str(self.completion_tokens),
            "llm.total_tokens": str(self.prompt_tokens + self.completion_tokens),
            "llm.cost": str(self.cost) if self.cost is not None else "0.0",
            "session.id": str(self.session_id),
            "agent.id": str(self.agent_id),
            "thread.id": str(self.thread_id) if self.thread_id else "",
            "llm.is_streaming": "false",
            "llm.request.type": "chat",
            "gen_ai.openai.api_base": "https://api.openai.com/v1/",
            "gen_ai.usage.prompt_tokens": str(self.prompt_tokens),
            "gen_ai.usage.completion_tokens": str(self.completion_tokens),
        }

        try:
            prompts = self.prompt.get('messages', self.prompt)
            if not isinstance(prompts, list):
                prompts = [prompts]
            for i, prompt in enumerate(prompts):
                if not isinstance(prompt, dict):
                    continue
                if 'content' in prompt:
                    content = prompt['content']
                elif 'string' in prompt:
                    content = prompt['string']
                elif 'message' in prompt:
                    content = prompt['message']
                else:
                    content = prompt
                span_attributes[f"gen_ai.prompt.{i}.content"] = str(content)
                span_attributes[f"gen_ai.prompt.{i}.role"] = str(prompt.get('role', ""))
        except (KeyError, TypeError):
            span_attributes["gen_ai.prompt"] = self.prompt

        try:
            completions = self.completion.get('messages', self.completion)
            if not isinstance(completions, list):
                completions = [completions]
            for i, completion in enumerate(completions):
                if not isinstance(completion, dict):
                    continue
                span_attributes[f"gen_ai.completion.{i}.content"] = str(completion.get('content', ""))
                span_attributes[f"gen_ai.completion.{i}.finish_reason"] = "stop"
                span_attributes[f"gen_ai.completion.{i}.role"] = str(completion.get('role', ""))
                # span_attributes[f"gen_ai.completion.{i}.tool_calls"] = json.dumps(completion.get('role', []))
        except (KeyError, TypeError):
            span_attributes["gen_ai.completion"] = self.completion

        if self.promptarmor_flag is not None:
            span_attributes["llm.promptarmor_flag"] = str(self.promptarmor_flag).lower()

        span_attributes["gen_ai.system"] = "llm"
        span_attributes["gen_ai.operation.name"] = "chat"
        span_attributes["gen_ai.request.model"] = self.model if self.model else ""
        span_attributes["gen_ai.response.model"] = self.model if self.model else ""

        if self.params:
            if isinstance(self.params, dict):
                span_attributes["gen_ai.request.parameters"] = json.dumps(self.params)
            else:
                span_attributes["gen_ai.request.parameters"] = str(self.params)

        if self.returns:
            if isinstance(self.returns, dict):
                span_attributes["gen_ai.response.metadata"] = json.dumps(self.returns)
            else:
                span_attributes["gen_ai.response.metadata"] = str(self.returns)

        init_timestamp_ns = datetime_to_ns(self.init_timestamp)
        end_timestamp_ns = datetime_to_ns(self.end_timestamp) or init_timestamp_ns

        return Span(
            name=f"llm:{self.model}",
            trace_id=trace_id,
            span_id=str(self.id),
            parent_span_id=parent_span_id,
            kind=SpanKind.CLIENT,
            start_time=init_timestamp_ns,
            end_time=end_timestamp_ns,
            project_id=project_id,
            service_name=DEFAULT_SERVICE_NAME,
            scope_name=f"{DEFAULT_SCOPE_NAME}.llm",
            scope_version=DEFAULT_VERSION,
            resource_attributes={},
            span_attributes=span_attributes,
            events=[],
        )


class ToolEvent(BaseModel):
    """
    ToolEvent becomes a (child) Span
    """

    id: UUID
    session_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    name: Optional[str] = None
    logs: Optional[str] = None
    params: Optional[Union[str, dict]] = None
    returns: Optional[Union[dict, str]] = None
    init_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None

    async def to_span(
        self,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Span:
        """Convert a ToolEvent to a Span"""
        span_attributes = {
            "tool.id": str(self.id),
            "tool.name": self.name,
            "session.id": str(self.session_id),
            "agent.id": str(self.agent_id),
            "gen_ai.tool.name": self.name,
        }

        if self.params:
            if isinstance(self.params, dict):
                span_attributes["tool.params"] = json.dumps(self.params)
            else:
                span_attributes["tool.params"] = str(self.params)

        if self.returns:
            if isinstance(self.returns, dict):
                span_attributes["tool.returns"] = json.dumps(self.returns)
            else:
                span_attributes["tool.returns"] = str(self.returns)

        init_timestamp_ns = datetime_to_ns(self.init_timestamp)
        events = []
        if self.logs:
            events.append(
                {"timestamp": init_timestamp_ns, "name": "logs", "attributes": {"log.message": self.logs}}
            )

        return Span(
            name=f"tool:{self.name}",
            trace_id=trace_id,
            span_id=str(self.id),
            parent_span_id=parent_span_id,
            kind=SpanKind.INTERNAL,
            start_time=init_timestamp_ns,
            end_time=datetime_to_ns(self.end_timestamp),
            project_id=project_id,
            service_name=DEFAULT_SERVICE_NAME,
            scope_name=f"{DEFAULT_SCOPE_NAME}.tool",
            scope_version=DEFAULT_VERSION,
            resource_attributes={},
            span_attributes=span_attributes,
            events=events,
        )


class ErrorEvent(BaseModel):
    """
    ErrorEvent becomes a (child) Span
    """

    id: Optional[int] = pydantic.Field(default=uuid4())
    session_id: Optional[UUID] = None
    trigger_event_id: Optional[UUID] = None
    trigger_event_type: Optional[str] = None
    error_type: Optional[str] = None
    code: Optional[str] = None
    details: Optional[str] = None
    logs: Optional[str] = None
    timestamp: Optional[datetime] = None

    async def to_span(
        self,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Span:
        """Convert an ErrorEvent to a Span"""
        span_attributes = {
            "error.type": self.error_type or "unknown_error",
            "error.code": self.code if self.code else "",
            "session.id": str(self.session_id),
            "trigger_event.id": str(self.trigger_event_id) if self.trigger_event_id else "",
            "trigger_event.type": str(self.trigger_event_type) if self.trigger_event_type else "",
        }

        timestamp_ns = datetime_to_ns(self.timestamp)
        events = []
        if self.details:
            events.append(
                {
                    "timestamp": timestamp_ns,
                    "name": "error.details",
                    "attributes": {"error.details": self.details},
                }
            )
        if self.logs:
            events.append(
                {"timestamp": timestamp_ns, "name": "logs", "attributes": {"log.message": self.logs}}
            )

        return Span(
            name=f"error:{self.error_type or 'unknown'}",
            trace_id=trace_id,
            span_id=str(self.id),
            parent_span_id=parent_span_id,
            kind=SpanKind.INTERNAL,
            start_time=timestamp_ns,
            end_time=timestamp_ns,  # same as start for point-in-time event
            project_id=project_id,
            service_name=DEFAULT_SERVICE_NAME,
            scope_name=f"{DEFAULT_SCOPE_NAME}.error",
            scope_version=DEFAULT_VERSION,
            resource_attributes={},
            span_attributes=span_attributes,
            status_code="ERROR",
            status_message=self.details
            if self.details and len(self.details) < 100
            else (self.error_type or "unknown_error"),
            events=events,
        )
