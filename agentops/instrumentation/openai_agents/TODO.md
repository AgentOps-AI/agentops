# OpenAI Agents SDK Instrumentation TODOs

This document lists identified discrepancies between data available during processing and data reflected in the final API output JSON.

## Missing or Incomplete Data in Output JSON

1. **Missing Timestamps**:
   - In output JSON, `"start_time": ""` is empty despite the exporter having access to timestamps
   - The exporter tracks timing using `time.time()` but doesn't populate the `start_time` field
   - Timing data from span start/end events isn't being transferred to the output

2. **Debug Information Not in Output**:
   - Debug logging captures span_data attributes like `['export', 'handoffs', 'name', 'output_type', 'tools', 'type']`
   - Not all of these attributes are present in the final output JSON
   - Consider enriching output with more of the available attributes

3. **Empty Attributes Object**:
   - In output JSON, `"attributes": {}` is completely empty
   - The exporter creates a rich set of attributes for the span, but these aren't making it into the "attributes" field
   - The data appears in "span_attributes" but not in the general "attributes" field

4. **Trace-Level Information Missing**:
   - Trace-level information in `_export_trace()` includes metadata like group_id
   - This trace information is only minimally represented in the output through trace_id and trace state
   - Consider enhancing trace representation in output

5. **Response Data Truncation**:
   - Content length is limited in the instrumentor.py: `if len(content) > 1000: content = content[:1000]`
   - The truncated data is missing from the output JSON
   - Consider adding indicators when content has been truncated

6. **Event Data Not Present**:
   - Event data fields are empty arrays in output JSON:
     ```
     "event_timestamps": [],
     "event_names": [],
     "event_attributes": [],
     ```
   - The exporter has access to event data but isn't populating these arrays

7. **Library Version Inconsistency**:
   - While the exporter sets `LIBRARY_VERSION` in attributes, this value isn't consistently reflected in output
   - This was fixed by ensuring `LIBRARY_VERSION` is always a string in the init module
   - Ensure consistent usage across all attribute setting

8. **Limited Resource Attributes**:
   - Resource attributes in the output contain basic information but miss details available to the exporter
   - Rich context about the agent, model, and execution environment isn't fully transferred to resource attributes

## Next Steps

- Review the exporter and processor implementations to ensure all available data is being transferred to output
- Add explicit handling for timestamps to populate start_time fields
- Consider expanding resource attributes with more contextual information
- Implement event tracking to populate event arrays in output
- Ensure consistent attribute mapping between internal representations and output format