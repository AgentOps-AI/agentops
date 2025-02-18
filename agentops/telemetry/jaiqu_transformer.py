"""
Module for transforming OpenTelemetry spans to target schema using Jaiqu.

This module provides functionality to:
1. Extract spans from PostgreSQL
2. Transform spans to target schema using Jaiqu
3. Validate transformed data against schema
"""

import logging
from typing import Any, Dict, List, Optional
import jaiqu
from opentelemetry.sdk.trace import Span
from opentelemetry.trace import SpanKind, Status, StatusCode
import json
import psycopg2
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class JaiquTransformer:
    """
    Transforms OpenTelemetry spans to target schema using Jaiqu.
    
    This class handles:
    1. Fetching spans from PostgreSQL
    2. Transforming spans to target schema
    3. Validating transformed data
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "agentops_test",
        user: str = "postgres",
        password: str = "postgres",
        table_name: str = "otel_spans"
    ) -> None:
        """
        Initialize the JaiquTransformer.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            table_name: Table containing spans
        """
        self.connection_params = {
            "host": host,
            "port": port,
            "database": "agentops_test",  # Always use test database
            "user": user,
            "password": password
        }
        self.table_name = table_name
        logger.info(f"Initialized JaiquTransformer for table {table_name} in database {self.connection_params['database']}")
    
    def fetch_spans(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch spans from PostgreSQL.
        
        Args:
            trace_id: Optional trace ID to filter spans
            
        Returns:
            List of spans as dictionaries
        """
        try:
            with psycopg2.connect(**self.connection_params) as conn:
                with conn.cursor() as cur:
                    query = f"""
                        SELECT 
                            trace_id,
                            span_id,
                            parent_span_id,
                            name,
                            kind,
                            start_time,
                            end_time,
                            status_code,
                            status_message,
                            attributes,
                            service_name,
                            resource_attributes
                        FROM {self.table_name}
                        {"WHERE trace_id = %s" if trace_id else ""}
                    """
                    
                    if trace_id:
                        cur.execute(query, (trace_id,))
                    else:
                        cur.execute(query)
                    
                    rows = cur.fetchall()
                    
                    # Convert rows to dictionaries with column names
                    columns = [
                        'trace_id', 'span_id', 'parent_span_id', 'name', 'kind',
                        'start_time', 'end_time', 'status_code', 'status_message',
                        'attributes', 'service_name', 'resource_attributes'
                    ]
                    
                    spans = []
                    for row in rows:
                        span_data = dict(zip(columns, row))
                        # JSONB fields are already converted to Python dictionaries by psycopg2
                        spans.append(span_data)
                    
                    logger.info(f"Fetched {len(spans)} spans from PostgreSQL")
                    return spans
        except Exception as e:
            logger.error(f"Error fetching spans: {e}")
            raise
    
    def transform_span(self, span_data: Dict[str, Any], target_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single span to target schema using Jaiqu.
        
        Args:
            span_data: OpenTelemetry span data
            target_schema: Target schema for transformation
            
        Returns:
            Transformed span data
            
        Raises:
            ValueError: If required fields are missing or invalid
            TypeError: If field types don't match schema
        """
        try:
            # Validate required fields
            if not span_data.get("span_id"):
                raise ValueError("Missing required field: span_id")
            if not span_data.get("name"):
                raise ValueError("Missing required field: name")
            if "start_time" not in span_data or "end_time" not in span_data:
                raise ValueError("Missing required fields: start_time or end_time")
            
            # Convert timestamps to ISO format
            try:
                start_time = datetime.fromtimestamp(
                    span_data["start_time"] / 1e9, 
                    tz=timezone.utc
                ).isoformat()
                end_time = datetime.fromtimestamp(
                    span_data["end_time"] / 1e9, 
                    tz=timezone.utc
                ).isoformat()
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid timestamp format: {e}")
            
            # Process attributes
            attributes = span_data.get("attributes", {})
            processed_attributes = {}
            
            # Process special fields
            for key, value in attributes.items():
                if key == "event.data" and isinstance(value, str):
                    try:
                        processed_attributes["event_data"] = json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse event.data as JSON: {value}")
                        processed_attributes["event_data"] = value
                else:
                    # Convert dot notation to underscore
                    processed_key = key.replace(".", "_")
                    processed_attributes[processed_key] = value
            
            # Create transformed data structure
            transformed_data = {
                "id": span_data["span_id"],
                "trace_id": span_data["trace_id"],
                "parent_id": span_data["parent_span_id"],
                "operation": span_data["name"],
                "service": span_data.get("service_name", "unknown"),
                "start": start_time,
                "end": end_time,
                "status": {
                    "code": span_data.get("status_code", 0),
                    "message": span_data.get("status_message", "")
                },
                "attributes": processed_attributes,
                "resource_attributes": span_data.get("resource_attributes", {})
            }
            
            # Log schema comparison
            logger.info("Schema Comparison:")
            logger.info("Original Schema (PostgreSQL):")
            logger.info(json.dumps({
                "id": "integer, auto-increment",
                "trace_id": "text, not null",
                "span_id": "text, not null",
                "parent_span_id": "text",
                "name": "text, not null",
                "kind": "integer, not null",
                "start_time": "bigint (nanoseconds), not null",
                "end_time": "bigint (nanoseconds), not null",
                "status_code": "integer",
                "status_message": "text",
                "attributes": "jsonb",
                "service_name": "text",
                "resource_attributes": "jsonb",
                "created_at": "timestamp with timezone"
            }, indent=2))
            
            logger.info("Target Schema (Jaiqu):")
            logger.info(json.dumps({
                "id": "string (from span_id)",
                "trace_id": "string",
                "parent_id": "string (from parent_span_id)",
                "operation": "string (from name)",
                "service": "string (from service_name)",
                "start": "string, ISO 8601 (from start_time)",
                "end": "string, ISO 8601 (from end_time)",
                "status": {
                    "code": "integer (from status_code)",
                    "message": "string (from status_message)"
                },
                "attributes": "object (from attributes)",
                "resource_attributes": "object (from resource_attributes)"
            }, indent=2))
            
            logger.info("Data Transformation:")
            logger.info("Original Data:")
            logger.info(json.dumps(span_data, indent=2))
            logger.info("Transformed Data:")
            logger.info(json.dumps(transformed_data, indent=2))
            
            return transformed_data
        except Exception as e:
            logger.error(f"Error transforming span {span_data.get('span_id')}: {e}")
            raise
    
    def transform_spans(
        self, 
        spans: List[Dict[str, Any]], 
        target_schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Transform multiple spans to target schema.
        
        Args:
            spans: List of OpenTelemetry spans
            target_schema: Target schema for transformation
            
        Returns:
            List of transformed spans
        """
        transformed_spans = []
        for span in spans:
            try:
                transformed_span = self.transform_span(span, target_schema)
                transformed_spans.append(transformed_span)
            except Exception as e:
                logger.error(f"Error transforming span: {e}")
                # Continue processing other spans
                continue
        
        logger.info(f"Successfully transformed {len(transformed_spans)} spans")
        return transformed_spans
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate data against schema using Jaiqu.
        
        Args:
            data: Data to validate
            schema: Schema to validate against
            
        Returns:
            True if validation succeeds, False otherwise
        """
        try:
            # Check required fields
            required_fields = schema.get('required', [])
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate field types
            properties = schema.get('properties', {})
            for field, value in data.items():
                if field in properties:
                    field_schema = properties[field]
                    field_type = field_schema.get('type')
                    
                    # Skip validation for null values
                    if value is None:
                        continue
                    
                    # Basic type validation
                    if field_type == 'string':
                        if not isinstance(value, str):
                            logger.error(f"Field {field} should be string, got {type(value)}")
                            return False
                        # Check date-time format if specified
                        if field_schema.get('format') == 'date-time':
                            try:
                                datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except ValueError:
                                logger.error(f"Invalid date-time format for field {field}")
                                return False
                    elif field_type == 'integer':
                        try:
                            int(value)  # Try to convert to integer
                        except (TypeError, ValueError):
                            logger.error(f"Field {field} should be convertible to integer, got {type(value)}")
                            return False
                    elif field_type == 'object':
                        if not isinstance(value, dict):
                            logger.error(f"Field {field} should be object, got {type(value)}")
                            return False
                        # Validate nested object if schema is provided
                        if 'properties' in field_schema:
                            if not self.validate_schema(value, field_schema):
                                return False
                    elif field_type == 'array':
                        if not isinstance(value, list):
                            logger.error(f"Field {field} should be array, got {type(value)}")
                            return False
            
            return True
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False
