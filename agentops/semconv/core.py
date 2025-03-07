"""Core attributes applicable to all spans."""

class CoreAttributes:
    """Core attributes applicable to all spans."""
    
    # Identity attributes
    NAME = "name"                      # Name of the component
    DESCRIPTION = "description"        # Description of the component
    
    # Status attributes
    STATUS = "status"                  # Status (success, error, etc.)
    ERROR_TYPE = "error.type"          # Type of error if status is error
    ERROR_MESSAGE = "error.message"    # Error message if status is error
    
    # Metadata
    TAGS = "tags"                      # User-defined tags (array)
