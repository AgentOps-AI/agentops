"""Tests for AgentOps decorators."""

from unittest.mock import patch

import pytest

from agentops.decorators import session
from agentops.session.session import SessionState


def test_session_basic():
    """Test basic @session decorator usage."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session
        def test_func():
            return "success"
        
        result = test_func()
        
        assert result == "success"
        mock_start.assert_called_once_with(None)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_with_tags():
    """Test @session decorator with tags."""
    test_tags = ["test_tag1", "test_tag2"]
    
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session(test_tags)
        def test_func():
            return "tagged"
        
        result = test_func()
        
        assert result == "tagged"
        mock_start.assert_called_once_with(test_tags)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_with_exception():
    """Test @session decorator when wrapped function raises an exception."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_func()
        
        mock_start.assert_called_once_with(None)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_with_args():
    """Test @session decorator with function arguments."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = True

        @session
        def func_with_args(x: int, y: int, name: str = "default") -> str:
            return f"{x} + {y} = {x + y}, name: {name}"
        
        result = func_with_args(1, 2, name="test")
        
        assert result == "1 + 2 = 3, name: test"
        mock_start.assert_called_once_with(None)
        mock_end.assert_called_once_with(
            end_state=str(SessionState.SUCCEEDED),
            is_auto_end=True
        )


def test_session_no_active_session():
    """Test @session decorator when no session is started."""
    with patch('agentops.start_session') as mock_start, \
         patch('agentops.end_session') as mock_end:
        mock_start.return_value = None  # Simulate no session started

        @session
        def test_func():
            return "no session"
        
        result = test_func()
        
        assert result == "no session"
        mock_start.assert_called_once_with(None)
        mock_end.assert_not_called()  # end_session shouldn't be called if no session was started

