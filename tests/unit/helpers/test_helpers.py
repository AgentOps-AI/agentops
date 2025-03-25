"""Tests for the config helper functions."""

import pytest

from agentops.helpers.config import get_config, get_tags_from_config
from agentops.config import Config


class TestConfigHelpers:
    """Test suite for configuration helper functions."""
    
    def test_get_config_returns_valid_instance(self):
        """Test that get_config returns a valid Config instance."""
        # Call the helper function
        config = get_config()
        
        # Verify it returns a Config instance
        assert isinstance(config, Config)
        
        # Verify it has the expected attributes
        assert hasattr(config, 'api_key')
        assert hasattr(config, 'endpoint')
        assert hasattr(config, 'default_tags')
    
    def test_get_config_returns_singleton(self):
        """Test that get_config returns the same Config instance each time."""
        # Call the helper function twice
        config1 = get_config()
        config2 = get_config()
        
        # Verify they are the same object (singleton pattern)
        assert config1 is config2
        assert isinstance(config1, Config)
    
    def test_get_tags_from_config_with_actual_config(self):
        """Test that get_tags_from_config returns tags from the actual application config."""
        # Get the actual application config
        config = get_config()
        original_tags = config.default_tags
        
        try:
            # Temporarily set some test tags
            test_tags = {"test_tag1", "test_tag2"}
            config.default_tags = test_tags
            
            # Call the helper function
            tags = get_tags_from_config()
            
            # Verify it returns the expected tags
            assert isinstance(tags, list)
            assert set(tags) == test_tags
        finally:
            # Restore the original tags
            config.default_tags = original_tags
    
    def test_get_tags_from_config_with_empty_tags(self):
        """Test that get_tags_from_config returns an empty list when no tags are set."""
        # Get the actual application config
        config = get_config()
        original_tags = config.default_tags
        
        try:
            # Temporarily set empty tags
            config.default_tags = set()
            
            # Call the helper function
            tags = get_tags_from_config()
            
            # Verify it returns an empty list
            assert tags == []
        finally:
            # Restore the original tags
            config.default_tags = original_tags