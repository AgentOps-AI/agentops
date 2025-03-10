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

This approach allows for real-time visibility of spans in progress, which is essential for monitoring and debugging active processes in a flamegraph visualization.</think>Based on the codebase search results, I can explain how Cursor achieves immediate span export for flamegraph visualization without waiting for spans to end.

The key mechanism is implemented in the `LiveSpanProcessor` class in `src/prefect/telemetry/processors.py`. Here's how it works:

### 1. Tracking Active Spans

```python
class LiveSpanProcessor(SpanProcessor):
    def __init__(self, span_exporter: SpanExporter):
        self.span_exporter = span_exporter
        self._in_flight: Dict[int, Span] = {}  # Dictionary of active spans
        self._lock = Lock()
        self._stop_event = Event()
        self._export_thread = Thread(target=self._export_periodically, daemon=True)
        self._export_thread.start()
        
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        if not span.context or not span.context.trace_flags.sampled:
            return
        with self._lock:
            self._in_flight[span.context.span_id] = span
```

When a span starts, it's added to an `_in_flight` dictionary that tracks all currently active spans.

### 2. Periodic Export of Active Spans

```python
def _export_periodically(self) -> None:
    while not self._stop_event.is_set():
        time.sleep(1)
        with self._lock:
            to_export = [
                self._readable_span(span) for span in self._in_flight.values()
            ]
            if to_export:
                self.span_exporter.export(to_export)
```

A background thread runs periodically (every 1 second) to export snapshots of all active spans. This is the critical part - it doesn't wait for spans to complete before exporting them.

### 3. Creating "In-Flight" Snapshots

```python
def _readable_span(self, span: Span) -> ReadableSpan:
    readable = span._readable_span()
    readable._end_time = time.time_ns()  # Temporarily set end time to now
    readable._attributes = {
        **(readable._attributes or {}),
        "prefect.in-flight": True,  # Mark as in-flight
    }
    return readable
```

For each active span, it:
1. Creates a readable snapshot
2. Sets a temporary end time to the current time
3. Adds a special attribute `"prefect.in-flight": True` to indicate it's still running

### 4. Normal Export When Spans End

```python
def on_end(self, span: ReadableSpan) -> None:
    if not span.context or not span.context.trace_flags.sampled:
        return
    with self._lock:
        del self._in_flight[span.context.span_id]
        self.span_exporter.export((span,))
```

When spans actually complete, they're removed from the in-flight dictionary and exported normally.

This approach allows the flamegraph to show real-time information about spans that are still in progress, with each span snapshot having a temporary end time set to the current moment. The UI can then use these snapshots to render the flamegraph with both completed and in-progress spans, providing immediate visibility without waiting for spans to finish.

This pattern is particularly useful for long-running spans or deep execution stacks, as it provides continuous visibility into what's happening without delay.
