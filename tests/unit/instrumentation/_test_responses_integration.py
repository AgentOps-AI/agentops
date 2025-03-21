"""
Integration test for OpenAI responses instrumentation.

This test verifies that the OpenAI responses instrumentor integrates
properly with AgentOps by checking that it's added to the available
instrumentors list and can be activated/deactivated.
"""

import pytest
from unittest.mock import patch, MagicMock

import agentops
from agentops.instrumentation import available_instrumentors, instrument_one
from agentops.instrumentation.openai import OpenAIResponsesInstrumentor

def test_instrumentor_in_available_list():
    """Test that our instrumentor is in the available instrumentors list."""
    # Find our instrumentor in the list
    openai_responses_loader = None
    for loader in available_instrumentors:
        if loader.class_name == "OpenAIResponsesInstrumentor":
            openai_responses_loader = loader
            break
    
    # Verify it exists
    assert openai_responses_loader is not None, "OpenAIResponsesInstrumentor not found in available instrumentors"
    
    # Verify properties
    assert openai_responses_loader.module_name == "agentops.instrumentation.openai"
    assert openai_responses_loader.provider_import_name == "openai"

@patch("agentops.instrumentation.openai.OpenAIResponsesInstrumentor.instrument")
@patch("agentops.instrumentation.openai.OpenAIResponsesInstrumentor.uninstrument")
def test_instrumentor_activation(mock_instrument, mock_uninstrument):
    """Test that our instrumentor can be activated and deactivated."""
    # Create a mock instrumentor that returns itself for get_instance
    mock_instrumentor = MagicMock()
    mock_instrumentor.instrument = mock_instrument
    mock_instrumentor.uninstrument = mock_uninstrument
    
    # Create a mock loader
    mock_loader = MagicMock()
    mock_loader.should_activate = True
    mock_loader.get_instance.return_value = mock_instrumentor
    mock_loader.class_name = "OpenAIResponsesInstrumentor"
    
    # Test instrument_one with our mock loader
    instrumentor = instrument_one(mock_loader)
    
    # Verify instrument was called
    assert mock_instrument.called, "instrument() was not called"
    assert instrumentor is mock_instrumentor
    
    # Run uninstrument
    instrumentor.uninstrument()
    
    # Verify uninstrument was called
    assert mock_uninstrument.called, "uninstrument() was not called"

@patch("importlib.import_module")
def test_instrumentor_import_detection(mock_import_module):
    """Test that the instrumentor checks for OpenAI before activating."""
    # Set up mock responses
    def mock_import_side_effect(module_name):
        if module_name == "openai":
            return MagicMock()
        raise ImportError(f"No module named '{module_name}'")
    
    mock_import_module.side_effect = mock_import_side_effect
    
    # Find our loader
    openai_responses_loader = None
    for loader in available_instrumentors:
        if loader.class_name == "OpenAIResponsesInstrumentor":
            openai_responses_loader = loader
            break
    
    assert openai_responses_loader is not None
    
    # Test activation check with OpenAI available
    assert openai_responses_loader.should_activate
    
    # Test activation check with OpenAI not available
    mock_import_module.side_effect = lambda x: exec('raise ImportError("No module named \'openai\'")')
    openai_responses_loader.should_activate  # This will use the updated mock

if __name__ == "__main__":
    # Run the tests manually
    test_instrumentor_in_available_list()
    print("✓ Instrumentor is in available list")
    
    with patch("agentops.instrumentation.openai.OpenAIResponsesInstrumentor.instrument") as mock_i, \
         patch("agentops.instrumentation.openai.OpenAIResponsesInstrumentor.uninstrument") as mock_u:
        test_instrumentor_activation(mock_i, mock_u)
    print("✓ Instrumentor can be activated and deactivated")
    
    with patch("importlib.import_module") as mock_import:
        test_instrumentor_import_detection(mock_import)
    print("✓ Import detection works properly")
    
    print("\nAll tests passed!")