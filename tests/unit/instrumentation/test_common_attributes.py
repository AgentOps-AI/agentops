"""
Tests for Common Attributes Module

This module contains tests for the common attribute processing utilities that are shared
across all instrumentors in the AgentOps package.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Set

from agentops.instrumentation.common.attributes import (
    AttributeMap,
    _extract_attributes_from_mapping,
    get_common_attributes,
    get_base_trace_attributes,
    get_base_span_attributes
)
from agentops.helpers import get_tags_from_config

from agentops.semconv import (
    CoreAttributes,
    InstrumentationAttributes,
    WorkflowAttributes,
)


class TestCommonAttributes:
    """Test suite for common attribute processing utilities"""

    def test_extract_attributes_from_mapping(self):
        """Test extraction of attributes based on mapping"""
        # Create a simple span data object with attributes
        class SpanData:
            def __init__(self):
                self.trace_id = "trace123"
                self.span_id = "span456"
                self.parent_id = "parent789"
                self.name = "test_span"
                
        span_data = SpanData()
        
        # Define a mapping
        mapping = {
            "target.trace_id": "trace_id",
            "target.span_id": "span_id",
            "target.parent_id": "parent_id",
            "target.name": "name",
            "target.missing": "missing_attr"  # This attribute doesn't exist
        }
        
        # Extract attributes
        attributes = _extract_attributes_from_mapping(span_data, mapping)
        
        # Verify extracted attributes
        assert attributes["target.trace_id"] == "trace123"
        assert attributes["target.span_id"] == "span456"
        assert attributes["target.parent_id"] == "parent789"
        assert attributes["target.name"] == "test_span"
        assert "target.missing" not in attributes  # Missing attribute should be skipped
        
    def test_extract_attributes_from_dict(self):
        """Test extraction of attributes from a dictionary"""
        # Create a dictionary with attributes
        span_data = {
            "trace_id": "trace123",
            "span_id": "span456",
            "parent_id": "parent789",
            "name": "test_span"
        }
        
        # Define a mapping
        mapping = {
            "target.trace_id": "trace_id",
            "target.span_id": "span_id",
            "target.parent_id": "parent_id",
            "target.name": "name",
            "target.missing": "missing_key"  # This key doesn't exist
        }
        
        # Extract attributes
        attributes = _extract_attributes_from_mapping(span_data, mapping)
        
        # Verify extracted attributes
        assert attributes["target.trace_id"] == "trace123"
        assert attributes["target.span_id"] == "span456"
        assert attributes["target.parent_id"] == "parent789"
        assert attributes["target.name"] == "test_span"
        assert "target.missing" not in attributes  # Missing key should be skipped

    def test_extract_attributes_handles_none_empty_values(self):
        """Test that the extraction function properly handles None and empty values"""
        # Create a span data object with None and empty values
        class SpanData:
            def __init__(self):
                self.none_attr = None
                self.empty_str = ""
                self.empty_list = []
                self.empty_dict = {}
                self.valid_attr = "valid_value"
                
        span_data = SpanData()
        
        # Define a mapping
        mapping = {
            "target.none": "none_attr",
            "target.empty_str": "empty_str",
            "target.empty_list": "empty_list",
            "target.empty_dict": "empty_dict",
            "target.valid": "valid_attr"
        }
        
        # Extract attributes
        attributes = _extract_attributes_from_mapping(span_data, mapping)
        
        # Verify that None and empty values are skipped
        assert "target.none" not in attributes
        assert "target.empty_str" not in attributes
        assert "target.empty_list" not in attributes
        assert "target.empty_dict" not in attributes
        assert attributes["target.valid"] == "valid_value"

    def test_extract_attributes_serializes_complex_objects(self):
        """Test that complex objects are properly serialized during extraction"""
        # Create a dictionary with complex values
        span_data = {
            "complex_obj": {"attr1": "value1", "attr2": "value2"},
            "dict_obj": {"key1": "value1", "key2": "value2"},
            "list_obj": ["item1", "item2"]
        }
                
        # Define a mapping
        mapping = {
            "target.complex": "complex_obj",
            "target.dict": "dict_obj",
            "target.list": "list_obj"
        }
        
        # Extract attributes with serialization
        attributes = _extract_attributes_from_mapping(span_data, mapping)
        
        # Verify that complex objects are serialized to strings
        assert isinstance(attributes["target.complex"], str)
        assert isinstance(attributes["target.dict"], str)
        assert isinstance(attributes["target.list"], str)
        
        # Check that serialized values contain expected content
        assert "value1" in attributes["target.complex"]
        assert "value2" in attributes["target.complex"]
        assert "key1" in attributes["target.dict"]
        assert "key2" in attributes["target.dict"]
        assert "item1" in attributes["target.list"]
        assert "item2" in attributes["target.list"]

    def test_get_common_attributes(self):
        """Test that common instrumentation attributes are correctly generated"""
        # Get common attributes
        attributes = get_common_attributes()
        
        # Verify required keys and values
        assert InstrumentationAttributes.NAME in attributes
        assert InstrumentationAttributes.VERSION in attributes
        assert attributes[InstrumentationAttributes.NAME] == "agentops"

    def test_get_base_trace_attributes(self):
        """Test generation of base trace attributes"""
        # Create a simple trace object
        class TraceObj:
            def __init__(self):
                self.name = "test_workflow"
                self.trace_id = "trace123"
                
        trace = TraceObj()
        
        # Get base trace attributes
        attributes = get_base_trace_attributes(trace)
        
        # Verify core trace attributes
        assert attributes[WorkflowAttributes.WORKFLOW_NAME] == "test_workflow"
        assert attributes[CoreAttributes.TRACE_ID] == "trace123"
        assert attributes[WorkflowAttributes.WORKFLOW_STEP_TYPE] == "trace"
        assert attributes[InstrumentationAttributes.NAME] == "agentops"
        
        # Test error case when trace_id is missing
        class InvalidTrace:
            def __init__(self):
                self.name = "invalid_workflow"
                # No trace_id
                
        invalid_trace = InvalidTrace()
        invalid_attributes = get_base_trace_attributes(invalid_trace)
        assert invalid_attributes == {}

    def test_get_base_span_attributes(self):
        """Test generation of base span attributes"""
        # Create a simple span object
        class SpanObj:
            def __init__(self):
                self.span_id = "span456"
                self.trace_id = "trace123"
                self.parent_id = "parent789"
                
        span = SpanObj()
        
        # Get base span attributes
        attributes = get_base_span_attributes(span)
        
        # Verify core span attributes
        assert attributes[CoreAttributes.SPAN_ID] == "span456"
        assert attributes[CoreAttributes.TRACE_ID] == "trace123"
        assert attributes[CoreAttributes.PARENT_ID] == "parent789"
        assert attributes[InstrumentationAttributes.NAME] == "agentops"
        
        # Test without parent_id
        class SpanWithoutParent:
            def __init__(self):
                self.span_id = "span456"
                self.trace_id = "trace123"
                # No parent_id
                
        span_without_parent = SpanWithoutParent()
        attributes_without_parent = get_base_span_attributes(span_without_parent)
        
        # Verify parent_id is not included
        assert CoreAttributes.PARENT_ID not in attributes_without_parent

    def test_get_tags_from_config(self):
        """Test retrieval of tags from the configuration"""
        # Mock the get_config function
        mock_config = MagicMock()
        mock_config.default_tags = {"tag1", "tag2", "tag3"}
        
        with patch("agentops.helpers.config.get_config", return_value=mock_config):
            # Get tags from config
            tags = get_tags_from_config()
            
            # Verify tags are returned as a list
            assert isinstance(tags, list)
            assert set(tags) == {"tag1", "tag2", "tag3"}
            
    def test_get_tags_from_config_handles_empty_tags(self):
        """Test that empty tags are handled correctly"""
        # Mock the get_config function with empty tags
        mock_config = MagicMock()
        mock_config.default_tags = set()
        
        with patch("agentops.helpers.config.get_config", return_value=mock_config):
            # Get tags from config
            tags = get_tags_from_config()
            
            # Verify empty tags returns an empty list
            assert tags == []  # This should pass if get_tags_from_config returns [] for empty sets
            
    # Removed test_get_tags_from_config_handles_error since we're not handling errors anymore

    def test_tags_added_to_trace_attributes(self):
        """Test that tags are added to trace attributes but not span attributes"""
        # Create test objects
        class TraceObj:
            def __init__(self):
                self.name = "test_workflow"
                self.trace_id = "trace123"
                
        class SpanObj:
            def __init__(self):
                self.span_id = "span456"
                self.trace_id = "trace123"
                
        trace = TraceObj()
        span = SpanObj()
        
        # Mock the get_tags_from_config function to return test tags
        with patch("agentops.instrumentation.common.attributes.get_tags_from_config", 
                  return_value=["test_tag1", "test_tag2"]):
            # Get attributes for both trace and span
            trace_attributes = get_base_trace_attributes(trace)
            span_attributes = get_base_span_attributes(span)
            
            
            # Verify tags are added to trace attributes
            assert CoreAttributes.TAGS in trace_attributes
            assert trace_attributes[CoreAttributes.TAGS] == ["test_tag1", "test_tag2"]
            
            # Verify tags are NOT added to span attributes
            assert CoreAttributes.TAGS not in span_attributes