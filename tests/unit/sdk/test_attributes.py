"""
Tests for agentops.sdk.attributes module.

This module tests all attribute management functions for telemetry contexts.
"""

import platform
from unittest.mock import Mock, patch

import pytest

from agentops.sdk.attributes import (
    get_system_resource_attributes,
    get_global_resource_attributes,
    get_trace_attributes,
    get_span_attributes,
    get_session_end_attributes,
)
from agentops.semconv import ResourceAttributes, SpanAttributes, CoreAttributes


class TestGetSystemResourceAttributes:
    """Test get_system_resource_attributes function."""

    def test_basic_system_attributes(self):
        """Test that basic system attributes are included."""
        attributes = get_system_resource_attributes()

        # Check that all basic platform attributes are present
        assert ResourceAttributes.HOST_MACHINE in attributes
        assert ResourceAttributes.HOST_NAME in attributes
        assert ResourceAttributes.HOST_NODE in attributes
        assert ResourceAttributes.HOST_PROCESSOR in attributes
        assert ResourceAttributes.HOST_SYSTEM in attributes
        assert ResourceAttributes.HOST_VERSION in attributes
        assert ResourceAttributes.HOST_OS_RELEASE in attributes

        # Check that values match platform module
        assert attributes[ResourceAttributes.HOST_MACHINE] == platform.machine()
        assert attributes[ResourceAttributes.HOST_NAME] == platform.node()
        assert attributes[ResourceAttributes.HOST_NODE] == platform.node()
        assert attributes[ResourceAttributes.HOST_PROCESSOR] == platform.processor()
        assert attributes[ResourceAttributes.HOST_SYSTEM] == platform.system()
        assert attributes[ResourceAttributes.HOST_VERSION] == platform.version()
        assert attributes[ResourceAttributes.HOST_OS_RELEASE] == platform.release()

    @patch("agentops.sdk.attributes.os.cpu_count")
    @patch("agentops.sdk.attributes.psutil.cpu_percent")
    def test_cpu_stats_success(self, mock_cpu_percent, mock_cpu_count):
        """Test CPU stats when successfully retrieved."""
        mock_cpu_count.return_value = 8
        mock_cpu_percent.return_value = 25.5

        attributes = get_system_resource_attributes()

        assert ResourceAttributes.CPU_COUNT in attributes
        assert ResourceAttributes.CPU_PERCENT in attributes
        assert attributes[ResourceAttributes.CPU_COUNT] == 8
        assert attributes[ResourceAttributes.CPU_PERCENT] == 25.5

    @patch("agentops.sdk.attributes.os.cpu_count")
    @patch("agentops.sdk.attributes.psutil.cpu_percent")
    def test_cpu_stats_cpu_count_none(self, mock_cpu_percent, mock_cpu_count):
        """Test CPU stats when cpu_count returns None."""
        mock_cpu_count.return_value = None
        mock_cpu_percent.return_value = 25.5

        attributes = get_system_resource_attributes()

        assert ResourceAttributes.CPU_COUNT in attributes
        assert attributes[ResourceAttributes.CPU_COUNT] == 0

    @patch("agentops.sdk.attributes.os.cpu_count")
    @patch("agentops.sdk.attributes.psutil.cpu_percent")
    def test_cpu_stats_exception(self, mock_cpu_percent, mock_cpu_count):
        """Test CPU stats when exception occurs."""
        mock_cpu_count.side_effect = Exception("CPU count error")
        mock_cpu_percent.side_effect = Exception("CPU percent error")

        attributes = get_system_resource_attributes()

        # Should not include CPU attributes when exception occurs
        assert ResourceAttributes.CPU_COUNT not in attributes
        assert ResourceAttributes.CPU_PERCENT not in attributes

    @patch("agentops.sdk.attributes.psutil.virtual_memory")
    def test_memory_stats_success(self, mock_virtual_memory):
        """Test memory stats when successfully retrieved."""
        mock_memory = Mock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.used = 4294967296  # 4GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory

        attributes = get_system_resource_attributes()

        assert ResourceAttributes.MEMORY_TOTAL in attributes
        assert ResourceAttributes.MEMORY_AVAILABLE in attributes
        assert ResourceAttributes.MEMORY_USED in attributes
        assert ResourceAttributes.MEMORY_PERCENT in attributes
        assert attributes[ResourceAttributes.MEMORY_TOTAL] == 8589934592
        assert attributes[ResourceAttributes.MEMORY_AVAILABLE] == 4294967296
        assert attributes[ResourceAttributes.MEMORY_USED] == 4294967296
        assert attributes[ResourceAttributes.MEMORY_PERCENT] == 50.0

    @patch("agentops.sdk.attributes.psutil.virtual_memory")
    def test_memory_stats_exception(self, mock_virtual_memory):
        """Test memory stats when exception occurs."""
        mock_virtual_memory.side_effect = Exception("Memory error")

        attributes = get_system_resource_attributes()

        # Should not include memory attributes when exception occurs
        assert ResourceAttributes.MEMORY_TOTAL not in attributes
        assert ResourceAttributes.MEMORY_AVAILABLE not in attributes
        assert ResourceAttributes.MEMORY_USED not in attributes
        assert ResourceAttributes.MEMORY_PERCENT not in attributes


class TestGetGlobalResourceAttributes:
    """Test get_global_resource_attributes function."""

    @patch("agentops.sdk.attributes.get_imported_libraries")
    def test_basic_attributes_with_project_id(self, mock_get_libs):
        """Test basic attributes with project ID."""
        mock_get_libs.return_value = ["requests", "pandas"]

        attributes = get_global_resource_attributes("test-service", project_id="test-project")

        assert ResourceAttributes.SERVICE_NAME in attributes
        assert ResourceAttributes.PROJECT_ID in attributes
        assert ResourceAttributes.IMPORTED_LIBRARIES in attributes
        assert attributes[ResourceAttributes.SERVICE_NAME] == "test-service"
        assert attributes[ResourceAttributes.PROJECT_ID] == "test-project"
        assert attributes[ResourceAttributes.IMPORTED_LIBRARIES] == ["requests", "pandas"]

    @patch("agentops.sdk.attributes.get_imported_libraries")
    def test_basic_attributes_without_project_id(self, mock_get_libs):
        """Test basic attributes without project ID."""
        mock_get_libs.return_value = ["requests", "pandas"]

        attributes = get_global_resource_attributes("test-service")

        assert ResourceAttributes.SERVICE_NAME in attributes
        assert ResourceAttributes.PROJECT_ID not in attributes
        assert ResourceAttributes.IMPORTED_LIBRARIES in attributes
        assert attributes[ResourceAttributes.SERVICE_NAME] == "test-service"
        assert attributes[ResourceAttributes.IMPORTED_LIBRARIES] == ["requests", "pandas"]

    @patch("agentops.sdk.attributes.get_imported_libraries")
    def test_no_imported_libraries(self, mock_get_libs):
        """Test when no imported libraries are found."""
        mock_get_libs.return_value = None

        attributes = get_global_resource_attributes("test-service", project_id="test-project")

        assert ResourceAttributes.SERVICE_NAME in attributes
        assert ResourceAttributes.PROJECT_ID in attributes
        assert ResourceAttributes.IMPORTED_LIBRARIES not in attributes
        assert attributes[ResourceAttributes.SERVICE_NAME] == "test-service"
        assert attributes[ResourceAttributes.PROJECT_ID] == "test-project"

    @patch("agentops.sdk.attributes.get_imported_libraries")
    def test_empty_imported_libraries(self, mock_get_libs):
        """Test when imported libraries list is empty."""
        mock_get_libs.return_value = []

        attributes = get_global_resource_attributes("test-service", project_id="test-project")

        assert ResourceAttributes.SERVICE_NAME in attributes
        assert ResourceAttributes.PROJECT_ID in attributes
        assert ResourceAttributes.IMPORTED_LIBRARIES not in attributes
        assert attributes[ResourceAttributes.SERVICE_NAME] == "test-service"
        assert attributes[ResourceAttributes.PROJECT_ID] == "test-project"


class TestGetTraceAttributes:
    """Test get_trace_attributes function."""

    def test_no_tags(self):
        """Test when no tags are provided."""
        attributes = get_trace_attributes()

        assert attributes == {}

    def test_list_tags(self):
        """Test with list of tags."""
        tags = ["tag1", "tag2", "tag3"]
        attributes = get_trace_attributes(tags)

        assert CoreAttributes.TAGS in attributes
        assert attributes[CoreAttributes.TAGS] == ["tag1", "tag2", "tag3"]

    def test_dict_tags(self):
        """Test with dictionary of tags."""
        tags = {"key1": "value1", "key2": "value2"}
        attributes = get_trace_attributes(tags)

        assert "key1" in attributes
        assert "key2" in attributes
        assert attributes["key1"] == "value1"
        assert attributes["key2"] == "value2"

    def test_mixed_dict_tags(self):
        """Test with dictionary containing various value types."""
        tags = {
            "string_key": "string_value",
            "int_key": 42,
            "float_key": 3.14,
            "bool_key": True,
            "list_key": [1, 2, 3],
        }
        attributes = get_trace_attributes(tags)

        assert attributes["string_key"] == "string_value"
        assert attributes["int_key"] == 42
        assert attributes["float_key"] == 3.14
        assert attributes["bool_key"] is True
        assert attributes["list_key"] == [1, 2, 3]

    def test_invalid_tags_type(self):
        """Test with invalid tags type."""
        with patch("agentops.sdk.attributes.logger") as mock_logger:
            attributes = get_trace_attributes("invalid_tags")

            assert attributes == {}
            mock_logger.warning.assert_called_once()

    def test_none_tags(self):
        """Test with None tags."""
        attributes = get_trace_attributes(None)

        assert attributes == {}


class TestGetSpanAttributes:
    """Test get_span_attributes function."""

    def test_basic_span_attributes(self):
        """Test basic span attributes."""
        attributes = get_span_attributes("test-operation", "test-kind")

        assert SpanAttributes.AGENTOPS_SPAN_KIND in attributes
        assert SpanAttributes.OPERATION_NAME in attributes
        assert attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == "test-kind"
        assert attributes[SpanAttributes.OPERATION_NAME] == "test-operation"
        assert SpanAttributes.OPERATION_VERSION not in attributes

    def test_span_attributes_with_version(self):
        """Test span attributes with version."""
        attributes = get_span_attributes("test-operation", "test-kind", version=1)

        assert SpanAttributes.AGENTOPS_SPAN_KIND in attributes
        assert SpanAttributes.OPERATION_NAME in attributes
        assert SpanAttributes.OPERATION_VERSION in attributes
        assert attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == "test-kind"
        assert attributes[SpanAttributes.OPERATION_NAME] == "test-operation"
        assert attributes[SpanAttributes.OPERATION_VERSION] == 1

    def test_span_attributes_with_version_zero(self):
        """Test span attributes with version zero."""
        attributes = get_span_attributes("test-operation", "test-kind", version=0)

        assert SpanAttributes.OPERATION_VERSION in attributes
        assert attributes[SpanAttributes.OPERATION_VERSION] == 0

    def test_span_attributes_with_additional_kwargs(self):
        """Test span attributes with additional keyword arguments."""
        attributes = get_span_attributes(
            "test-operation",
            "test-kind",
            version=1,
            custom_key="custom_value",
            another_key=42,
        )

        assert SpanAttributes.AGENTOPS_SPAN_KIND in attributes
        assert SpanAttributes.OPERATION_NAME in attributes
        assert SpanAttributes.OPERATION_VERSION in attributes
        assert "custom_key" in attributes
        assert "another_key" in attributes
        assert attributes["custom_key"] == "custom_value"
        assert attributes["another_key"] == 42

    def test_span_attributes_overwrite_kwargs(self):
        """Test that kwargs can overwrite default attributes."""
        attributes = get_span_attributes(
            "test-operation",
            "test-kind",
            version=1,
            custom_operation_name="overwritten-name",
            custom_span_kind="overwritten-kind",
        )

        # kwargs should overwrite the default values
        assert attributes["custom_operation_name"] == "overwritten-name"
        assert attributes["custom_span_kind"] == "overwritten-kind"
        # The original positional arguments should still be set
        assert attributes[SpanAttributes.OPERATION_NAME] == "test-operation"
        assert attributes[SpanAttributes.AGENTOPS_SPAN_KIND] == "test-kind"


class TestGetSessionEndAttributes:
    """Test get_session_end_attributes function."""

    def test_session_end_attributes_success(self):
        """Test session end attributes with success state."""
        attributes = get_session_end_attributes("Success")

        assert SpanAttributes.AGENTOPS_SESSION_END_STATE in attributes
        assert attributes[SpanAttributes.AGENTOPS_SESSION_END_STATE] == "Success"

    def test_session_end_attributes_failure(self):
        """Test session end attributes with failure state."""
        attributes = get_session_end_attributes("Failure")

        assert SpanAttributes.AGENTOPS_SESSION_END_STATE in attributes
        assert attributes[SpanAttributes.AGENTOPS_SESSION_END_STATE] == "Failure"

    def test_session_end_attributes_custom_state(self):
        """Test session end attributes with custom state."""
        attributes = get_session_end_attributes("CustomState")

        assert SpanAttributes.AGENTOPS_SESSION_END_STATE in attributes
        assert attributes[SpanAttributes.AGENTOPS_SESSION_END_STATE] == "CustomState"

    def test_session_end_attributes_empty_string(self):
        """Test session end attributes with empty string."""
        attributes = get_session_end_attributes("")

        assert SpanAttributes.AGENTOPS_SESSION_END_STATE in attributes
        assert attributes[SpanAttributes.AGENTOPS_SESSION_END_STATE] == ""


class TestAttributesIntegration:
    """Integration tests for attributes module."""

    def test_all_functions_work_together(self):
        """Test that all attribute functions work together without conflicts."""
        # Get system attributes
        system_attrs = get_system_resource_attributes()
        assert isinstance(system_attrs, dict)

        # Get global attributes
        global_attrs = get_global_resource_attributes("test-service", project_id="test-project")
        assert isinstance(global_attrs, dict)

        # Get trace attributes
        trace_attrs = get_trace_attributes(["tag1", "tag2"])
        assert isinstance(trace_attrs, dict)

        # Get span attributes
        span_attrs = get_span_attributes("test-operation", "test-kind", version=1)
        assert isinstance(span_attrs, dict)

        # Get session end attributes
        session_attrs = get_session_end_attributes("Success")
        assert isinstance(session_attrs, dict)

        # Verify no key conflicts between different attribute types
        all_keys = (
            set(system_attrs.keys())
            | set(global_attrs.keys())
            | set(trace_attrs.keys())
            | set(span_attrs.keys())
            | set(session_attrs.keys())
        )
        assert len(all_keys) == len(system_attrs) + len(global_attrs) + len(trace_attrs) + len(span_attrs) + len(
            session_attrs
        )

    def test_attribute_types_consistency(self):
        """Test that all attributes return consistent types."""
        # All functions should return dictionaries
        assert isinstance(get_system_resource_attributes(), dict)
        assert isinstance(get_global_resource_attributes("test"), dict)
        assert isinstance(get_trace_attributes(), dict)
        assert isinstance(get_span_attributes("test", "test"), dict)
        assert isinstance(get_session_end_attributes("test"), dict)

        # All dictionary values should be serializable
        import json

        try:
            json.dumps(get_system_resource_attributes())
            json.dumps(get_global_resource_attributes("test"))
            json.dumps(get_trace_attributes())
            json.dumps(get_span_attributes("test", "test"))
            json.dumps(get_session_end_attributes("test"))
        except (TypeError, ValueError) as e:
            pytest.fail(f"Attributes are not JSON serializable: {e}")
