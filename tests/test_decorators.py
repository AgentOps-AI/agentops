import pytest
from collections import namedtuple
from typing import Tuple
import json

from agentops.decorators import record_action, record_tool
from agentops.client import Client
from agentops.session import Session
from agentops.event import ActionEvent
from agentops.helpers import filter_unjsonable


class TestDecorators:
    # Test data
    Point = namedtuple("Point", ["x", "y"])
    Person = namedtuple("Person", ["name", "age"])
    # Custom namedtuple to test specific subclass behavior mentioned in PR
    CustomTuple = namedtuple("CustomTuple", ["data"])

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset client state before each test"""
        Client._instance = None
        Client().configure(api_key="test_key")

    @staticmethod
    @record_action("test_regular_tuple")
    def function_with_regular_tuple() -> Tuple[int, str]:
        return (1, "test")

    @staticmethod
    @record_action("test_named_tuple")
    def function_with_named_tuple() -> Point:
        return TestDecorators.Point(x=1, y=2)

    @staticmethod
    @record_action("test_multiple_named_tuples")
    def function_with_multiple_named_tuples() -> Tuple[Point, Person]:
        return (TestDecorators.Point(x=1, y=2), TestDecorators.Person(name="John", age=30))

    @staticmethod
    @record_action("test_custom_tuple")
    def function_with_custom_tuple() -> CustomTuple:
        """Test case for PR #608 where code checks for specific tuple subclass"""
        return TestDecorators.CustomTuple(data={"key": "value"})

    @staticmethod
    @record_tool("test_tool_tuple")
    def tool_with_tuple() -> Tuple[int, str]:
        return (1, "test")

    @staticmethod
    @record_tool("test_tool_named_tuple")
    def tool_with_named_tuple() -> Point:
        return TestDecorators.Point(x=1, y=2)

    def test_type_preservation(self):
        """Test that tuple types are preserved after PR #608 changes.
        These tests verify that the decorator no longer modifies return types."""
        # Regular tuple
        result = self.function_with_regular_tuple()
        assert isinstance(result, tuple), "Regular tuples should be preserved"
        assert result == (1, "test")

        # Named tuple
        result = self.function_with_named_tuple()
        assert isinstance(result, self.Point), "Named tuples should be preserved"
        assert result.x == 1
        assert result.y == 2

        # Multiple named tuples
        result = self.function_with_multiple_named_tuples()
        assert isinstance(result, tuple), "Tuple of named tuples should be preserved"
        assert isinstance(result[0], self.Point)
        assert isinstance(result[1], self.Person)
        assert result[0].x == 1
        assert result[1].name == "John"

        # Custom tuple subclass (specific to PR #608 issue)
        result = self.function_with_custom_tuple()
        assert isinstance(result, self.CustomTuple), "Custom tuple subclass should be preserved"
        assert result.data == {"key": "value"}

        # Tool returns
        tool_result = self.tool_with_tuple()
        assert isinstance(tool_result, tuple), "Tool tuples should be preserved"
        assert tool_result == (1, "test")

        tool_named_result = self.tool_with_named_tuple()
        assert isinstance(tool_named_result, self.Point), "Tool named tuples should be preserved"
        assert tool_named_result.x == 1
        assert tool_named_result.y == 2

    def test_json_serialization(self):
        """Test that events can be properly serialized with tuples.
        This demonstrates @teocns's point that JSON serialization works fine with tuples,
        as they are naturally converted to lists during JSON serialization."""
        config = Client()._config
        session = Session(session_id="test_session", config=config)

        # Test with regular tuple
        direct_tuple = (1, "test")
        event1 = ActionEvent(action_type="test_action", params={"test": "params"}, returns=direct_tuple)
        event1_dict = filter_unjsonable(event1.__dict__)
        event1_json = json.dumps(event1_dict)
        assert event1_json, "Event with tuple returns should be JSON serializable"

        # Verify the serialized data structure
        event1_data = json.loads(event1_json)
        assert isinstance(event1_data["returns"], list), "JSON naturally converts tuples to lists"
        assert event1_data["returns"] == [1, "test"], "Tuple data should be preserved in JSON"

        # Test with named tuple
        named_tuple = self.Point(x=1, y=2)
        event2 = ActionEvent(action_type="test_action", params={"test": "params"}, returns=named_tuple)
        event2_dict = filter_unjsonable(event2.__dict__)
        event2_json = json.dumps(event2_dict)
        assert event2_json, "Event with named tuple returns should be JSON serializable"

        # Verify the serialized data structure
        event2_data = json.loads(event2_json)
        assert isinstance(event2_data["returns"], list), "JSON naturally converts named tuples to lists"
        assert event2_data["returns"] == [1, 2], "Named tuple data should be preserved in JSON"

        # Test with custom tuple subclass
        custom_tuple = self.CustomTuple(data={"key": "value"})
        event3 = ActionEvent(action_type="test_action", params={"test": "params"}, returns=custom_tuple)
        event3_dict = filter_unjsonable(event3.__dict__)
        event3_json = json.dumps(event3_dict)
        assert event3_json, "Event with custom tuple subclass should be JSON serializable"

        # Verify the serialized data structure
        event3_data = json.loads(event3_json)
        assert isinstance(event3_data["returns"], list), "JSON naturally converts custom tuples to lists"
        assert event3_data["returns"] == [{"key": "value"}], "Custom tuple data should be preserved in JSON"
