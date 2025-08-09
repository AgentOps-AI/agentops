"""
Tests for the Sentry event sanitizer
"""

from agentops.common.sentry import sanitize_event, SENSITIVE_DATA_PLACEHOLDER


def test_sanitize_event_without_exception():
    """Test that events without exceptions are returned unchanged"""
    mock_event = {"message": "Test event without exception"}
    result = sanitize_event(mock_event, {})

    assert result == mock_event
    assert result is mock_event


def test_sanitize_event_empty_vars():
    """Test that events with empty vars are handled correctly"""
    mock_event = {"exception": {"values": [{"stacktrace": {"frames": [{"vars": {}}]}}]}}

    result = sanitize_event(mock_event, {})
    assert result["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"] == {}


def test_comprehensive_sanitization():
    """Comprehensive test for sanitizing passwords in various locations"""
    mock_event = {
        "exception": {
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {
                                "vars": {
                                    # Root level password
                                    "password": "super_secret",
                                    # Non-sensitive data that should be preserved
                                    "normal_var": "keep this",
                                    # Nested dictionary with password
                                    "user_config": {
                                        "username": "testuser",
                                        "password": "123password456",
                                        "settings": {"password": "nested_deeper_pw"},
                                    },
                                    # Array of primitives (should be untouched)
                                    "simple_array": [1, 2, 3, "string", True, None],
                                    # Array with dictionary containing password
                                    "users": [{"name": "user1", "password": "user1_password"}],
                                    # Complex nested structure
                                    "complex_data": [
                                        {
                                            "name": "keep_this",
                                            "items": [
                                                {"id": 1, "password": "level3_pw_1"},
                                                {"id": 2, "password": "level3_pw_2"},
                                            ],
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    result = sanitize_event(mock_event, {})

    # Get the variables dict for easier access
    frame_vars = result["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"]

    # Test root level password sanitization
    assert frame_vars["password"] == SENSITIVE_DATA_PLACEHOLDER
    assert frame_vars["normal_var"] == "keep this"

    # Test nested dictionary sanitization
    assert frame_vars["user_config"]["username"] == "testuser"
    assert frame_vars["user_config"]["password"] == SENSITIVE_DATA_PLACEHOLDER
    assert frame_vars["user_config"]["settings"]["password"] == SENSITIVE_DATA_PLACEHOLDER

    # Test array of primitives (should be untouched)
    assert frame_vars["simple_array"] == [1, 2, 3, "string", True, None]

    # Test array with dictionary containing password
    assert frame_vars["users"][0]["name"] == "user1"
    assert frame_vars["users"][0]["password"] == SENSITIVE_DATA_PLACEHOLDER

    # Test complex nested structure
    complex_data = frame_vars["complex_data"][0]
    assert complex_data["name"] == "keep_this"
    assert complex_data["items"][0]["id"] == 1
    assert complex_data["items"][0]["password"] == SENSITIVE_DATA_PLACEHOLDER
    assert complex_data["items"][1]["id"] == 2
    assert complex_data["items"][1]["password"] == SENSITIVE_DATA_PLACEHOLDER
