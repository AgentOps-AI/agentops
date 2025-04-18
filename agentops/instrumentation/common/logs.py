import builtins
import logging
import os
import atexit
from datetime import datetime
from typing import Any, TextIO

# Store the original print function
_original_print = builtins.print

def setup_print_logger() -> None:
    """
    Monkeypatches the built-in print function and configures logging to also log to a file.
    Preserves existing logging configuration and console output behavior.
    """
    # Create a unique log file name with timestamp
    log_file = os.path.join(os.getcwd(), f"agentops-tmp.log")
    
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Add our file handler without removing existing ones
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    file_handler.setLevel(logging.INFO)  # Capture all log levels
    root_logger.addHandler(file_handler)
    
    # Set root logger level to DEBUG to ensure we capture everything
    root_logger.setLevel(logging.DEBUG)
    
    # Test logging
    logging.debug("Test debug message")
    logging.info("Test info message")
    logging.warning("Test warning message")
    
    def print_logger(*args: Any, **kwargs: Any) -> None:
        """
        Custom print function that logs to file and console.
        
        Args:
            *args: Arguments to print
            **kwargs: Keyword arguments to print
        """
        # Convert all arguments to strings and join them
        message = " ".join(str(arg) for arg in args)
        
        # First log to file
        logging.info(message)
        
        # Then print to console using original print
        _original_print(*args, **kwargs)
    
    # Replace the built-in print with our custom version
    builtins.print = print_logger

    def cleanup():
        """
        Cleanup function to be called when the process exits.
        Removes the log file and restores the original print function.
        """
        try:
            # Only remove our file handler
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler) and handler.baseFilename == log_file:
                    handler.close()
                    root_logger.removeHandler(handler)
            
            # Delete the log file
            if os.path.exists(log_file):
                # os.remove(log_file)
                pass
            
            # Restore the original print function
            builtins.print = _original_print
        except Exception as e:
            # If something goes wrong during cleanup, just print the error
            _original_print(f"Error during cleanup: {e}")

    # Register the cleanup function to run when the process exits
    atexit.register(cleanup) 