from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def format_duration(start_time, end_time) -> str:
    """Format duration between two timestamps"""
    if not start_time or not end_time:
        return "0.0s"

    start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    duration = end - start

    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    parts.append(f"{seconds:.1f}s")

    return " ".join(parts)


def format_token_cost(cost: float | Decimal) -> str:
    """Format token cost to 2 decimal places, or 6 decimal places if non-zero"""
    if isinstance(cost, Decimal):
        return "{:.6f}".format(cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
    return "{:.2f}".format(cost)
