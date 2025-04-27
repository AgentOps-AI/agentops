import builtins
import logging
import os
import atexit
from typing import Any

_original_print = builtins.print

LOGFILE_NAME = "agentops-tmp.log"

# Instrument loggers and print function to log to a file


def setup_print_logger() -> None:
    """
    ~Monkeypatches~ *Instruments the built-in print function and configures logging to also log to a file.
    Preserves existing logging configuration and console output behavior.
    """
    log_file = os.path.join(os.getcwd(), LOGFILE_NAME)

    file_logger = logging.getLogger('agentops_file_logger')
    file_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    file_handler.setLevel(logging.DEBUG)
    file_logger.addHandler(file_handler)

    # Ensure the new logger doesn't propagate to root
    file_logger.propagate = False

    def print_logger(*args: Any, **kwargs: Any) -> None:
        """
        Custom print function that logs to file and console.

        Args:
            *args: Arguments to print
            **kwargs: Keyword arguments to print
        """
        message = " ".join(str(arg) for arg in args)
        file_logger.info(message)

        # print to console using original print
        _original_print(*args, **kwargs)

    # replace the built-in print with ours
    builtins.print = print_logger

    def cleanup():
        """
        Cleanup function to be called when the process exits.
        Removes the log file and restores the original print function.
        """
        try:
            # Remove our file handler
            for handler in file_logger.handlers[:]:
                handler.close()
                file_logger.removeHandler(handler)

            # Restore the original print function
            builtins.print = _original_print
        except Exception as e:
            # If something goes wrong during cleanup, just print the error
            _original_print(f"Error during cleanup: {e}")

    # Register the cleanup function to run when the process exits
    atexit.register(cleanup)


def upload_logfile(trace_id: int) -> None:
    """
    Upload the log file to the API.
    """
    from agentops import get_client

    log_file = os.path.join(os.getcwd(), LOGFILE_NAME)
    if not os.path.exists(log_file):
        return
    with open(log_file, "r") as f:
        log_content = f.read()

    client = get_client()
    client.api.v4.upload_logfile(log_content, trace_id)

    os.remove(log_file)
