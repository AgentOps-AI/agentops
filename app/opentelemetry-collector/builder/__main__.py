import sys
import argparse

from builder.conf import OUT_DIR
from builder.otelcollector_config import render_base_config, render_processors_config


def generate_configs(args):
    """Render all of the OpenTelemetry Collector configs."""
    render_base_config(args.output_dir)
    render_processors_config(args.output_dir)


def main():
    parser = argparse.ArgumentParser(description="OpenTelemetry Collector builder")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    export_parser = subparsers.add_parser("generate_configs", help="Generate otelcollector configs")
    export_parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        default=str(OUT_DIR),
        help=f"Directory to save the exported data (default: {OUT_DIR})",
    )

    args = parser.parse_args()
    if args.command == "generate_configs":
        generate_configs(args)
    elif not args.command:
        parser.print_help()
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
