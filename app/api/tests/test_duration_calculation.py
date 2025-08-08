from agentops.api.models.traces import nanosecond_timedelta
import datetime
import os
import sys

# Ensure the repo root (which contains the `agentops` package) is on the path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _wall_clock_ns(start: datetime.datetime, duration_ns: int) -> datetime.datetime:
    """Helper to convert a start time + duration nanoseconds into an end datetime."""
    return start + nanosecond_timedelta(duration_ns)


def test_overlapping_spans_wall_clock_less_than_sum():
    """Two overlapping spans should yield wall-clock duration < sum(duration)."""

    root_start = datetime.datetime(2025, 7, 7, 1, 19, 4, 69444, tzinfo=datetime.timezone.utc)
    child_start = root_start + datetime.timedelta(seconds=1)

    root_duration_ns = 30_000_000_000  # 30 s
    child_duration_ns = 15_000_000_000  # 15 s (overlaps root)

    root_end = _wall_clock_ns(root_start, root_duration_ns)
    child_end = _wall_clock_ns(child_start, child_duration_ns)

    expected_wall_clock_ns = int((max(root_end, child_end) - min(root_start, child_start)).total_seconds() * 1e9)

    # Ensure overlap made wall-clock less than naive sum
    assert expected_wall_clock_ns == 30_000_000_000  # 30 s elapsed (root span duration)
    assert expected_wall_clock_ns < (root_duration_ns + child_duration_ns)


def test_non_overlapping_spans_wall_clock_equals_sum():
    """If spans do not overlap the wall-clock duration equals the sum."""

    first_start = datetime.datetime(2025, 7, 7, 10, 0, 0, tzinfo=datetime.timezone.utc)
    first_dur_ns = 10_000_000_000  # 10 s
    first_end = _wall_clock_ns(first_start, first_dur_ns)

    second_start = first_end  # starts immediately after first ends
    second_dur_ns = 5_000_000_000  # 5 s
    second_end = _wall_clock_ns(second_start, second_dur_ns)

    wall_clock_ns = int((second_end - first_start).total_seconds() * 1e9)
    assert wall_clock_ns == first_dur_ns + second_dur_ns == 15_000_000_000


def test_single_span_wall_clock_equals_itself():
    """Single span should report its own duration."""

    start = datetime.datetime(2025, 7, 7, 12, 0, 0, tzinfo=datetime.timezone.utc)
    dur_ns = 8_500_000_000  # 8.5 s
    end = _wall_clock_ns(start, dur_ns)

    wall_clock_ns = int((end - start).total_seconds() * 1e9)
    assert wall_clock_ns == dur_ns
