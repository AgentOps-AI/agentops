from agentops.log_capture import LogCapture


def test_logcap(agentops_session):
    import os
    import sys
    import time
    from dataclasses import dataclass
    from uuid import uuid4

    session = agentops_session
    capture = LogCapture(session_id=session.session_id)
    capture.start()
    try:
        # Test Rich formatting
        from rich.console import Console

        console = Console(force_terminal=True)
        rprint = console.print
        rprint("[red]This is red text[/red]")
        rprint("[blue]Blue[/blue] and [green]green[/green] mixed")
        rprint("[bold red]Bold red[/bold red] and [italic blue]italic blue[/italic blue]")

        # Test raw ANSI codes
        print("\033[31mDirect red ANSI\033[0m\n")
        print("\033[34mBlue\033[0m and \033[32mgreen\033[0m mixed ANSI\n")
        print("\033[1;31mBold red ANSI\033[0m\n")

        # Test stderr with colors
        sys.stderr.write("\033[35mMagenta error\033[0m\n")
        sys.stderr.write("\033[33mYellow warning\033[0m\n")

    finally:
        # Stop capture and show normal output is restored
        capture.stop()
        # print("\nCapture stopped - this prints normally to stdout")
        # sys.stderr.write("This error goes normally to stderr\n")
