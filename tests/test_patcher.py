# import pytest
# from unittest.mock import MagicMock
# from agentops.llm_tracker import LlmTracker
#
# # Mock the openai library
#
#
# @pytest.fixture
# def mock_openai(mocker):
#     mock = mocker.MagicMock()
#     mocker.patch.dict('sys.modules', {'openai': mock})
#     return mock
#
# # Test that the correct methods are overridden for version >= 1.0.0
#
#
# def test_override_api_version_ge_1(mock_openai):
#     mock_openai.__version__ = '1.0.0'  # Version is exactly 1.0.0
#     tracker = LlmTracker(client=MagicMock())
#
#     original_method = MagicMock()
#     mock_openai.chat = MagicMock(completions=MagicMock(create=original_method))
#
#     tracker.override_api('openai')
#
#     # The original method should be replaced with a new method
#     assert mock_openai.chat.completions.create != original_method
#     assert callable(mock_openai.chat.completions.create)
#
# # Test that the correct methods are overridden for version < 1.0.0
#
#
# def test_override_api_version_lt_1(mock_openai):
#     mock_openai.__version__ = '0.9.9'  # Version is less than 1.0.0
#     tracker = LlmTracker(client=MagicMock())
#
#     original_method = MagicMock()
#     mock_openai.ChatCompletion = MagicMock(create=original_method)
#
#     tracker.override_api('openai')
#
#     # The original method should be replaced with a new method
#     assert mock_openai.ChatCompletion.create != original_method
#     assert callable(mock_openai.ChatCompletion.create)
#
# # Test that the override_api method handles missing __version__ attribute
#
#
# def test_override_api_missing_version_attribute(mocker):
#     mock_openai = mocker.MagicMock()
#     mocker.patch.dict('sys.modules', {'openai': mock_openai})
#     tracker = LlmTracker(client=MagicMock())
#
#     # This should not raise an error, and should use the methods for version < 1.0.0
#     tracker.override_api('openai')
#
#     # Now you need to assert that the correct methods for version < 1.0.0 are overridden
#     # Assuming 'ChatCompletion.create' is the method to be overridden for version < 1.0.0
#     assert hasattr(mock_openai, 'ChatCompletion')
#     assert callable(mock_openai.ChatCompletion.create)
