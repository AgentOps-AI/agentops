from agentops.telemetry.jaiqu_transformer import JaiquTransformer
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create transformer
transformer = JaiquTransformer(
    host='localhost',
    port=5432,
    database='agentops_test',
    user='postgres',
    password='postgres',
    table_name='otel_spans'
)

# Define target schema
target_schema = {
    'type': 'object',
    'properties': {
        'id': {'type': 'string'},
        'trace_id': {'type': 'string'},
        'parent_id': {'type': 'string'},
        'operation': {'type': 'string'},
        'service': {'type': 'string'},
        'start': {'type': 'string', 'format': 'date-time'},
        'end': {'type': 'string', 'format': 'date-time'},
        'status': {
            'type': 'object',
            'properties': {
                'code': {'type': 'integer'},
                'message': {'type': 'string'}
            }
        },
        'attributes': {'type': 'object'}
    },
    'required': ['id', 'trace_id', 'operation', 'service', 'start', 'end']
}

try:
    # Fetch spans
    spans = transformer.fetch_spans()
    logger.info(f"Fetched {len(spans)} spans")
    
    # Filter spans by service name
    markdown_spans = [
        span for span in spans 
        if span.get('service_name') == 'agentops-markdown-test'
    ]
    logger.info(f"Found {len(markdown_spans)} spans for service agentops-markdown-test")
    
    if not markdown_spans:
        logger.warning("No spans found for service agentops-markdown-test")
        exit(0)
    
    # Transform spans
    transformed_spans = transformer.transform_spans(markdown_spans, target_schema)
    logger.info(f"Transformed {len(transformed_spans)} spans")
    
    # Print a sample of original and transformed spans
    if markdown_spans and transformed_spans:
        print("\nSample Original Span:")
        print(json.dumps(markdown_spans[0], indent=2))
        print("\nSample Transformed Span:")
        print(json.dumps(transformed_spans[0], indent=2))

except Exception as e:
    logger.error(f"Error: {str(e)}")
    exit(1)
