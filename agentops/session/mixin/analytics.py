from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional, Union


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


class AnalyticsSessionMixin:
    """
    Mixin that adds presentation features to a session
    """

    def __init__(self, *args, **kwargs):
        self.event_counts = {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}

    # ------------------------------------------------------------------------------------------
    @property
    def token_cost(self) -> str:
        """
        Processes token cost based on the last response from the API.
        """
        try:
            # Get token cost from either response or direct value
            cost = Decimal(0)
            if self.api and self.api.last_response is not None:
                cost_value = self.api.last_response.json().get("token_cost", "unknown")
                if cost_value != "unknown" and cost_value is not None:
                    cost = Decimal(str(cost_value))

            # Format the cost
            return (
                "{:.2f}".format(cost)
                if cost == 0
                else "{:.6f}".format(cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            )
        except (ValueError, AttributeError):
            return "0.00"

    @property
    def analytics(self) -> Optional[Dict[str, Union[int, str]]]:
        """Get session analytics"""
        formatted_duration = format_duration(self.init_timestamp, self.end_timestamp)

        return {
            "LLM calls": self.event_counts["llms"],
            "Tool calls": self.event_counts["tools"],
            "Actions": self.event_counts["actions"],
            "Errors": self.event_counts["errors"],
            "Duration": formatted_duration,
            "Cost": self.token_cost,
        }
