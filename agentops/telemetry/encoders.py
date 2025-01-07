"""
Generic encoder for converting dataclasses to OpenTelemetry spans.
"""

from dataclasses import is_dataclass, fields
from typing import Any, Dict, Optional, Type, TypeVar
from uuid import UUID
import json

from opentelemetry.trace import SpanKind
from opentelemetry.util.types import AttributeValue
from opentelemetry.semconv.trace import SpanAttributes

from agentops.event import Event


T = TypeVar('T')

def span_safe(value: Any) -> AttributeValue:
    """Convert value to OTEL-compatible attribute value"""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)

class DataclassSpanEncoder:
    """Encodes dataclasses into OpenTelemetry spans using field names as attributes"""
    
    @staticmethod
    def get_span_name(obj: Any) -> str:
        """Generate span name from class name"""
        return obj.__class__.__name__.lower()

    @staticmethod
    def get_span_attributes(obj: Any) -> Dict[str, AttributeValue]:
        """Convert all dataclass fields to span attributes"""
        if not is_dataclass(obj):
            raise ValueError(f"Object {obj} is not a dataclass")

        attributes = {}
        for field in fields(obj):
            value = getattr(obj, field.name)
            if value is not None:  # Skip None values
                attributes[field.name] = span_safe(value)
        
        return attributes

    @staticmethod
    def encode(obj: Any, kind: Optional[SpanKind] = None) -> 'SpanDefinition':
        """Encode a dataclass instance into a SpanDefinition"""
        return SpanDefinition(
            name=DataclassSpanEncoder.get_span_name(obj),
            attributes=DataclassSpanEncoder.get_span_attributes(obj),
            kind=kind or SpanKind.INTERNAL
        )

class EventToSpanEncoder(DataclassSpanEncoder):
    """Encodes AgentOps events into OpenTelemetry spans with semantic conventions"""

    @staticmethod
    def get_span_attributes(obj: Event) -> Dict[str, AttributeValue]:
        """Convert event fields to span attributes with semantic conventions"""
        # Get base attributes from dataclass
        base_attributes = DataclassSpanEncoder.get_span_attributes(obj)
        
        # Common attributes for all events
        attributes = {
            SpanAttributes.CODE_NAMESPACE: obj.__class__.__name__,
            'event_type': base_attributes.get('event_type'),
            'init_timestamp': base_attributes.get('init_timestamp'),
            'end_timestamp': base_attributes.get('end_timestamp'),
            'id': base_attributes.get('id'),
            'params': base_attributes.get('params'),
            'returns': base_attributes.get('returns'),
        }

        # Add agent_id if present
        if 'agent_id' in base_attributes:
            attributes['agent_id'] = base_attributes['agent_id']

        # Add any remaining fields dynamically
        for key, value in base_attributes.items():
            if key not in attributes and value is not None:
                attributes[key] = value

        return attributes

    @staticmethod
    def get_span_kind(obj: Event) -> SpanKind:
        """Determine appropriate span kind based on event type"""
        # Map event types to span kinds
        event_type = obj.__class__.__name__.lower()
        
        # LLM events are client calls to external services
        if 'llm' in event_type:
            return SpanKind.CLIENT
            
        # Default to INTERNAL for other event types
        return SpanKind.INTERNAL

    @staticmethod
    def encode(obj: Event, kind: Optional[SpanKind] = None) -> 'SpanDefinition':
        """Encode an event into a SpanDefinition with appropriate span kind"""
        return SpanDefinition(
            name=obj.__class__.__name__.lower(),
            attributes=EventToSpanEncoder.get_span_attributes(obj),
            kind=kind or EventToSpanEncoder.get_span_kind(obj)
        )

class SpanDefinition:
    """Defines how a span should be created"""
    def __init__(
        self,
        name: str,
        attributes: Dict[str, AttributeValue],
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
    ):
        self.name = name
        self.attributes = attributes
        self.kind = kind
        self.parent_span_id = parent_span_id
