from fastapi import FastAPI, Request, HTTPException, Response
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
from celery import Celery
from pydantic import BaseModel
from typing import Dict, Any
import psycopg2
from psycopg2.extras import Json
import jwt
import logging
import json
import gzip
import io
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Span Processing Service")
celery_app = Celery('tasks', broker='redis://redis:6379/0')

# Database connection parameters
DB_PARAMS = {
    "dbname": os.getenv("POSTGRES_DB", "agentops_dev"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": os.getenv("POSTGRES_PORT", "5432")
}

class SpanData(BaseModel):
    trace_id: str
    span_id: str
    name: str
    attributes: Dict[str, Any]

@app.post("/v1/traces")
async def ingest_spans(request: Request):
    try:
        # Get content type and encoding
        content_type = request.headers.get("content-type", "")
        content_encoding = request.headers.get("content-encoding", "")
        
        # Read raw body
        body = await request.body()
        
        # Handle gzip compression if present
        if content_encoding == "gzip":
            with gzip.GzipFile(fileobj=io.BytesIO(body), mode="rb") as gz:
                body = gz.read()

        # Parse the protobuf message
        request_proto = trace_service_pb2.ExportTraceServiceRequest()
        request_proto.ParseFromString(body)

        # Process each resource spans
        for resource_spans in request_proto.resource_spans:
            resource_attrs = {}
            
            # Extract resource attributes
            for attr in resource_spans.resource.attributes:
                resource_attrs[attr.key] = attr.value.string_value

            # Process each scope spans
            for scope_spans in resource_spans.scope_spans:
                # Process each span
                for span in scope_spans.spans:
                    # Extract span attributes
                    span_attrs = {}
                    for attr in span.attributes:
                        span_attrs[attr.key] = attr.value.string_value
                    
                    # Combine resource and span attributes
                    combined_attrs = {**resource_attrs, **span_attrs}
                    
                    # Convert trace and span IDs to hex strings
                    trace_id = span.trace_id.hex()
                    span_id = span.span_id.hex()
                    
                    # Queue span for processing
                    process_span.delay(
                        trace_id=trace_id,
                        span_id=span_id,
                        name=span.name,
                        attributes=combined_attrs
                    )

                    logger.info(f"Queued span for processing: {span.name} (trace_id: {trace_id})")

        return Response(
            content=trace_service_pb2.ExportTraceServiceResponse().SerializeToString(),
            media_type="application/x-protobuf"
        )

    except Exception as e:
        logger.error(f"Error processing spans: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@celery_app.task(bind=True, max_retries=3)
def process_span(self, trace_id: str, span_id: str, name: str, attributes: dict):
    try:
        # Extract JWT and API key from attributes
        jwt_token = attributes.get("jwt")
        api_key = attributes.get("api_key")

        if not jwt_token or not api_key:
            raise Exception("Missing authentication credentials in span attributes")

        try:
            # Verify JWT token
            # Note: JWT_SECRET should be properly configured in production
            payload = jwt.decode(
                jwt_token, 
                os.getenv("JWT_SECRET", "development-secret"),
                algorithms=["HS256"]
            )
            organization_id = payload.get("organization_id")
            user_id = payload.get("user_id")

            if not organization_id or not user_id:
                raise Exception("Invalid JWT payload: missing required claims")

        except jwt.InvalidTokenError as e:
            logger.error(f"JWT verification failed: {str(e)}")
            raise Exception("Invalid JWT token")

        # Prepare event data
        event_data = {
            "trace_id": trace_id,
            "span_id": span_id,
            "name": name,
            "attributes": Json(attributes),  # Use psycopg2.extras.Json for JSONB
            "created_at": datetime.utcnow(),
            "organization_id": organization_id,
            "user_id": user_id
        }

        # Store in database
        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO events (
                        trace_id, span_id, name, attributes, 
                        created_at, organization_id, user_id
                    ) VALUES (
                        %(trace_id)s, %(span_id)s, %(name)s, %(attributes)s,
                        %(created_at)s, %(organization_id)s, %(user_id)s
                    ) RETURNING id
                """, event_data)
                
                event_id = cur.fetchone()[0]
                conn.commit()

        logger.info(f"Successfully stored span {span_id} with event ID {event_id}")
        return {"success": True, "event_id": event_id}

    except Exception as e:
        logger.error(f"Error processing span {span_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
