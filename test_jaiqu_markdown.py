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
        # Find a span with event.data
        event_span = next(
            (span for span in markdown_spans if span.get('attributes', {}).get('event.data')),
            markdown_spans[0]
        )
        event_index = markdown_spans.index(event_span)
        
        print("\nOriginal Span with event.data:")
        print(json.dumps(event_span, indent=2))
        print("\nEvent Data (parsed):")
        event_data = event_span.get('attributes', {}).get('event.data', '{}')
        try:
            parsed_event_data = json.loads(event_data)
            print(json.dumps(parsed_event_data, indent=2))
        except json.JSONDecodeError:
            print("Could not parse event.data as JSON")
            print(event_data)
        
        print("\nTransformed Span:")
        print(json.dumps(transformed_spans[event_index], indent=2))

except Exception as e:
    logger.error(f"Error: {str(e)}")
    exit(1)
