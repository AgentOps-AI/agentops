import builtins
import logging
import atexit
from typing import Any
from io import StringIO

_original_print = builtins.print

# Global buffer to store logs
_log_buffer = StringIO()


def setup_print_logger() -> None:
    """
    Instruments the built-in print function and configures logging to use a memory buffer.
    Preserves existing logging configuration and console output behavior.
    """
    buffer_logger = logging.getLogger("agentops_buffer_logger")
    buffer_logger.setLevel(logging.DEBUG)

    # Check if the logger already has handlers to prevent duplicates
    if not buffer_logger.handlers:
        # Create a StreamHandler that writes to our StringIO buffer
        buffer_handler = logging.StreamHandler(_log_buffer)
        buffer_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        buffer_handler.setLevel(logging.DEBUG)
        buffer_logger.addHandler(buffer_handler)

        # Ensure the new logger doesn't propagate to root
        buffer_logger.propagate = False

    def print_logger(*args: Any, **kwargs: Any) -> None:
        """
        Custom print function that logs to buffer and console.

        Args:
            *args: Arguments to print
            **kwargs: Keyword arguments to print
        """
        message = " ".join(str(arg) for arg in args)
        buffer_logger.info(message)

        # print to console using original print
        _original_print(*args, **kwargs)

    # Only replace print if it hasn't been replaced already
    if builtins.print is _original_print:
        builtins.print = print_logger

    def cleanup():
        """
        Cleanup function to be called when the process exits.
        Restores the original print function and clears the buffer.
        """
        try:
            # Remove our buffer handler
            for handler in buffer_logger.handlers[:]:
                handler.close()
                buffer_logger.removeHandler(handler)

            # Clear the buffer
            _log_buffer.seek(0)
            _log_buffer.truncate()

            # Restore the original print function
            builtins.print = _original_print
        except Exception as e:
            # If something goes wrong during cleanup, just print the error
            _original_print(f"Error during cleanup: {e}")

    # Register the cleanup function to run when the process exits
    atexit.register(cleanup)


def upload_logfile(trace_id: int) -> None:
    """
    Upload the log content from the memory buffer to the API.
    """
    from agentops import get_client

    # Get the content from the buffer
    log_content = _log_buffer.getvalue()
    if not log_content:
        return

    client = get_client()
    client.api.v4.upload_logfile(log_content, trace_id)

    # Clear the buffer after upload
    _log_buffer.seek(0)
    _log_buffer.truncate()
