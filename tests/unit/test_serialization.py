"""Tests for serialization helpers."""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict

import pytest

from agentops.helpers.serialization import (
    filter_unjsonable,
    is_jsonable,
    model_to_dict,
    safe_serialize,
    serialize_uuid,
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


class ModelWithoutDict:
    """A class without __dict__ attribute."""

    __slots__ = ["value"]

    def __init__(self, value: str):
        self.value = value


# Define test cases for is_jsonable
class TestIsJsonable:
    def test_jsonable_types(self):
        """Test that jsonable types return True."""
        jsonable_objects = [
            "string",
            "",
            123,
            123.45,
            True,
            False,
            None,
            [1, 2, 3],
            {"key": "value"},
            [],
            {},
        ]

        for obj in jsonable_objects:
            assert is_jsonable(obj) is True

    def test_unjsonable_types(self):
        """Test that unjsonable types return False."""
        unjsonable_objects = [
            datetime.now(),
            uuid.uuid4(),
            Decimal("123.45"),
            {1, 2, 3},  # set
            SampleEnum.ONE,
            lambda x: x,  # function
            object(),  # generic object
        ]

        for obj in unjsonable_objects:
            assert is_jsonable(obj) is False

    def test_circular_reference(self):
        """Test that circular references are not jsonable."""
        a = {}
        b = {}
        a["b"] = b
        b["a"] = a

        # The current implementation doesn't handle ValueError from circular references
        # So this will raise an exception instead of returning False
        with pytest.raises(ValueError, match="Circular reference detected"):
            is_jsonable(a)


# Define test cases for filter_unjsonable
class TestFilterUnjsonable:
    def test_filter_simple_dict(self):
        """Test filtering of simple dictionary."""
        input_dict = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "uuid": uuid.uuid4(),
            "datetime": datetime.now(),
            "set": {1, 2, 3},
        }

        result = filter_unjsonable(input_dict)

        # Check that jsonable values are preserved
        assert result["string"] == "value"
        assert result["number"] == 42
        assert result["list"] == [1, 2, 3]
        assert result["dict"] == {"nested": "value"}

        # Check that unjsonable values are converted to strings or empty strings
        assert isinstance(result["uuid"], str)
        assert result["datetime"] == ""
        assert result["set"] == ""

    def test_filter_nested_dict(self):
        """Test filtering of nested dictionaries."""
        input_dict = {
            "level1": {
                "level2": {
                    "uuid": uuid.uuid4(),
                    "string": "preserved",
                    "datetime": datetime.now(),
                }
            },
            "list_with_unjsonable": [
                {"uuid": uuid.uuid4()},
                "string",
                datetime.now(),
            ],
        }

        result = filter_unjsonable(input_dict)

        # Check nested structure is preserved
        assert result["level1"]["level2"]["string"] == "preserved"
        assert isinstance(result["level1"]["level2"]["uuid"], str)
        assert result["level1"]["level2"]["datetime"] == ""

        # Check list filtering
        assert result["list_with_unjsonable"][1] == "string"
        assert isinstance(result["list_with_unjsonable"][0]["uuid"], str)
        assert result["list_with_unjsonable"][2] == ""

    def test_filter_list(self):
        """Test filtering of lists."""
        input_list = [
            "string",
            42,
            uuid.uuid4(),
            datetime.now(),
            [1, 2, uuid.uuid4()],
            {"uuid": uuid.uuid4()},
        ]

        result = filter_unjsonable(input_list)

        assert result[0] == "string"
        assert result[1] == 42
        assert isinstance(result[2], str)  # UUID converted to string
        assert result[3] == ""  # datetime converted to empty string
        assert isinstance(result[4][2], str)  # nested UUID converted to string
        assert isinstance(result[5]["uuid"], str)  # nested UUID converted to string

    def test_filter_empty_structures(self):
        """Test filtering of empty structures."""
        assert filter_unjsonable({}) == {}
        assert filter_unjsonable([]) == []
        assert filter_unjsonable({"empty": {}}) == {"empty": {}}


# Define test cases for serialize_uuid
class TestSerializeUuid:
    def test_serialize_uuid(self):
        """Test UUID serialization."""
        test_uuid = uuid.uuid4()
        result = serialize_uuid(test_uuid)

        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_serialize_uuid_string(self):
        """Test that UUID string representation is correct."""
        test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")
        result = serialize_uuid(test_uuid)

        assert result == "00000000-0000-0000-0000-000000000001"


# Define test cases for safe_serialize
class TestSafeSerialize:
    def test_strings_returned_untouched(self):
        """Test that strings are returned untouched."""
        test_strings = [
            "simple string",
            "",
            "special chars: !@#$%^&*()",
            '{"json": "string"}',  # JSON as a string
            "[1, 2, 3]",  # JSON array as a string
            "line 1\nline 2",  # String with newlines
        ]

        for input_str in test_strings:
            # The string should be returned exactly as is
            assert safe_serialize(input_str) == input_str

    def test_complex_objects_serialized(self):
        """Test that complex objects are properly serialized."""
        test_cases = [
            # Test case, expected serialized form (or None for dict check)
            ({"key": "value"}, '{"key": "value"}'),
            ([1, 2, 3], "[1, 2, 3]"),
            (123, "123"),
            (123.45, "123.45"),
            (True, "true"),
            (False, "false"),
            (None, "null"),
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
            (uuid.UUID("00000000-0000-0000-0000-000000000001"), '"00000000-0000-0000-0000-000000000001"'),
            # Decimal
            (Decimal("123.45"), '"123.45"'),
            # Set
            ({1, 2, 3}, "[1, 2, 3]"),
            # Enum
            (SampleEnum.ONE, "1"),
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

    def test_serialization_error_handling(self):
        """Test handling of serialization errors."""

        # Create an object that causes JSON serialization to fail
        class BadObject:
            def __init__(self):
                self.recursive = None

            def __getitem__(self, key):
                # This will cause infinite recursion during JSON serialization
                return self.recursive

            def __str__(self):
                return "BadObject representation"

        bad_obj = BadObject()
        bad_obj.recursive = bad_obj

        result = safe_serialize(bad_obj)
        assert result == '"BadObject representation"'

    def test_value_error_handling(self):
        """Test handling of ValueError during JSON serialization."""

        # Create an object that causes a ValueError during JSON serialization
        class ValueErrorObject:
            def to_json(self):
                raise ValueError("Cannot serialize this object")

            def __str__(self):
                return "ValueErrorObject representation"

        obj = ValueErrorObject()
        result = safe_serialize(obj)
        assert result == "ValueErrorObject representation"


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

    def test_dict_fallback_exception_handling(self):
        """Test exception handling in dict fallback."""
        # Test with object that has no __dict__ attribute
        model_without_dict = ModelWithoutDict("test value")
        assert model_to_dict(model_without_dict) == {}

        # Test with object that raises exception when accessing __dict__
        class BadModel:
            @property
            def __dict__(self):
                raise AttributeError("No dict for you!")

        bad_model = BadModel()
        assert model_to_dict(bad_model) == {}
