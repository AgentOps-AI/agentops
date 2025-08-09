import base64
import pickle
from typing import Any, Dict


class SpanAttributeEncoder:
    @staticmethod
    def encode(attributes: Dict[str, Any]) -> bytes:
        """Encode span attributes to binary format."""
        return pickle.dumps(attributes)

    @staticmethod
    def decode(binary_data: bytes) -> Dict[str, Any]:
        """Decode binary data to span attributes."""
        return pickle.loads(binary_data)

    @staticmethod
    def encode_to_base64(attributes: Dict[str, Any]) -> str:
        """Encode span attributes to base64 string for debugging."""
        binary_data = SpanAttributeEncoder.encode(attributes)
        return base64.b64encode(binary_data).decode("utf-8")

    @staticmethod
    def decode_from_base64(base64_str: str) -> Dict[str, Any]:
        """Decode base64 string to span attributes for debugging."""
        binary_data = base64.b64decode(base64_str)
        return SpanAttributeEncoder.decode(binary_data)
