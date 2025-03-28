import sentry_sdk
import functools
from contextlib import contextmanager
from typing import Optional, Dict
import inspect

# Dictionary to store per-module Sentry settings
_module_sentry_settings: Dict[str, bool] = {}
# Global default setting
_default_opt_out = False


def set_opt_out_sentry(value: bool, module_name: Optional[str] = None):
    """
    Function to enable or disable Sentry error tracking globally or for specific modules.

    Args:
        value (bool): Set to True to disable Sentry, False to enable it.
        module_name (Optional[str]): If provided, sets Sentry setting for specific module.
                                   If None, sets the global default.

    Example:
        # Disable Sentry for current module:
        set_opt_out_sentry(True, __name__)

        # Disable Sentry globally:
        set_opt_out_sentry(True)

        # Enable Sentry for specific module:
        set_opt_out_sentry(False, "my_module")
    """
    global _default_opt_out, _module_sentry_settings

    if module_name is None:
        _default_opt_out = value
        # Initialize Sentry globally based on default setting
        if not _default_opt_out:
            sentry_sdk.init(
                dsn="<Enter your DSN here>",
                traces_sample_rate=1.0,
                send_default_pii=True,
            )
            print("Global Sentry error tracking is enabled.")
        else:
            sentry_sdk.init()  # Initialize with empty DSN to effectively disable
            print("Global Sentry error tracking is disabled.")
    else:
        _module_sentry_settings[module_name] = value
        print(f"Sentry error tracking is {'disabled' if value else 'enabled'} for module: {module_name}")


def is_sentry_enabled(module_name: Optional[str] = None) -> bool:
    """
    Check if Sentry error tracking is enabled for a specific module or globally.

    Args:
        module_name (Optional[str]): Module name to check. If None, checks global setting.

    Returns:
        bool: True if Sentry is enabled, False if disabled
    """
    if module_name is None:
        return not _default_opt_out
    return not _module_sentry_settings.get(module_name, _default_opt_out)


def track_errors(func=None, *, module_override: Optional[str] = None):
    """
    Decorator to automatically track errors in Sentry.
    Respects per-module and global Sentry settings.

    Args:
        func: The function to decorate
        module_override: Optional module name to override the automatic module detection

    Usage:
        @track_errors
        def your_function():
            # Your code here

        @track_errors(module_override="custom_module")
        def your_function():
            # Your code here
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get the module name from the function or use override
            mod_name = module_override or func.__module__
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if is_sentry_enabled(mod_name):
                    sentry_sdk.capture_exception(e)
                raise

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


@contextmanager
def track_errors_context(module_name: Optional[str] = None):
    """
    Context manager to track errors in Sentry.
    Respects per-module and global Sentry settings.

    Args:
        module_name: Optional module name to override the automatic module detection

    Usage:
        with track_errors_context():
            # Your code here

        with track_errors_context("custom_module"):
            # Your code here
    """
    try:
        yield
    except Exception as e:
        # If no module_name provided, get it from the caller's frame
        if module_name is None:
            frame = inspect.currentframe()
            if frame and frame.f_back:
                module_name = frame.f_back.f_globals.get("__name__")

        if is_sentry_enabled(module_name):
            sentry_sdk.capture_exception(e)
        raise


def capture_error(exception):
    """Captures the error in Sentry if it's enabled for the calling module."""
    frame = inspect.currentframe()
    if frame and frame.f_back:
        module_name = frame.f_back.f_globals.get("__name__")
        if is_sentry_enabled(module_name):
            sentry_sdk.capture_exception(exception)
