from unittest.mock import patch


from agentops.sdk.core import tracer
from agentops.sdk.attributes import get_global_resource_attributes
from agentops.semconv.resource import ResourceAttributes


@patch("agentops.sdk.attributes.get_imported_libraries", return_value=["agentops"])
def test_global_resource_attributes_no_system(mock_libs):
    attrs = get_global_resource_attributes("svc", project_id="proj")
    assert attrs[ResourceAttributes.SERVICE_NAME] == "svc"
    assert attrs[ResourceAttributes.PROJECT_ID] == "proj"
    assert ResourceAttributes.IMPORTED_LIBRARIES in attrs
    assert ResourceAttributes.HOST_MACHINE not in attrs
    assert ResourceAttributes.CPU_COUNT not in attrs


@patch("agentops.sdk.core.get_system_resource_attributes")
def test_system_metadata_only_for_session(mock_sys_attrs, instrumentation):
    mock_sys_attrs.return_value = {ResourceAttributes.HOST_MACHINE: "test"}

    ctx = tracer.start_trace("session")
    tracer.end_trace(ctx, end_state="Success")
    spans = instrumentation.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].attributes.get(ResourceAttributes.HOST_MACHINE) == "test"

    instrumentation.clear_spans()

    ctx = tracer.start_trace("custom")
    tracer.end_trace(ctx, end_state="Success")
    spans = instrumentation.get_finished_spans()
    assert len(spans) == 1
    assert ResourceAttributes.HOST_MACHINE not in spans[0].attributes
