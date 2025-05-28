"""
Tests for API consistency changes in agentops.init().

This module tests the changes to the init() function return value behavior
that were reverted in commit bf850af to maintain backward compatibility.
"""

import pytest
from unittest.mock import MagicMock, patch

import agentops
from agentops.legacy import Session


class TestInitReturnValueConsistency:
    """Tests for agentops.init() return value consistency."""

    def setup_method(self):
        """Reset client state before each test."""
        # Reset the global client
        agentops._client = agentops.Client()
        agentops._client._initialized = False

    @patch("agentops.client.Client.init")
    def test_init_returns_client_init_result(self, mock_client_init):
        """Test that init() returns the result of _client.init()."""
        # Setup mock to return a specific value
        expected_result = MagicMock()
        mock_client_init.return_value = expected_result

        # Call init
        result = agentops.init(api_key="test-key")

        # Verify the result is what client.init() returned
        assert result == expected_result

        # Verify client.init was called with correct parameters
        mock_client_init.assert_called_once()

    @patch("agentops.client.Client.init")
    def test_init_auto_start_session_true_returns_session(self, mock_client_init):
        """Test that init() with auto_start_session=True returns a Session object."""
        # Setup mock to return a Session (typical behavior when auto_start_session=True)
        mock_session = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session

        # Call init with auto_start_session=True
        result = agentops.init(api_key="test-key", auto_start_session=True)

        # Verify the result is the Session object
        assert result == mock_session

        # Verify client.init was called with auto_start_session=True
        mock_client_init.assert_called_once()
        call_kwargs = mock_client_init.call_args[1]
        assert call_kwargs["auto_start_session"] is True

    @patch("agentops.client.Client.init")
    def test_init_auto_start_session_false_returns_none(self, mock_client_init):
        """Test that init() with auto_start_session=False returns None."""
        # Setup mock to return None (typical behavior when auto_start_session=False)
        mock_client_init.return_value = None

        # Call init with auto_start_session=False
        result = agentops.init(api_key="test-key", auto_start_session=False)

        # Verify the result is None
        assert result is None

        # Verify client.init was called with auto_start_session=False
        mock_client_init.assert_called_once()
        call_kwargs = mock_client_init.call_args[1]
        assert call_kwargs["auto_start_session"] is False

    @patch("agentops.client.Client.init")
    def test_init_default_auto_start_session_behavior(self, mock_client_init):
        """Test that init() with default auto_start_session returns appropriate value."""
        # Setup mock to return a Session (default behavior typically starts a session)
        mock_session = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session

        # Call init without specifying auto_start_session
        result = agentops.init(api_key="test-key")

        # Verify the result is the Session object
        assert result == mock_session

        # Verify client.init was called
        mock_client_init.assert_called_once()

    @patch("agentops.client.Client.init")
    def test_init_passes_all_parameters(self, mock_client_init):
        """Test that init() passes all parameters to client.init()."""
        # Setup mock
        mock_client_init.return_value = None

        # Call init with various parameters
        result = agentops.init(  # noqa: F841
            api_key="test-key",
            endpoint="https://test.endpoint.com",
            app_url="https://test.app.com",
            max_wait_time=5000,
            max_queue_size=512,
            default_tags=["test", "integration"],
            instrument_llm_calls=True,
            auto_start_session=False,
            skip_auto_end_session=True,
            env_data_opt_out=True,
            custom_param="custom_value",
        )

        # Verify client.init was called with all parameters
        mock_client_init.assert_called_once()
        call_args, call_kwargs = mock_client_init.call_args

        # Check that all expected parameters were passed
        expected_params = {
            "api_key": "test-key",
            "endpoint": "https://test.endpoint.com",
            "app_url": "https://test.app.com",
            "max_wait_time": 5000,
            "max_queue_size": 512,
            "default_tags": ["test", "integration"],
            "instrument_llm_calls": True,
            "auto_start_session": False,
            "skip_auto_end_session": True,
            "env_data_opt_out": True,
            "custom_param": "custom_value",
        }

        for param, value in expected_params.items():
            assert call_kwargs[param] == value

    @patch("agentops.client.Client.init")
    def test_init_exception_propagation(self, mock_client_init):
        """Test that exceptions from client.init() are properly propagated."""
        # Setup mock to raise an exception
        test_exception = ValueError("Test initialization error")
        mock_client_init.side_effect = test_exception

        # Call init and expect the exception to be raised
        with pytest.raises(ValueError, match="Test initialization error"):
            agentops.init(api_key="test-key")

        # Verify client.init was called
        mock_client_init.assert_called_once()


class TestInitBackwardCompatibility:
    """Tests for backward compatibility of agentops.init()."""

    def setup_method(self):
        """Reset client state before each test."""
        # Reset the global client
        agentops._client = agentops.Client()
        agentops._client._initialized = False

    @patch("agentops.client.Client.init")
    def test_init_return_value_used_in_conditional(self, mock_client_init):
        """Test that init() return value can be used in conditional statements."""
        # Test case 1: init returns a Session (truthy)
        mock_session = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session

        result = agentops.init(api_key="test-key", auto_start_session=True)

        # Should be able to use in conditional
        if result:
            session_available = True
        else:
            session_available = False

        assert session_available is True
        assert result == mock_session

        # Test case 2: init returns None (falsy)
        mock_client_init.return_value = None

        result = agentops.init(api_key="test-key", auto_start_session=False)

        # Should be able to use in conditional
        if result:
            session_available = True
        else:
            session_available = False

        assert session_available is False
        assert result is None

    @patch("agentops.client.Client.init")
    def test_init_return_value_assignment_patterns(self, mock_client_init):
        """Test common assignment patterns with init() return value."""
        # Pattern 1: Direct assignment
        mock_session = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session

        session = agentops.init(api_key="test-key")
        assert session == mock_session

        # Pattern 2: Assignment with default
        mock_client_init.return_value = None

        session = agentops.init(api_key="test-key") or "no_session"
        assert session == "no_session"

        # Pattern 3: Conditional assignment
        mock_client_init.return_value = mock_session

        result = agentops.init(api_key="test-key")
        session = result if result else None
        assert session == mock_session

    @patch("agentops.client.Client.init")
    def test_init_chaining_with_session_methods(self, mock_client_init):
        """Test that init() return value can be used for method chaining when appropriate."""
        # Create a mock session with methods
        mock_session = MagicMock(spec=Session)
        # Add the method to the mock before using it
        mock_session.some_method = MagicMock(return_value="method_result")
        mock_client_init.return_value = mock_session

        # Should be able to chain methods when session is returned
        result = agentops.init(api_key="test-key")
        if result:
            method_result = result.some_method()
            assert method_result == "method_result"

    @patch("agentops.client.Client.init")
    def test_init_multiple_calls_behavior(self, mock_client_init):
        """Test behavior of multiple init() calls."""
        # First call returns a session
        mock_session1 = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session1

        result1 = agentops.init(api_key="test-key")
        assert result1 == mock_session1

        # Second call returns None (already initialized)
        mock_client_init.return_value = None

        result2 = agentops.init(api_key="test-key")
        assert result2 is None

        # Verify both calls were made
        assert mock_client_init.call_count == 2


class TestInitAPIConsistencyRegression:
    """Regression tests for the API consistency changes that were reverted."""

    def setup_method(self):
        """Reset client state before each test."""
        # Reset the global client
        agentops._client = agentops.Client()
        agentops._client._initialized = False

    @patch("agentops.client.Client.init")
    def test_init_does_not_always_return_client(self, mock_client_init):
        """Test that init() does NOT always return the client instance (reverted behavior)."""
        # This test ensures the reverted change is working correctly
        # The original change made init() always return the client, but this was reverted

        # Setup mock to return None
        mock_client_init.return_value = None

        # Call init
        result = agentops.init(api_key="test-key", auto_start_session=False)

        # Should return None, not the client instance
        assert result is None
        assert result != agentops._client

    @patch("agentops.client.Client.init")
    def test_init_return_value_matches_client_init(self, mock_client_init):
        """Test that init() return value exactly matches client.init() return value."""
        # Test with various return values
        test_values = [None, MagicMock(spec=Session), "string_value", 42, {"dict": "value"}, ["list", "value"]]

        for test_value in test_values:
            # Reset mock
            mock_client_init.reset_mock()
            mock_client_init.return_value = test_value

            # Call init
            result = agentops.init(api_key="test-key")

            # Should return exactly what client.init() returned
            assert result == test_value
            assert result is test_value  # Same object reference

    def test_init_function_signature_unchanged(self):
        """Test that init() function signature is unchanged."""
        import inspect

        # Get the signature of the init function
        signature = inspect.signature(agentops.init)

        # Verify key parameters exist
        expected_params = [
            "api_key",
            "endpoint",
            "app_url",
            "max_wait_time",
            "max_queue_size",
            "default_tags",
            "instrument_llm_calls",
            "auto_start_session",
            "skip_auto_end_session",
            "env_data_opt_out",
        ]

        for param in expected_params:
            assert param in signature.parameters, f"Parameter {param} missing from init() signature"

    @patch("agentops.client.Client.init")
    def test_init_preserves_client_state(self, mock_client_init):
        """Test that init() preserves client state regardless of return value."""
        # Setup mock
        mock_client_init.return_value = None

        # Get initial client reference
        initial_client = agentops._client

        # Call init
        result = agentops.init(api_key="test-key")

        # Client reference should be unchanged
        assert agentops._client is initial_client

        # Return value should not affect client state
        assert result != agentops._client


class TestInitDocumentationExamples:
    """Tests based on common documentation examples to ensure compatibility."""

    def setup_method(self):
        """Reset client state before each test."""
        # Reset the global client
        agentops._client = agentops.Client()
        agentops._client._initialized = False

    @patch("agentops.client.Client.init")
    def test_common_usage_pattern_1(self, mock_client_init):
        """Test: session = agentops.init(api_key="...", auto_start_session=True)"""
        mock_session = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session

        # Common pattern from documentation
        session = agentops.init(api_key="test-key", auto_start_session=True)

        # Should work as expected
        assert session == mock_session

    @patch("agentops.client.Client.init")
    def test_common_usage_pattern_2(self, mock_client_init):
        """Test: agentops.init(api_key="...", auto_start_session=False)"""
        mock_client_init.return_value = None

        # Common pattern from documentation
        result = agentops.init(api_key="test-key", auto_start_session=False)

        # Should return None
        assert result is None

    @patch("agentops.client.Client.init")
    def test_common_usage_pattern_3(self, mock_client_init):
        """Test: if agentops.init(...): # do something"""
        # Test truthy case
        mock_session = MagicMock(spec=Session)
        mock_client_init.return_value = mock_session

        if agentops.init(api_key="test-key"):
            truthy_result = True
        else:
            truthy_result = False

        assert truthy_result is True

        # Test falsy case
        mock_client_init.return_value = None

        if agentops.init(api_key="test-key"):
            falsy_result = True
        else:
            falsy_result = False

        assert falsy_result is False
