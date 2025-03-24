"""Tests for serialization helpers."""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Dict, List, Optional

import pytest
from pydantic import BaseModel

from agentops.helpers.serialization import (
    AgentOpsJSONEncoder,
    filter_unjsonable,
    is_jsonable,
    model_to_dict,
    safe_serialize,
)


# Define test models and data structures
class SampleEnum(Enum):
    ONE = 1
    TWO = 2
    THREE = "three"


class SimpleModel:
    """A simple class with __dict__ but no model_dump or dict method."""
    def __init__(self, value: str):
        self.value = value


class ModelWithToJson:
    """A class that implements to_json method."""
    def __init__(self, data: Dict):
        self.data = data
        
    def to_json(self):
        return self.data


class PydanticV1Model:
    """Mock Pydantic v1 model with dict method."""
    def __init__(self, **data):
        self.__dict__.update(data)
        
    def dict(self):
        return self.__dict__


class PydanticV2Model:
    """Mock Pydantic v2 model with model_dump method."""
    def __init__(self, **data):
        self.__dict__.update(data)
        
    def model_dump(self):
        return self.__dict__


class ModelWithParse:
    """Mock model with parse method."""
    def __init__(self, data):
        self.data = data
        
    def parse(self):
        return self.data


# Define test cases for safe_serialize
class TestSafeSerialize:
    def test_strings_returned_untouched(self):
        """Test that strings are returned untouched."""
        test_strings = [
            "simple string",
            "",
            "special chars: !@#$%^&*()",
            "{\"json\": \"string\"}",  # JSON as a string
            "[1, 2, 3]",               # JSON array as a string
            "line 1\nline 2",          # String with newlines
        ]
        
        for input_str in test_strings:
            # The string should be returned exactly as is
            assert safe_serialize(input_str) == input_str
    
    def test_complex_objects_serialized(self):
        """Test that complex objects are properly serialized."""
        test_cases = [
            # Test case, expected serialized form (or None for dict check)
            ({"key": "value"}, '{"key": "value"}'),
            ([1, 2, 3], '[1, 2, 3]'),
            (123, '123'),
            (123.45, '123.45'),
            (True, 'true'),
            (False, 'false'),
            (None, 'null'),
        ]
        
        for input_obj, expected in test_cases:
            result = safe_serialize(input_obj)
            if expected is not None:
                # Check exact match for simple cases
                assert json.loads(result) == json.loads(expected)
            else:
                # For complex cases just verify it's valid JSON
                assert isinstance(result, str)
                assert json.loads(result) is not None
    
    def test_pydantic_models(self):
        """Test serialization of Pydantic-like models."""
        # V1 model with dict()
        v1_model = PydanticV1Model(name="test", value=42)
        v1_result = safe_serialize(v1_model)
        assert json.loads(v1_result) == {"name": "test", "value": 42}
        
        # V2 model with model_dump()
        v2_model = PydanticV2Model(name="test", value=42)
        v2_result = safe_serialize(v2_model)
        assert json.loads(v2_result) == {"name": "test", "value": 42}
        
        # Note: parse() method is currently not implemented due to recursion issues
        # See TODO in serialization.py
    
    def test_special_types(self):
        """Test serialization of special types using AgentOpsJSONEncoder."""
        test_cases = [
            # Datetime
            (datetime(2023, 1, 1, 12, 0, 0), '"2023-01-01T12:00:00"'),
            # UUID
            (uuid.UUID('00000000-0000-0000-0000-000000000001'), '"00000000-0000-0000-0000-000000000001"'),
            # Decimal
            (Decimal('123.45'), '"123.45"'),
            # Set
            ({1, 2, 3}, '[1, 2, 3]'),
            # Enum
            (SampleEnum.ONE, '1'),
            (SampleEnum.THREE, '"three"'),
            # Class with to_json
            (ModelWithToJson({"key": "value"}), '{"key": "value"}'),
        ]
        
        for input_obj, expected in test_cases:
            result = safe_serialize(input_obj)
            
            # Handle list comparison for sets where order might vary
            if isinstance(input_obj, set):
                assert sorted(json.loads(result)) == sorted(json.loads(expected))
            else:
                assert json.loads(result) == json.loads(expected)
    
    def test_nested_objects(self):
        """Test serialization of nested objects."""
        nested_obj = {
            "string": "value",
            "number": 42,
            "list": [1, 2, {"inner": "value"}],
            "dict": {"inner": {"deeper": [1, 2, 3]}},
            "model": PydanticV2Model(name="test"),
        }
        
        result = safe_serialize(nested_obj)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed["string"] == "value"
        assert parsed["number"] == 42
        assert parsed["list"][2]["inner"] == "value"
        assert parsed["dict"]["inner"]["deeper"] == [1, 2, 3]
        
        # Just verify we have the model in some form
        assert "model" in parsed
        # And verify it contains the expected data in some form
        assert "test" in str(parsed["model"])
    
    def test_fallback_to_str(self):
        """Test fallback to str() for unserializable objects."""
        class Unserializable:
            def __str__(self):
                return "Unserializable object"
        
        obj = Unserializable()
        result = safe_serialize(obj)
        # The string is wrapped in quotes because it's serialized as a JSON string
        assert result == '"Unserializable object"'


class TestModelToDict:
    def test_none_returns_empty_dict(self):
        """Test that None returns an empty dict."""
        assert model_to_dict(None) == {}
    
    def test_dict_returns_unchanged(self):
        """Test that a dict is returned unchanged."""
        test_dict = {"key": "value"}
        assert model_to_dict(test_dict) is test_dict
    
    def test_pydantic_models(self):
        """Test conversion of Pydantic-like models to dicts."""
        # V1 model with dict()
        v1_model = PydanticV1Model(name="test", value=42)
        assert model_to_dict(v1_model) == {"name": "test", "value": 42}
        
        # V2 model with model_dump()
        v2_model = PydanticV2Model(name="test", value=42)
        assert model_to_dict(v2_model) == {"name": "test", "value": 42}
    
    @pytest.mark.skip(reason="parse() method handling is currently commented out in the implementation")
    def test_parse_method(self):
        """Test models with parse method."""
        parse_model = ModelWithParse({"name": "test", "value": 42})
        assert model_to_dict(parse_model) == {"name": "test", "value": 42}
    
    def test_dict_fallback(self):
        """Test fallback to __dict__."""
        simple_model = SimpleModel("test value")
        assert model_to_dict(simple_model) == {"value": "test value"}