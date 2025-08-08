"""
Export data to ClickHouse.

Takes data from the existing v2.py endpoints and formats it as Spans and Traces.

Traces and their root spans share the same ID which comes from the Session ID.

`exporter` is a terrible name, but here we are.
"""

from agentops.api.log_config import logger
from agentops.api.db.supabase_client import get_async_supabase
from .models import Session, Agent, LLMEvent, ActionEvent, ToolEvent, ErrorEvent
from .models import Trace, Span
from .processor import (
    clickhouse_create_trace,
    clickhouse_create_span,
    clickhouse_update_span,
)


def _filter_for_updated_data(keys: list, data: dict) -> dict:
    """Return just the selected fields from the data."""
    return {k: v for k, v in data.items() if k in keys}


async def _get_project_id(session_id: str) -> str:
    """Get the project ID from the session ID."""
    supabase = await get_async_supabase()
    session = await supabase.table('sessions').select('project_id').eq('id', session_id).single().execute()
    return session.data['project_id']


async def create_session(data: dict) -> None:
    """Save session data to ClickHouse."""
    logger.info("Started creating ClickHouse session")
    session = Session(**data)
    trace: Trace = await session.to_trace()
    await clickhouse_create_trace(trace)
    logger.info(f"Created ClickHouse session as trace {trace}")


async def update_session(data: dict) -> None:
    """Update session data for an existing record in ClickHouse."""
    assert 'id' in data, 'session_id must be provided to update session data.'

    session = Session(**data)
    trace: Trace = await session.to_trace()
    span: Span = trace.spans[0]
    await clickhouse_update_span(span.span_id, span.to_clickhouse_dict())


async def create_agent(data: dict) -> None:
    """Save agent data to ClickHouse."""
    assert 'session_id' in data, 'session_id must be provided to create agent data.'
    project_id = await _get_project_id(data['session_id'])

    agent = Agent(**data)
    span = await agent.to_span(
        trace_id=str(data['session_id']), parent_span_id=str(data['session_id']), project_id=str(project_id)
    )
    await clickhouse_create_span(span)
    logger.info(f"Created ClickHouse agent as span {span}")


async def update_agent(data: dict) -> None:
    raise NotImplementedError('Pretty sure we never update agent data.')


async def create_llm_event(data: dict) -> None:
    """Save LLM event data to ClickHouse."""
    assert 'session_id' in data, 'session_id must be provided to create LLM event data.'
    assert 'agent_id' in data, 'agent_id must be provided to create LLM event data.'
    project_id = await _get_project_id(data['session_id'])

    llm_event = LLMEvent(**data)
    span: Span = await llm_event.to_span(
        trace_id=str(data['session_id']), parent_span_id=str(data['agent_id']), project_id=str(project_id)
    )
    await clickhouse_create_span(span)
    logger.info(f"Created ClickHouse LLM event as span {span}")


async def update_llm_event(data: dict) -> None:
    """Update LLM event data for an existing record in ClickHouse."""
    assert 'id' in data, 'id must be provided to update LLM event data.'

    llm_event = LLMEvent(**data)
    span: Span = await llm_event.to_span()
    await clickhouse_update_span(span.span_id, span.to_clickhouse_dict())
    logger.info(f"Updated ClickHouse LLM event as span {span}")


# data['session_id'] = '06246901-8691-4ae3-848e-69aec2d0722b'
async def create_action_event(data: dict) -> None:
    """Save action event data to ClickHouse."""
    assert 'session_id' in data, 'session_id must be provided to create action event data.'
    assert 'agent_id' in data, 'agent_id must be provided to create action event data.'
    project_id = await _get_project_id(data['session_id'])

    action_event = ActionEvent(**data)
    span: Span = await action_event.to_span(
        trace_id=str(data['session_id']), parent_span_id=str(data['agent_id']), project_id=str(project_id)
    )
    await clickhouse_create_span(span)
    logger.info(f"Created ClickHouse action event as span {span}")


async def update_action_event(data: dict) -> None:
    """Update action event data for an existing record in ClickHouse."""
    assert 'id' in data, 'Action Event ID must be provided to update action event data.'

    action_event = ActionEvent(**data)
    span: Span = await action_event.to_span()
    await clickhouse_update_span(span.span_id, span.to_clickhouse_dict())
    logger.info(f"Updated ClickHouse action event as span {span}")


async def create_tool_event(data: dict) -> None:
    """Save tool event data to ClickHouse."""
    assert 'session_id' in data, 'session_id must be provided to create tool event data.'
    assert 'agent_id' in data, 'agent_id must be provided to create tool event data.'
    project_id = await _get_project_id(data['session_id'])

    tool_event = ToolEvent(**data)
    span: Span = await tool_event.to_span(
        trace_id=str(data['session_id']), parent_span_id=str(data['agent_id']), project_id=str(project_id)
    )
    await clickhouse_create_span(span)
    logger.info(f"Created ClickHouse tool event as span {span}")


async def update_tool_event(data: dict) -> None:
    """Update tool event data for an existing record in ClickHouse."""
    assert 'id' in data, 'id must be provided to update tool event data.'

    tool_event = ToolEvent(**data)
    span: Span = await tool_event.to_span()
    await clickhouse_update_span(span.span_id, span.to_clickhouse_dict())
    logger.info(f"Updated ClickHouse tool event as span {span}")


async def create_error_event(data: dict) -> None:
    """Save error event data to ClickHouse."""
    assert 'session_id' in data, 'session_id must be provided to create error event data.'
    project_id = await _get_project_id(data['session_id'])

    error_event = ErrorEvent(**data)
    span: Span = await error_event.to_span(
        trace_id=str(data['session_id']), parent_span_id=str(data['session_id']), project_id=str(project_id)
    )
    await clickhouse_create_span(span)
    logger.info(f"Created ClickHouse error event as span {span}")


async def update_error_event(data: dict) -> None:
    """Update error event data for an existing record in ClickHouse."""
    assert 'id' in data, 'id must be provided to update error event data.'

    error_event = ErrorEvent(**data)
    span: Span = await error_event.to_span()
    await clickhouse_update_span(span.span_id, span.to_clickhouse_dict())
    logger.info(f"Updated ClickHouse error event as span {span}")
