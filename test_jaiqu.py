from agentops.telemetry.jaiqu_transformer import JaiquTransformer
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Create transformer
    logger.info("Creating JaiquTransformer...")
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

    # Fetch spans
    logger.info("Fetching spans...")
    spans = transformer.fetch_spans()
    logger.info(f"Fetched {len(spans)} spans")

    if not spans:
        logger.warning("No spans found in the database")
        sys.exit(0)

    # Transform spans
    logger.info("Transforming spans...")
    transformed_spans = transformer.transform_spans(spans, target_schema)
    logger.info(f"Transformed {len(transformed_spans)} spans")

    # Print transformed spans
    print("\nOriginal Spans:")
    print(json.dumps(spans[:3], indent=2))
    print("\nTransformed Spans:")
    print(json.dumps(transformed_spans[:3], indent=2))

except Exception as e:
    logger.error(f"Error: {str(e)}")
    sys.exit(1)
