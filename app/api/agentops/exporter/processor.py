"""
Processor
---------
The processor handles acquiring a connection to each endpoint and marshalling the data
between each.

This module serves as both an internal API for working with the interchange of data between
the Supabase and ClickHouse databases, as well as a CLI tool for exporting data from Supabase
to ClickHouse as a batch operation.
"""

from typing import Any, Optional, AsyncGenerator
import warnings
import asyncio
import os
import psycopg
import psycopg_pool
from clickhouse_driver.util.escape import escape_param as _clickhouse_escape_param

from agentops.api.db.clickhouse_client import get_async_clickhouse
from .models import BaseModel, Session, Agent, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from .models import Trace, Span


EXPORT_TABLES_MODELS: dict[str, BaseModel] = {
    'sessions': Session,
    'agents': Agent,
    'actions': ActionEvent,
    'llms': LLMEvent,
    'tools': ToolEvent,
    'errors': ErrorEvent,
}
EXPORT_AS_SPANS = (
    'agents',
    'actions',
    'llms',
    'tools',
    'errors',
)
IMPORT_TABLE_NAME = 'otel_traces'

# Supabase connection pooling for export
SUPABASE_MIN_POOL_SIZE = 12
SUPABASE_MAX_POOL_SIZE = 24

# DRY_RUN does not write data to ClickHouse
DRY_RUN = False

# Pagination for exporting data from Supabase
PAGE_NUMBER = 0
# Cutoff after a certain number of pages
MAX_PAGES = None

# Timeout for writing a trace to ClickHouse
TIMEOUT = 240
# Number of rows to fetch from Supabase per page for export
BATCH_ROW_COUNT = 1000

# Maximum number of concurrent workers
MAX_CONCURRENT = 42
PARALLEL_READS = 21

# Filenames for persistent state
DROPPED_RECORDS_FILENAME = 'dropped_records.csv'
LAST_SESSION_ID_FILENAME = 'last_session_id.txt'

# Global variables that will be initialized in main() or init functions
_last_session_file = None
LAST_SESSION_ID = None


def write_dropped_record(table: str, id: Any, exception: Exception) -> None:
    """Make a note of a record that was dropped during processing."""
    with open(DROPPED_RECORDS_FILENAME, 'a') as f:
        msg = str(exception).replace('"', "'").replace("\n", " ~ ")
        f.write(f"{table},{str(id)},\"{msg}\"\n")


def write_last_session_id(session_id: Any) -> None:
    """Write the last session_id by truncating and writing to the already open file."""
    print(session_id)
    if _last_session_file:
        _last_session_file.seek(0)
        _last_session_file.truncate()
        _last_session_file.write(str(session_id))
        _last_session_file.flush()


# Supabase connection pool instance
_supabase_pool: Optional[Any] = None


def get_supabase_pool() -> Any:
    """Get a read-only connection pool to Supabase."""
    global _supabase_pool

    host = os.getenv('SUPABASE_HOST')
    port = os.getenv('SUPABASE_PORT')
    database = os.getenv('SUPABASE_DATABASE')
    user = os.getenv('SUPABASE_USER')
    password = os.getenv('SUPABASE_PASSWORD')

    if _supabase_pool is None:
        _supabase_pool = psycopg_pool.AsyncConnectionPool(
            f"postgresql://{user}:{password}@{host}:{port}/{database}",
            min_size=SUPABASE_MIN_POOL_SIZE,
            max_size=SUPABASE_MAX_POOL_SIZE,
            # configure=lambda c: c.execute("SET default_transaction_read_only = on")
        )
    return _supabase_pool


async def close_supabase_pool() -> None:
    """Close the connection pool to Supabase."""
    global _supabase_pool
    if _supabase_pool is not None:
        await _supabase_pool.close()
        _supabase_pool = None


class SupabaseExporterMeta(type):
    def __class_getitem__(cls, model_class: BaseModel) -> 'SupabaseExporter':
        if model_class not in EXPORT_TABLES_MODELS.values():
            raise ValueError(model_class.__name__)

        table_name = [k for k, v in EXPORT_TABLES_MODELS.items() if v == model_class][0]
        return SupabaseExporter(table_name, model_class)


class SupabaseExporter(metaclass=SupabaseExporterMeta):
    """
    Exporter that connects to a Supabase table and fetches records as model instances.

    Usage:
    ```
    sessions = SupabaseExporter['sessions']
    async for session in sessions.fetchall("SELECT * FROM {table_name}"):
        print(session)
    ```
    `table_name` is always populated with the table name of the model class.

    Extra parameters can be passed to the fetchall method as keyword arguments.
    ```
    async for session in sessions.fetchall("SELECT * FROM {table_name} WHERE id = '{id}'", id='123'):
        print(session)
    ```
    """

    table_name: str
    model_class: BaseModel

    def __init__(self, table_name: str, model_class: BaseModel) -> None:
        self.table_name = table_name
        self.model_class = model_class

    def get_model_instance(self, **kwargs) -> BaseModel:
        try:
            return self.model_class(**kwargs)
        except Exception as e:
            write_dropped_record(self.table_name, kwargs.get('id', 'unknown'), e)

    async def fetchall(self, query: str, **kwargs) -> AsyncGenerator[BaseModel, None]:
        query = query.format(table_name=self.table_name, **kwargs)
        async with get_supabase_pool().connection() as conn:
            # Use a dictionary row factory to get rows as dictionaries
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(query)
                for row in await cur.fetchall():
                    yield self.get_model_instance(**row)

    async def fetchone(self, query: str, **kwargs) -> BaseModel:
        query = query.format(table_name=self.table_name, **kwargs)
        async with get_supabase_pool().connection() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(query)
                return self.get_model_instance(**await cur.fetchone())


supabase = SupabaseExporter


async def fetch_all_for_session(model_class: BaseModel, session_id) -> AsyncGenerator[BaseModel, None]:
    """Fetch all records for a session from a given table"""
    query = """
        SELECT * FROM {table_name}
        WHERE session_id = '{session_id}'
    """
    exporter = supabase[model_class]
    async for result in exporter.fetchall(query, session_id=session_id):
        yield result


async def get_session_as_trace(session: Session) -> Trace:
    """Convert a session to a trace with all related spans"""
    write_last_session_id(session.id)
    try:
        trace: Trace = await session.to_trace()
        parent_span_id = trace.spans[0].span_id
    except Exception as e:
        if not session:
            write_dropped_record('session', 'unknown', e)
            return
        write_dropped_record('session', session.id, e)
        return

    for table_name in EXPORT_AS_SPANS:
        model_class = EXPORT_TABLES_MODELS[table_name]
        async for record in fetch_all_for_session(model_class, session.id):
            try:
                if isinstance(record, (Agent, ErrorEvent)):
                    # agent and error belong to parent span
                    span = await record.to_span(
                        trace_id=trace.id, parent_span_id=parent_span_id, project_id=str(session.project_id)
                    )
                elif isinstance(record, (ActionEvent, LLMEvent, ToolEvent)):
                    # actions, llms, and tools belong to an agent
                    span = await record.to_span(
                        trace_id=trace.id,
                        parent_span_id=str(record.agent_id),
                        project_id=str(session.project_id),
                    )
                else:
                    warnings.warn(f"Unknown record type: {type(record)}")
                    continue
            except Exception as e:
                table_name = [k for k, v in EXPORT_TABLES_MODELS.items() if v == model_class][0]
                write_dropped_record(table_name, record.id, e)
                continue
            trace.spans.append(span)
    return trace


async def get_sessions(offset: int, limit: int) -> list[Session]:
    """Get raw session records without processing them as traces yet"""
    query = """
        SELECT * FROM {table_name}
        WHERE id > '{last_session_id}'
        ORDER BY id ASC
        LIMIT {limit}
        OFFSET {offset}
    """
    sessions = []
    lsid = LAST_SESSION_ID if LAST_SESSION_ID else '00000000-0000-0000-0000-000000000000'
    async for session in supabase[Session].fetchall(query, offset=offset, limit=limit, last_session_id=lsid):
        sessions.append(session)
    return sessions


async def get_sessions_as_traces(offset: int, limit: int) -> AsyncGenerator[Trace, None]:
    """Get sessions and convert them to traces with parallel processing"""
    sessions = await get_sessions(offset, limit)
    for i in range(0, len(sessions), PARALLEL_READS):
        batch = sessions[i : i + PARALLEL_READS]
        tasks = [asyncio.create_task(get_session_as_trace(session)) for session in batch]
        for task in asyncio.as_completed(tasks):
            trace = await task
            print(trace.id)
            yield trace


# Cache for session_id to project_id mapping
_SESSION_PROJECT_CACHE = {}
_SESSION_PROJECT_CACHE_ORDER = []
_SESSION_PROJECT_CACHE_MAX_SIZE = 10000


async def get_project_id_for_session_id(session_id: str) -> str:
    """
    Get the project id for a given session id
    Caches the result for 10,000 sessions
    """
    if not session_id:
        print("Warning: Received empty session_id")
        return None

    # Check cache first
    if session_id in _SESSION_PROJECT_CACHE:
        # Move to the end of the order list to mark as recently used
        # Only try to remove if the session_id is actually in the order list
        if session_id in _SESSION_PROJECT_CACHE_ORDER:
            _SESSION_PROJECT_CACHE_ORDER.remove(session_id)
            _SESSION_PROJECT_CACHE_ORDER.append(session_id)
        else:
            # Fix inconsistency by adding to order list if missing
            _SESSION_PROJECT_CACHE_ORDER.append(session_id)
        return _SESSION_PROJECT_CACHE[session_id]

    query = """
        SELECT * FROM sessions
        WHERE id = '{session_id}'
        LIMIT 1
    """
    result = await supabase[Session].fetchone(query, session_id=session_id)
    if result:
        project_id = result.project_id
        # Add to cache
        if len(_SESSION_PROJECT_CACHE_ORDER) >= _SESSION_PROJECT_CACHE_MAX_SIZE:
            # Remove oldest entry
            oldest_session_id = _SESSION_PROJECT_CACHE_ORDER.pop(0)
            del _SESSION_PROJECT_CACHE[oldest_session_id]
        _SESSION_PROJECT_CACHE[session_id] = project_id
        _SESSION_PROJECT_CACHE_ORDER.append(session_id)
        return project_id
    raise Exception(f"Warning: No project_id found for session_id: {session_id}")


async def get_v2_sourced_rows(limit: int, offset: int) -> list:
    """Get span from ClickHouse that were supplied by v2 exporter"""
    client = await get_async_clickhouse()
    query = """
    SELECT * FROM otel_2.otel_traces
    WHERE mapContains(SpanAttributes, 'session.id')
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        query = query.format(table_name=IMPORT_TABLE_NAME, limit=limit, offset=offset)
        result = await client.query(query)
        if result and hasattr(result, 'result_rows') and len(result.result_rows) > 0:
            rows = []
            for row in result.result_rows:
                row_dict = dict(zip(result.column_names, row))
                rows.append(row_dict)
            return rows
        return []
    except Exception as e:
        print(f"Error fetching rows: {e}")
        return []


async def assign_correct_project_id(span_id: str, project_id: str) -> bool:
    """Assign the correct project id to each row"""
    clickhouse_client = await get_async_clickhouse()
    query = """
    ALTER TABLE otel_2.{table_name} 
    UPDATE ResourceAttributes = mapUpdate(ResourceAttributes, map('agentops.project.id', "{project_id}")) 
    WHERE SpanId = {span_id};
    """
    if project_id is None:
        raise Exception(f"Project id is None for span_id: {span_id}")

    query = query.format(table_name=IMPORT_TABLE_NAME, project_id=project_id, span_id=span_id)
    result = await clickhouse_client.query(query)
    if result.rows_affected > 0:
        return True
    return False


async def count_v2_sourced_rows() -> int:
    """Count the number of rows in the v2 sourced table"""
    clickhouse_client = await get_async_clickhouse()
    query = """
    SELECT COUNT(1) FROM otel_2.otel_traces
    WHERE mapContains(SpanAttributes, 'session.id')
    """
    result = await clickhouse_client.query(query)
    return result.result_rows[0][0]


class _ClickhouseDriverContextShim:
    # i just need context.server_info.get_timezone()
    class ServerInfo:
        def get_timezone(self):
            return 'UTC'  # TODO this is prob not correct

    server_info = ServerInfo()


def clickhouse_escape_param(value: Any) -> str:
    """Escape a parameter for use in a ClickHouse query"""
    # not robust enough to pass a full span for insertion or update :/
    context = _ClickhouseDriverContextShim()
    return _clickhouse_escape_param(value, context)


def clickhouse_escape_value(value: str) -> Any:
    """Escape a value for use in a ClickHouse query"""
    # we don't pass the query to the full escape because it seems like `insert`
    # handles most of it.
    if value is None:
        return 'NULL'
    if isinstance(value, list):
        return [clickhouse_escape_value(v) for v in value]
    if isinstance(value, dict):
        return {k: clickhouse_escape_value(v) for k, v in value.items()}
    if isinstance(value, int):
        return str(value)
    return value


async def clickhouse_create(data: list[dict]) -> None:
    """Create a record in ClickHouse"""
    client = await get_async_clickhouse()

    for i, row in enumerate(data):
        for key, value in row.items():
            data[i][key] = clickhouse_escape_value(value)

    if not DRY_RUN:
        await client.insert(
            table=IMPORT_TABLE_NAME,
            data=[list(row.values()) for row in data],
            column_names=list(data[0].keys()),
        )
    else:
        print(data)


async def clickhouse_create_trace(trace: Trace) -> None:
    """Create a trace in ClickHouse"""
    data = [span.to_clickhouse_dict() for span in trace.spans]
    await clickhouse_create(data)


async def clickhouse_get_span_raw(span_id: str) -> dict:
    """Get raw span data from ClickHouse"""
    client = await get_async_clickhouse()
    query = """
    SELECT * FROM {table_name}
    WHERE SpanId = '{span_id}'
    """
    query = query.format(table_name=IMPORT_TABLE_NAME, span_id=span_id)
    result = await client.query(query)
    if result and hasattr(result, 'result_rows') and len(result.result_rows) > 0:
        row_dict = dict(zip(result.column_names, result.result_rows[0]))
        return row_dict

    return None


async def clickhouse_create_span(span: Span) -> None:
    """Create a single span in ClickHouse"""
    data = [span.to_clickhouse_dict()]
    await clickhouse_create(data)


async def clickhouse_delete_span(span_id: Any) -> None:
    """Delete a span from ClickHouse by SpanId"""
    client = await get_async_clickhouse()
    query = """
    ALTER TABLE {table_name} 
    DELETE WHERE SpanId = '{span_id}'
    """
    query = query.format(table_name=IMPORT_TABLE_NAME, span_id=str(span_id))
    if not DRY_RUN:
        await client.query(query)
    else:
        print(query)


async def clickhouse_update_span(span_id: str, update_data: dict) -> None:
    """Update a record in ClickHouse by deleting and re-inserting it."""
    # reasons for going this route at the moment:
    # - serialization is a bitch and there is no tooling readily available to help with it
    # - latency for propagation of updates is apparently comparable to deletion

    def merge_dicts_recursive(old, new):
        result = old.copy()
        for key, value in new.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts_recursive(result[key], value)
            else:
                result[key] = value
        return result

    existing_span: dict = await clickhouse_get_span_raw(span_id)
    if existing_span:
        await clickhouse_delete_span(span_id)  # yolo
    else:
        existing_span = {}

    merged_data = merge_dicts_recursive(existing_span, update_data)
    await clickhouse_create(
        [
            merged_data,
        ]
    )


async def write_trace_with_timeout(trace: Trace) -> None:
    """Write a trace to ClickHouse with a timeout"""
    try:
        write_task = asyncio.create_task(clickhouse_create_trace(trace))
        await asyncio.wait_for(write_task, timeout=TIMEOUT)
        return True
    except asyncio.TimeoutError:
        write_dropped_record('trace', trace.id, "Timeout")
        return False
    except Exception as e:
        write_dropped_record('trace', trace.id, str(e))
        return False


async def process_page(offset: int, limit: int) -> None:
    """Process a page of sessions and write them to ClickHouse"""
    pending_tasks = set()
    async for trace in get_sessions_as_traces(offset=offset, limit=limit):
        if len(pending_tasks) >= MAX_CONCURRENT:
            done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                await task

        task = asyncio.create_task(write_trace_with_timeout(trace))
        pending_tasks.add(task)

    if pending_tasks:  # let the pool drain
        done, pending = await asyncio.wait(pending_tasks)
        for task in done:
            await task
        await close_supabase_pool()


async def count_session_rows() -> int:
    """Count the number of rows in the sessions table"""
    query = """
        SELECT COUNT(*) FROM sessions
        WHERE id > '{last_session_id}'
    """
    query = query.format(
        last_session_id=LAST_SESSION_ID if LAST_SESSION_ID else '00000000-0000-0000-0000-000000000000'
    )
    async with get_supabase_pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query)
            rows = await cur.fetchone()
    return rows[0]


def init_files():
    """Initialize files needed for the exporter."""
    global _last_session_file, LAST_SESSION_ID

    # Initialize dropped records file
    if not os.path.exists(DROPPED_RECORDS_FILENAME):
        with open(DROPPED_RECORDS_FILENAME, 'w') as f:
            f.write("table,id,exception\n")

    # Initialize last session ID file
    if not os.path.exists(LAST_SESSION_ID_FILENAME):
        from pathlib import Path

        Path(LAST_SESSION_ID_FILENAME).touch()

    # Open the last session ID file
    _last_session_file = open(LAST_SESSION_ID_FILENAME, 'r+')
    LAST_SESSION_ID = _last_session_file.read().strip()


async def main() -> None:
    """Main entry point for the exporter"""
    # Initialize files
    init_files()

    try:
        row_count = await count_session_rows()
        total_pages = row_count // BATCH_ROW_COUNT
        print(f"Total pages: {total_pages}".center(80, "="))

        for page_number in range(0, total_pages):
            offset, limit = page_number * BATCH_ROW_COUNT, BATCH_ROW_COUNT
            await process_page(offset, limit)
            print(f"Processed page {page_number}".center(80, "="))
            if MAX_PAGES is not None and MAX_PAGES >= page_number:
                break
    finally:
        if _last_session_file:
            _last_session_file.close()
        await close_supabase_pool()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv('.env', override=True)

    asyncio.run(main())
