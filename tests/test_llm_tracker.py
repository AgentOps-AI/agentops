import pytest
from agentops.llm_tracker import LlmTracker
from agentops import Client
from unittest.mock import MagicMock, patch


class TestLlmTracker:
    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=Client)

    @pytest.fixture
    def llm_tracker(self, mock_client):
        return LlmTracker(mock_client)

    @pytest.fixture
    def mock_openai_response(self):
        return {
            'object': 'text.completion',
            'choices': [{'message': {'content': 'Hello, world!'}}],
            'model': 'text-davinci-002'
        }

    @patch('agentops.llm_tracker.get_ISO_time')
    def test_handle_response_openai(self, mock_get_ISO_time, llm_tracker, mock_openai_response):
        mock_get_ISO_time.return_value = '2022-01-01T00:00:00Z'
        kwargs = {'messages': 'Hello, world!'}
        result = llm_tracker._handle_response_openai(
            mock_openai_response, kwargs, '2022-01-01T00:00:00Z')

        assert result['object'] == 'text.completion'
        assert result['choices'][0]['message']['content'] == 'Hello, world!'
        assert llm_tracker.client.record.called

    def test_override_api(self, llm_tracker):
        with patch.object(llm_tracker, '_override_method') as mock_override_method:
            llm_tracker.override_api('openai')
            assert mock_override_method.call_count == 6
