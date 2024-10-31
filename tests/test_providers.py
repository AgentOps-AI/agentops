import unittest
from unittest.mock import MagicMock, patch
import litellm
import openai
from openai.resources.chat.completions import Completions, AsyncCompletions
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice, CompletionUsage

from agentops.llms.openai import OpenAiProvider
from agentops.llms.litellm import LiteLLMProvider

class TestProviders(unittest.TestCase):
    def setUp(self):
        # Create mock clients
        self.mock_openai_client = MagicMock()
        self.mock_litellm_client = MagicMock()
        
        # Store original methods before any overrides
        self.original_litellm_completion = litellm.completion
        self.original_litellm_acompletion = litellm.acompletion
        
        # Test parameters
        self.test_messages = [{"role": "user", "content": "test"}]
        self.test_params = {
            "messages": self.test_messages,
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 100
        }

        # Create a proper ChatCompletion mock response
        message = ChatCompletionMessage(
            role="assistant",
            content="test response"
        )
        
        choice = Choice(
            index=0,
            message=message,
            finish_reason="stop"
        )
        
        usage = CompletionUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        
        self.mock_response = ChatCompletion(
            id="test_id",
            model="gpt-3.5-turbo",
            object="chat.completion",
            choices=[choice],
            usage=usage,
            created=1234567890
        )

    def tearDown(self):
        # Restore original methods after each test
        litellm.completion = self.original_litellm_completion
        litellm.acompletion = self.original_litellm_acompletion

    @patch('openai.resources.chat.completions.Completions.create')
    def test_provider_override_independence(self, mock_openai_create):
        """Test that OpenAI and LiteLLM providers don't interfere with each other's method overrides"""
        
        # Initialize both providers
        openai_provider = OpenAiProvider(self.mock_openai_client)
        litellm_provider = LiteLLMProvider(self.mock_litellm_client)
        
        # Set up mock returns
        mock_openai_create.return_value = self.mock_response
        
        # Create a MagicMock for litellm completion
        mock_litellm_completion = MagicMock(return_value=self.mock_response)
        
        try:
            # Store original and set mock
            original_litellm_completion = litellm.completion
            litellm.completion = mock_litellm_completion
            
            # Override both providers
            openai_provider.override()
            litellm_provider.override()
            
            # Test OpenAI completion
            Completions.create(**self.test_params)
            self.assertTrue(
                mock_openai_create.called,
                "OpenAI's create method should be called"
            )
            
            # Test LiteLLM completion
            litellm.completion(**self.test_params)
            self.assertTrue(
                mock_litellm_completion.called,
                "LiteLLM's completion method should be called"
            )
            
        finally:
            # Restore litellm's completion function
            litellm.completion = original_litellm_completion
            
            # Undo overrides
            openai_provider.undo_override()
            litellm_provider.undo_override()

    @patch('openai.resources.chat.completions.Completions.create')
    def test_provider_override_order_independence(self, mock_openai_create):
        """Test that the order of provider overrides doesn't matter"""
        
        # Set up mock returns
        mock_openai_create.return_value = self.mock_response
        
        # Create a MagicMock for litellm completion
        mock_litellm_completion = MagicMock(return_value=self.mock_response)
        
        try:
            # Store original and set mock
            original_litellm_completion = litellm.completion
            litellm.completion = mock_litellm_completion
            
            # Test overriding OpenAI first, then LiteLLM
            openai_provider = OpenAiProvider(self.mock_openai_client)
            litellm_provider = LiteLLMProvider(self.mock_litellm_client)
            
            openai_provider.override()
            first_openai_create = Completions.create
            litellm_provider.override()
            
            # Test both providers work independently
            Completions.create(**self.test_params)
            litellm.completion(**self.test_params)
            
            # Verify methods weren't affected by each other
            self.assertIs(Completions.create, first_openai_create)
            
            # Cleanup first test
            litellm_provider.undo_override()
            openai_provider.undo_override()
            
            # Reset the mock for the second test
            mock_litellm_completion.reset_mock()
            
            # Now test overriding LiteLLM first, then OpenAI
            litellm_provider = LiteLLMProvider(self.mock_litellm_client)
            openai_provider = OpenAiProvider(self.mock_openai_client)
            
            litellm_provider.override()
            first_litellm_method = litellm.completion
            openai_provider.override()
            
            # Test both providers work independently
            Completions.create(**self.test_params)
            litellm.completion(**self.test_params)
            
            # Verify methods weren't affected by each other
            self.assertIs(litellm.completion, first_litellm_method)
            
        finally:
            # Restore litellm's completion function
            litellm.completion = original_litellm_completion
            
            # Cleanup
            openai_provider.undo_override()
            litellm_provider.undo_override()


if __name__ == '__main__':
    unittest.main()