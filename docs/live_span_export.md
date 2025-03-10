1. The `LiveSpanProcessor` class extends the OpenTelemetry `SpanProcessor` and is responsible for handling spans as they are created and completed.

2. Key mechanism for immediate export:
   - It maintains an in-memory dictionary of "in-flight" (currently active) spans with `self._in_flight`
   - When a span starts (`on_start` method), it's added to this dictionary
   - A background thread (`_export_thread`) runs periodically to export these in-flight spans
   - This thread calls `_export_periodically` which exports snapshots of active spans every second

3. The critical part is in the `_readable_span` method, which:
   - Takes a currently active span
   - Creates a readable version of it
   - Sets a temporary end time to the current time (`readable._end_time = time.time_ns()`)
   - Adds a special attribute to indicate it's an in-flight span (`"prefect.in-flight": True`)

4. This allows the system to export "snapshots" of currently running spans before they've actually completed, making them immediately visible in the flamegraph UI.

5. When spans actually complete (`on_end` method), they're removed from the in-flight dictionary and exported normally.

The tests in `tests/telemetry/test_processors.py` confirm this behavior, particularly the `test_periodic_export` test which verifies that spans are exported with the "prefect.in-flight" attribute before they're completed.

The UI components in `ui/src/components/FlowRunGraphs.vue` and `ui-v2/src/components/ui/chart.tsx` show how these spans are visualized in the UI, although the specific flamegraph implementation details aren't fully visible in the provided snippets.

This approach allows for real-time visibility of spans in progress, which is essential for monitoring and debugging active processes in a flamegraph visualization.

## How Tests Handle Span Snapshots

Tests for the `LiveSpanProcessor` are implemented in `tests/telemetry/test_processors.py` and demonstrate how span snapshots are handled:

1. **Separate Export Events for the Same Logical Span**:
   - Spans and their snapshots are treated as separate export events, but they represent the same logical span
   - The exporter receives multiple span objects for different states of the same span (identified by the same span ID)

2. **What Tests Expect**:
   - For a span that starts and ends, tests expect:
     - At least one in-flight span export (snapshot) with the `prefect.in-flight: True` attribute
     - One final span export when the span completes (without the in-flight attribute)

3. **Verification Approach**:
   - The `test_periodic_export` test confirms that active spans are exported with the "prefect.in-flight" attribute before completion
   - The `test_span_processing_lifecycle` test verifies that when spans complete, they're exported again (without the in-flight attribute)
   - Tests verify both types of exports separately, focusing on the correct behavior of each export operation

4. **Distinguishing Snapshots from Completed Spans**:
   - The key distinction is that snapshots are marked with `prefect.in-flight: True`
   - Completed spans don't have this attribute
   - This allows visualization systems to differentiate between snapshots and completed spans, updating the display accordingly

This testing approach ensures both the real-time visibility feature works correctly (through snapshots) while also maintaining the complete and accurate final representation of spans after they've completed.
