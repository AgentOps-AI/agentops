import pytest
from unittest.mock import patch
from agentops.sdk.decorators.sentry_manager import (
    set_opt_out_sentry,
    is_sentry_enabled,
    track_errors,
    track_errors_context,
    capture_error,
)


# Mock sentry_sdk for testing
@pytest.fixture
def mock_sentry():
    with patch("agentops.sdk.decorators.sentry_manager.sentry_sdk") as mock_sdk:
        yield mock_sdk


# Test Global Sentry Settings
class TestGlobalSentrySettings:
    def test_default_sentry_enabled(self):
        """Test that Sentry is enabled by default"""
        assert is_sentry_enabled() is True

    def test_global_opt_out(self):
        """Test global opt-out functionality"""
        set_opt_out_sentry(True)
        assert is_sentry_enabled() is False
        # Reset to default
        set_opt_out_sentry(False)

    def test_global_opt_in(self):
        """Test global opt-in functionality"""
        set_opt_out_sentry(False)
        assert is_sentry_enabled() is True


# Test Module-Level Settings
class TestModuleLevelSettings:
    def test_module_specific_setting(self):
        """Test module-specific Sentry settings"""
        test_module = "test_module"
        # Enable globally but disable for specific module
        set_opt_out_sentry(False)  # Global enable
        set_opt_out_sentry(True, test_module)  # Module disable
        assert is_sentry_enabled() is True  # Global still enabled
        assert is_sentry_enabled(test_module) is False  # Module disabled

    def test_module_override_global(self):
        """Test that module settings override global settings"""
        test_module = "test_module"
        # Disable globally but enable for specific module
        set_opt_out_sentry(True)  # Global disable
        set_opt_out_sentry(False, test_module)  # Module enable
        assert is_sentry_enabled() is False  # Global still disabled
        assert is_sentry_enabled(test_module) is True  # Module enabled


# Test Error Tracking Decorator
class TestErrorTrackingDecorator:
    def test_decorator_with_enabled_sentry(self, mock_sentry):
        """Test that errors are captured when Sentry is enabled"""
        set_opt_out_sentry(False)  # Enable Sentry

        @track_errors
        def raise_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            raise_error()

        mock_sentry.capture_exception.assert_called_once()

    def test_decorator_with_disabled_sentry(self, mock_sentry):
        """Test that errors are not captured when Sentry is disabled"""
        set_opt_out_sentry(True)  # Disable Sentry

        @track_errors
        def raise_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            raise_error()

        mock_sentry.capture_exception.assert_not_called()

    def test_decorator_with_module_override(self, mock_sentry):
        """Test decorator with explicit module override"""
        test_module = "test_module"
        set_opt_out_sentry(True)  # Global disable
        set_opt_out_sentry(False, test_module)  # Module enable

        @track_errors(module_override=test_module)
        def raise_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            raise_error()

        mock_sentry.capture_exception.assert_called_once()


# Test Context Manager
class TestContextManager:
    def test_context_manager_with_enabled_sentry(self, mock_sentry):
        """Test that errors are captured in context when Sentry is enabled"""
        set_opt_out_sentry(False)  # Enable Sentry

        with pytest.raises(ValueError):
            with track_errors_context():
                raise ValueError("Test error")

        mock_sentry.capture_exception.assert_called_once()

    def test_context_manager_with_disabled_sentry(self, mock_sentry):
        """Test that errors are not captured in context when Sentry is disabled"""
        set_opt_out_sentry(True)  # Disable Sentry

        with pytest.raises(ValueError):
            with track_errors_context():
                raise ValueError("Test error")

        mock_sentry.capture_exception.assert_not_called()

    def test_context_manager_with_module_name(self, mock_sentry):
        """Test context manager with specific module name"""
        test_module = "test_module"
        set_opt_out_sentry(True)  # Global disable
        set_opt_out_sentry(False, test_module)  # Module enable

        with pytest.raises(ValueError):
            with track_errors_context(module_name=test_module):
                raise ValueError("Test error")

        mock_sentry.capture_exception.assert_called_once()

    def test_nested_context_managers(self, mock_sentry):
        """Test nested context managers with different module settings"""
        outer_module = "outer_module"
        inner_module = "inner_module"

        set_opt_out_sentry(False)  # Global enable
        set_opt_out_sentry(True, outer_module)  # Outer module disable
        set_opt_out_sentry(False, inner_module)  # Inner module enable

        with pytest.raises(ValueError):
            with track_errors_context(module_name=outer_module):
                # This error should not be captured (outer module disabled)
                with track_errors_context(module_name=inner_module):
                    # This error should be captured (inner module enabled)
                    raise ValueError("Test error")

        # Only inner context should capture the error
        assert mock_sentry.capture_exception.call_count == 1


# Test Direct Error Capture
class TestDirectErrorCapture:
    def test_capture_error_enabled(self, mock_sentry):
        """Test direct error capture when Sentry is enabled"""
        set_opt_out_sentry(False)
        error = ValueError("Test error")
        capture_error(error)
        mock_sentry.capture_exception.assert_called_once_with(error)

    def test_capture_error_disabled(self, mock_sentry):
        """Test direct error capture when Sentry is disabled"""
        set_opt_out_sentry(True)
        error = ValueError("Test error")
        capture_error(error)
        mock_sentry.capture_exception.assert_not_called()


# Test Real-world Scenarios
class TestRealWorldScenarios:
    def test_multiple_functions_different_modules(self, mock_sentry):
        """Test multiple functions with different module settings"""
        module1 = "module1"
        module2 = "module2"

        set_opt_out_sentry(True)  # Global disable
        set_opt_out_sentry(False, module1)  # Enable module1
        set_opt_out_sentry(True, module2)  # Disable module2

        @track_errors(module_override=module1)
        def function1():
            raise ValueError("Error 1")

        @track_errors(module_override=module2)
        def function2():
            raise ValueError("Error 2")

        # Should capture error (module1 enabled)
        with pytest.raises(ValueError):
            function1()
        assert mock_sentry.capture_exception.call_count == 1

        # Should not capture error (module2 disabled)
        with pytest.raises(ValueError):
            function2()
        assert mock_sentry.capture_exception.call_count == 1  # Count shouldn't increase

    def test_error_propagation(self, mock_sentry):
        """Test that errors properly propagate through multiple layers"""
        set_opt_out_sentry(False)

        @track_errors
        def inner_function():
            raise ValueError("Inner error")

        @track_errors
        def outer_function():
            try:
                inner_function()
            except ValueError:
                raise RuntimeError("Outer error")

        with pytest.raises(RuntimeError):
            outer_function()

        # Should capture both errors
        assert mock_sentry.capture_exception.call_count == 2
