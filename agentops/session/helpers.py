from uuid import UUID

from opentelemetry.util.types import Attributes, AttributeValue


def trace_id_to_uuid(trace_id: int) -> UUID:
    # Convert the trace_id to a 32-character hex string
    trace_id_hex = format(trace_id, '032x')
    
    # Format as UUID string (8-4-4-4-12)
    uuid_str = f"{trace_id_hex[0:8]}-{trace_id_hex[8:12]}-{trace_id_hex[12:16]}-{trace_id_hex[16:20]}-{trace_id_hex[20:32]}"
    
    # Create UUID object
    return UUID(uuid_str)

def dict_to_span_attributes(data: dict, prefix: str = "") -> Attributes:
    """Convert a dictionary to OpenTelemetry span attributes.
    
    Follows OpenTelemetry AttributeValue type constraints:
    - str
    - bool
    - int
    - float
    - Sequence[str]
    - Sequence[bool]
    - Sequence[int]
    - Sequence[float]
    
    Args:
        data: Dictionary to convert
        prefix: Optional prefix for attribute names (e.g. "session.")
        
    Returns:
        Dictionary of span attributes with flattened structure
    """
    attributes: dict[str, AttributeValue] = {}
    
    def _flatten(obj, parent_key=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                if prefix:
                    new_key = f"{prefix}{new_key}"
                
                if isinstance(value, dict):
                    _flatten(value, new_key)
                elif isinstance(value, (str, bool, int, float)):
                    attributes[new_key] = value
                elif isinstance(value, (list, tuple)):
                    # Only include sequences if they contain valid types
                    if value and all(isinstance(x, str) for x in value):
                        attributes[new_key] = list(value)
                    elif value and all(isinstance(x, bool) for x in value):
                        attributes[new_key] = list(value)
                    elif value and all(isinstance(x, int) for x in value):
                        attributes[new_key] = list(value)
                    elif value and all(isinstance(x, float) for x in value):
                        attributes[new_key] = list(value)
                    else:
                        # Convert mixed/unsupported sequences to string
                        attributes[new_key] = ",".join(str(x) for x in value)
                else:
                    # Convert unsupported types to string
                    attributes[new_key] = str(value)
    
    _flatten(data)
    return attributes
