from fastapi import FastAPI, Request, HTTPException, Response
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2
from celery import Celery
from pydantic import BaseModel
from typing import Dict, Any
import logging
import json
import gzip
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Span Processing Service")
celery_app = Celery('tasks', broker='redis://redis:6379/0')

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
        # Your processing logic here
        # For example:
        logger.info(f"Processing span: {name} (trace_id: {trace_id}, span_id: {span_id})")
        # Add your storage/processing logic here

        # Just dump the span payload
        json.dumps({
            "trace_id": trace_id,
            "span_id": span_id,
            "name": name,
            "attributes": attributes
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error processing span {span_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
