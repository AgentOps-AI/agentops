"""Helper functions for accessing configuration values.

This module provides utility functions for accessing configuration values from
the global Config object in a safe way.
"""

from typing import List, Any

from agentops.config import Config


def get_config() -> Config:
    """Get the global configuration object from the Client singleton.
    
    Returns:
        The Config instance from the global Client
    """
    from agentops import get_client
    return get_client().config


def get_tags_from_config() -> List[str]:
    """Get tags from the global configuration.
    
    Returns:
        List of tags if they exist in the configuration, or empty list
    """
    config = get_config()
    if config.default_tags:
        return list(config.default_tags)
    return []  # Return empty list for empty tags set