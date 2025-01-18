import argparse
import importlib.metadata

from .time_travel import fetch_time_travel_id, set_time_travel_active_state


def version_command():
    try:
        version = importlib.metadata.version("agentops")
        print(f"AgentOps version: {version}")
    except importlib.metadata.PackageNotFoundError:
        print("AgentOps package not found. Are you in development mode?")


def main():
    parser = argparse.ArgumentParser(description="AgentOps CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Version command
    version_parser = subparsers.add_parser("version", help="Show AgentOps version")

    # Time travel command
    time_travel_parser = subparsers.add_parser("time-travel", help="Time travel related commands")
    time_travel_parser.add_argument("--id", help="Get time travel ID", action="store_true")
    time_travel_parser.add_argument("--off", help="Turn off time travel", action="store_true")

    args = parser.parse_args()

    if args.command == "version":
        version_command()
    elif args.command == "time-travel":
        if args.id:
            ttd_id = None  # This would typically come from somewhere
            print(fetch_time_travel_id(ttd_id))
        if args.off:
            set_time_travel_active_state(False)


if __name__ == "__main__":
    main()
