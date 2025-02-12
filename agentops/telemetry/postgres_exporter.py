"""PostgreSQL exporter for OpenTelemetry spans."""

import json
from typing import Sequence
import psycopg2
from psycopg2.extras import execute_batch
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class PostgresSpanExporter(SpanExporter):
    """Export spans to PostgreSQL database.
    
    This exporter stores OpenTelemetry spans in a PostgreSQL database for
    long-term storage and analytics via Jaiqu.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_name: str = "otel_spans"
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
        self._ensure_table_exists()
        
    def _ensure_table_exists(self):
        """Create the spans table if it doesn't exist."""
        with psycopg2.connect(**self.connection_params) as conn:
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

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export the spans to PostgreSQL.
        
        Args:
            spans: The spans to export.
            
        Returns:
            The result of the export operation.
        """
        try:
            with psycopg2.connect(**self.connection_params) as conn:
                with conn.cursor() as cur:
                    # Prepare the values for batch insert
                    values = []
                    for span in spans:
                        status = span.status
                        resource = span.resource.attributes
                        attributes = dict(span.attributes) if span.attributes else {}
                        
                        values.append((
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
                            resource.get("service.name"),
                            json.dumps(dict(resource)) if resource else None
                        ))
                    
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
                    
            return SpanExportResult.SUCCESS
        except Exception as e:
            return SpanExportResult.FAILURE
            
    def shutdown(self):
        """Shutdown the exporter.
        
        This is a no-op for this exporter as the connection is created/closed
        per export operation.
        """
        pass
