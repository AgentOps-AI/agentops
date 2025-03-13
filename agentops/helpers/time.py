from datetime import datetime, timezone


def get_ISO_time():
    """
    Get the current UTC time in ISO 8601 format with milliseconds precision in UTC timezone.

    Returns:
        str: The current UTC time as a string in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def iso_to_unix_nano(iso_time: str) -> int:
    dt = datetime.fromisoformat(iso_time)
    return int(dt.timestamp() * 1_000_000_000)


def from_unix_nano_to_iso(unix_nano: int) -> str:
    return datetime.fromtimestamp(unix_nano / 1_000_000_000, timezone.utc).isoformat()
