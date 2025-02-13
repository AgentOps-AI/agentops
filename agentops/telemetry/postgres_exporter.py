"""PostgreSQL exporter for OpenTelemetry spans.

This exporter implements the OpenTelemetry SpanExporter interface to store spans
in a PostgreSQL database for long-term storage and analytics via Jaiqu.
"""

import json
import logging
from typing import Sequence, Optional, Dict, Any
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import execute_batch
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import SpanKind
from opentelemetry.util import types


class PostgresSpanExporter(SpanExporter):
    """Export spans to PostgreSQL database.
    
    This exporter implements the OpenTelemetry SpanExporter interface to store spans
    in a PostgreSQL database. It ensures proper parent-child relationships are maintained
    and provides robust error handling and logging.
    
    The exporter creates a table with the following schema:
    - trace_id: Unique identifier for the trace (session)
    - span_id: Unique identifier for the span
    - parent_span_id: ID of the parent span (for hierarchy)
    - name: Name of the span
    - kind: SpanKind value
    - start_time: Start time in nanoseconds since epoch
    - end_time: End time in nanoseconds since epoch
    - status_code: Status code of the span
    - status_message: Status message if any
    - attributes: JSON of span attributes
    - service_name: Name of the service
    - resource_attributes: JSON of resource attributes
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_name: str = "otel_spans",
        max_retry_attempts: int = 3,
    ):
        """Initialize the PostgreSQL exporter.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            table_name: Name of the table to store spans
        """
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        self.table_name = table_name
        self.max_retry_attempts = max_retry_attempts
        self.logger = logging.getLogger(__name__)
        self._ensure_table_exists()
        
    @contextmanager
    def _get_connection(self):
        """Get a database connection with error handling."""
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
        except psycopg2.Error as e:
            self.logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                
    def _ensure_table_exists(self):
        """Create the spans table if it doesn't exist."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id SERIAL PRIMARY KEY,
                            trace_id TEXT NOT NULL,
                            span_id TEXT NOT NULL,
                            parent_span_id TEXT,
                            name TEXT NOT NULL,
                            kind INTEGER NOT NULL,
                            start_time BIGINT NOT NULL,
                            end_time BIGINT NOT NULL,
                            status_code INTEGER,
                            status_message TEXT,
                            attributes JSONB,
                            service_name TEXT,
                            resource_attributes JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(trace_id, span_id)
                        );
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_trace_id 
                            ON {self.table_name}(trace_id);
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_service_name 
                            ON {self.table_name}(service_name);
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_start_time 
                            ON {self.table_name}(start_time);
                    """)
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Error creating table: {e}")
            raise

    def _validate_span(self, span: ReadableSpan) -> bool:
        """Validate span data for proper parent-child relationships.
        
        Args:
            span: The span to validate.
            
        Returns:
            bool: True if span is valid, False otherwise.
        """
        if not span.context:
            self.logger.error(f"Span {span.name} has no context")
            return False
            
        if span.parent and not span.parent.span_id:
            self.logger.error(
                f"Span {span.name} has parent but no parent span ID"
            )
            return False
            
        return True
        
    def _prepare_span_data(self, span: ReadableSpan) -> Optional[tuple]:
        """Prepare span data for database insertion.
        
        Args:
            span: The span to prepare data for.
            
        Returns:
            tuple: Prepared data tuple or None if invalid.
        """
        try:
            if not self._validate_span(span):
                return None
                
            status = span.status
            resource = span.resource.attributes
            attributes = dict(span.attributes) if span.attributes else {}
            
            # Ensure service name is set at both resource and span levels
            service_name = resource.get("service.name")
            if service_name:
                attributes["service.name"] = service_name
            
            return (
                format(span.context.trace_id, "032x"),
                format(span.context.span_id, "016x"),
                format(span.parent.span_id, "016x") if span.parent else None,
                span.name,
                span.kind.value,
                span.start_time,
                span.end_time,
                status.status_code.value if status else None,
                status.description if status else None,
                json.dumps(attributes),
                service_name,
                json.dumps(dict(resource)) if resource else None
            )
        except Exception as e:
            self.logger.error(f"Error preparing span data: {e}")
            return None
    
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export the spans to PostgreSQL.
        
        Args:
            spans: The spans to export.
            
        Returns:
            The result of the export operation.
        """
        if not spans:
            return SpanExportResult.SUCCESS
            
        values = []
        for span in spans:
            span_data = self._prepare_span_data(span)
            if span_data:
                values.append(span_data)
                
        if not values:
            self.logger.warning("No valid spans to export")
            return SpanExportResult.SUCCESS
            
        for attempt in range(self.max_retry_attempts):
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        # Execute batch insert
                        execute_batch(cur, f"""
                            INSERT INTO {self.table_name} (
                                trace_id, span_id, parent_span_id, name, kind,
                                start_time, end_time, status_code, status_message,
                                attributes, service_name, resource_attributes
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            ) ON CONFLICT (trace_id, span_id) DO NOTHING
                        """, values)
                        conn.commit()
                        
                self.logger.info(f"Successfully exported {len(values)} spans")
                return SpanExportResult.SUCCESS
                
            except psycopg2.Error as e:
                self.logger.error(
                    f"Database error on attempt {attempt + 1}/{self.max_retry_attempts}: {e}"
                )
                if attempt == self.max_retry_attempts - 1:
                    return SpanExportResult.FAILURE
                    
            except Exception as e:
                self.logger.error(f"Unexpected error during export: {e}")
                return SpanExportResult.FAILURE
            
    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush any pending spans.
        
        Args:
            timeout_millis: The maximum time to wait in milliseconds.
            
        Returns:
            bool: True if the flush was successful, False otherwise.
        """
        return True

    def shutdown(self):
        """Shutdown the exporter.
        
        This is a no-op for this exporter as connections are managed per export.
        """
        pass
