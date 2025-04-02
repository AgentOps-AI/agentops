"""
Unit tests for the common attributes module.

This module tests the functionality of the common attribute processing utilities
shared across all instrumentors, including attribute extraction, common attribute
getters, and base trace/span attribute functions.
"""

import pytest
from unittest.mock import patch

from agentops.instrumentation.common.attributes import (
    _extract_attributes_from_mapping,
    get_common_attributes,
    get_base_trace_attributes,
    get_base_span_attributes,
)
from agentops.semconv import (
    CoreAttributes,
    InstrumentationAttributes,
    WorkflowAttributes,
)


class TestAttributeExtraction:
    """Tests for attribute extraction utilities."""

    def test_extract_attributes_from_object(self):
        """Test extracting attributes from an object."""

        # Create a test object with attributes
        class TestObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42
                self.attr3 = None
                self.attr4 = []
                self.attr5 = {}
                self.attr6 = ["list", "of", "values"]
                self.attr7 = {"key": "value"}

        test_obj = TestObject()

        # Define a mapping of target attributes to source attributes
        mapping = {
            "target_attr1": "attr1",
            "target_attr2": "attr2",
            "target_attr3": "attr3",  # None value, should be skipped
            "target_attr4": "attr4",  # Empty list, should be skipped
            "target_attr5": "attr5",  # Empty dict, should be skipped
            "target_attr6": "attr6",  # List value, should be handled
            "target_attr7": "attr7",  # Dict value, should be handled
            "target_attr8": "missing_attr",  # Missing attribute, should be skipped
        }

        # Extract attributes
        attributes = _extract_attributes_from_mapping(test_obj, mapping)

        # Verify extracted attributes
        assert "target_attr1" in attributes
        assert attributes["target_attr1"] == "value1"
        assert "target_attr2" in attributes
        assert attributes["target_attr2"] == 42
        assert "target_attr3" not in attributes  # None value should be skipped
        assert "target_attr4" not in attributes  # Empty list should be skipped
        assert "target_attr5" not in attributes  # Empty dict should be skipped
        assert "target_attr6" in attributes  # List value should be handled
        assert attributes["target_attr6"] == '["list", "of", "values"]'  # JSON encoded
        assert "target_attr7" in attributes  # Dict value should be handled
        assert attributes["target_attr7"] == '{"key": "value"}'  # JSON encoded
        assert "target_attr8" not in attributes  # Missing attribute should be skipped

    def test_extract_attributes_from_dict(self):
        """Test extracting attributes from a dictionary."""
        # Create a test dictionary
        test_dict = {
            "attr1": "value1",
            "attr2": 42,
            "attr3": None,
            "attr4": [],
            "attr5": {},
            "attr6": ["list", "of", "values"],
            "attr7": {"key": "value"},
        }

        # Define a mapping of target attributes to source attributes
        mapping = {
            "target_attr1": "attr1",
            "target_attr2": "attr2",
            "target_attr3": "attr3",  # None value, should be skipped
            "target_attr4": "attr4",  # Empty list, should be skipped
            "target_attr5": "attr5",  # Empty dict, should be skipped
            "target_attr6": "attr6",  # List value, should be handled
            "target_attr7": "attr7",  # Dict value, should be handled
            "target_attr8": "missing_attr",  # Missing key, should be skipped
        }

        # Extract attributes
        attributes = _extract_attributes_from_mapping(test_dict, mapping)

        # Verify extracted attributes
        assert "target_attr1" in attributes
        assert attributes["target_attr1"] == "value1"
        assert "target_attr2" in attributes
        assert attributes["target_attr2"] == 42
        assert "target_attr3" not in attributes  # None value should be skipped
        assert "target_attr4" not in attributes  # Empty list should be skipped
        assert "target_attr5" not in attributes  # Empty dict should be skipped
        assert "target_attr6" in attributes  # List value should be handled
        assert attributes["target_attr6"] == '["list", "of", "values"]'  # JSON encoded
        assert "target_attr7" in attributes  # Dict value should be handled
        assert attributes["target_attr7"] == '{"key": "value"}'  # JSON encoded
        assert "target_attr8" not in attributes  # Missing key should be skipped


class TestCommonAttributes:
    """Tests for common attribute getters."""

    def test_get_common_attributes(self):
        """Test getting common instrumentation attributes."""
        # Mock the version function to return a fixed value
        with patch("agentops.instrumentation.common.attributes.get_agentops_version", return_value="0.1.2"):
            # Get common attributes
            attributes = get_common_attributes()

            # Verify attributes
            assert InstrumentationAttributes.NAME in attributes
            assert attributes[InstrumentationAttributes.NAME] == "agentops"
            assert InstrumentationAttributes.VERSION in attributes
            assert attributes[InstrumentationAttributes.VERSION] == "0.1.2"

    def test_get_base_trace_attributes_with_valid_trace(self):
        """Test getting base trace attributes with a valid trace."""

        # Create a mock trace
        class MockTrace:
            def __init__(self):
                self.trace_id = "test_trace_id"
                self.name = "test_trace_name"

        mock_trace = MockTrace()

        # Mock the common attributes and tags functions
        with patch(
            "agentops.instrumentation.common.attributes.get_common_attributes",
            return_value={InstrumentationAttributes.NAME: "agentops", InstrumentationAttributes.VERSION: "0.1.2"},
        ):
            # Get base trace attributes
            attributes = get_base_trace_attributes(mock_trace)

            # Verify attributes
            assert CoreAttributes.TRACE_ID in attributes
            assert attributes[CoreAttributes.TRACE_ID] == "test_trace_id"
            assert WorkflowAttributes.WORKFLOW_NAME in attributes
            assert attributes[WorkflowAttributes.WORKFLOW_NAME] == "test_trace_name"
            assert WorkflowAttributes.WORKFLOW_STEP_TYPE in attributes
            assert attributes[WorkflowAttributes.WORKFLOW_STEP_TYPE] == "trace"
            assert InstrumentationAttributes.NAME in attributes
            assert attributes[InstrumentationAttributes.NAME] == "agentops"
            assert InstrumentationAttributes.VERSION in attributes
            assert attributes[InstrumentationAttributes.VERSION] == "0.1.2"

    def test_get_base_trace_attributes_with_invalid_trace(self):
        """Test getting base trace attributes with an invalid trace (missing trace_id)."""

        # Create a mock trace without trace_id
        class MockTrace:
            def __init__(self):
                self.name = "test_trace_name"

        mock_trace = MockTrace()

        # Mock the logger
        with patch("agentops.instrumentation.common.attributes.logger.warning") as mock_warning:
            # Get base trace attributes
            attributes = get_base_trace_attributes(mock_trace)

            # Verify logger was called
            mock_warning.assert_called_once_with("Cannot create trace attributes: missing trace_id")

            # Verify attributes is empty
            assert attributes == {}

    def test_get_base_span_attributes_with_basic_span(self):
        """Test getting base span attributes with a basic span."""

        # Create a mock span
        class MockSpan:
            def __init__(self):
                self.span_id = "test_span_id"
                self.trace_id = "test_trace_id"

        mock_span = MockSpan()

        # Mock the common attributes function
        with patch(
            "agentops.instrumentation.common.attributes.get_common_attributes",
            return_value={InstrumentationAttributes.NAME: "agentops", InstrumentationAttributes.VERSION: "0.1.2"},
        ):
            # Get base span attributes
            attributes = get_base_span_attributes(mock_span)

            # Verify attributes
            assert CoreAttributes.SPAN_ID in attributes
            assert attributes[CoreAttributes.SPAN_ID] == "test_span_id"
            assert CoreAttributes.TRACE_ID in attributes
            assert attributes[CoreAttributes.TRACE_ID] == "test_trace_id"
            assert InstrumentationAttributes.NAME in attributes
            assert attributes[InstrumentationAttributes.NAME] == "agentops"
            assert InstrumentationAttributes.VERSION in attributes
            assert attributes[InstrumentationAttributes.VERSION] == "0.1.2"
            assert CoreAttributes.PARENT_ID not in attributes  # No parent_id in span

    def test_get_base_span_attributes_with_parent(self):
        """Test getting base span attributes with a span that has a parent."""

        # Create a mock span with parent_id
        class MockSpan:
            def __init__(self):
                self.span_id = "test_span_id"
                self.trace_id = "test_trace_id"
                self.parent_id = "test_parent_id"

        mock_span = MockSpan()

        # Mock the common attributes function
        with patch(
            "agentops.instrumentation.common.attributes.get_common_attributes",
            return_value={InstrumentationAttributes.NAME: "agentops", InstrumentationAttributes.VERSION: "0.1.2"},
        ):
            # Get base span attributes
            attributes = get_base_span_attributes(mock_span)

            # Verify attributes
            assert CoreAttributes.SPAN_ID in attributes
            assert attributes[CoreAttributes.SPAN_ID] == "test_span_id"
            assert CoreAttributes.TRACE_ID in attributes
            assert attributes[CoreAttributes.TRACE_ID] == "test_trace_id"
            assert CoreAttributes.PARENT_ID in attributes
            assert attributes[CoreAttributes.PARENT_ID] == "test_parent_id"
            assert InstrumentationAttributes.NAME in attributes
            assert attributes[InstrumentationAttributes.NAME] == "agentops"
            assert InstrumentationAttributes.VERSION in attributes
            assert attributes[InstrumentationAttributes.VERSION] == "0.1.2"

    def test_get_base_span_attributes_with_unknown_values(self):
        """Test getting base span attributes with a span that has unknown values."""
        # Create a mock object that doesn't have the expected attributes
        mock_object = object()

        # Mock the common attributes function
        with patch(
            "agentops.instrumentation.common.attributes.get_common_attributes",
            return_value={InstrumentationAttributes.NAME: "agentops", InstrumentationAttributes.VERSION: "0.1.2"},
        ):
            # Get base span attributes
            attributes = get_base_span_attributes(mock_object)

            # Verify attributes
            assert CoreAttributes.SPAN_ID in attributes
            assert attributes[CoreAttributes.SPAN_ID] == "unknown"
            assert CoreAttributes.TRACE_ID in attributes
            assert attributes[CoreAttributes.TRACE_ID] == "unknown"
            assert CoreAttributes.PARENT_ID not in attributes  # No parent_id
            assert InstrumentationAttributes.NAME in attributes
            assert attributes[InstrumentationAttributes.NAME] == "agentops"
            assert InstrumentationAttributes.VERSION in attributes
            assert attributes[InstrumentationAttributes.VERSION] == "0.1.2"


if __name__ == "__main__":
    pytest.main()
