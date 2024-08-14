import argparse
from .time_travel import fetch_time_travel_id, set_time_travel_active_state


def main():
    parser = argparse.ArgumentParser(description="AgentOps CLI")
    subparsers = parser.add_subparsers(dest="command")

    timetravel_parser = subparsers.add_parser(
        "timetravel", help="Time Travel Debugging commands", aliases=["tt"]
    )
    timetravel_parser.add_argument(
        "branch_name",
        type=str,
        nargs="?",
        help="Given a branch name, fetches the cache file for Time Travel Debugging. Turns on feature by default",
    )
    timetravel_parser.add_argument(
        "--on",
        action="store_true",
        help="Turns on Time Travel Debugging",
    )
    timetravel_parser.add_argument(
        "--off",
        action="store_true",
        help="Turns off Time Travel Debugging",
    )

    args = parser.parse_args()

    if args.command in ["timetravel", "tt"]:
        if args.branch_name:
            fetch_time_travel_id(args.branch_name)
        if args.on:
            set_time_travel_active_state(True)
        if args.off:
            set_time_travel_active_state(False)
