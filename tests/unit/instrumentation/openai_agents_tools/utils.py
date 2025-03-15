"""
Utility functions for working with OpenAI Responses API data.

This module provides utility functions for working with OpenAI Responses API data,
including functions for conversion, serialization, and validation.
"""

import json
from typing import Any, Dict, List, Optional, Union

def serialize_response(response: Any) -> Dict[str, Any]:
    """
    Serialize an OpenAI Responses API response to a JSON-serializable dict.
    
    This function handles both Pydantic models and dictionaries, ensuring that
    all nested structures are properly serialized for JSON.
    
    Args:
        response: The OpenAI Responses API response to serialize.
                 Can be a Pydantic model or a dict.
    
    Returns:
        A JSON-serializable dict representation of the response.
    """
    if hasattr(response, 'model_dump'):
        # It's a Pydantic model
        return response.model_dump()
    elif isinstance(response, dict):
        # It's already a dict, but might contain Pydantic models
        result = {}
        for key, value in response.items():
            if hasattr(value, 'model_dump'):
                result[key] = value.model_dump()
            elif isinstance(value, list):
                result[key] = [
                    item.model_dump() if hasattr(item, 'model_dump') else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    else:
        # Try to convert to dict if it has a __dict__ attribute
        if hasattr(response, '__dict__'):
            return serialize_response(response.__dict__)
        return response

def validate_response(response_data: Dict[str, Any]) -> bool:
    """
    Validate that response data contains the expected structure for a Response object.
    
    This function checks that the response data contains the expected fields for a
    Response object, such as id, created_at, model, object, and output.
    
    Args:
        response_data: The response data to validate.
    
    Returns:
        True if the response data is valid, False otherwise.
    """
    required_fields = ['id', 'created_at', 'model', 'object', 'output']
    for field in required_fields:
        if field not in response_data:
            print(f"Missing required field: {field}")
            return False
    
    # Check that object is 'response'
    if response_data['object'] != 'response':
        print(f"Invalid object type: {response_data['object']}")
        return False
    
    # Check that output is a list
    if not isinstance(response_data['output'], list):
        print(f"Output is not a list: {type(response_data['output'])}")
        return False
    
    return True

def create_generation_span_data(response_data: Dict[str, Any], input: str) -> Dict[str, Any]:
    """
    Create a generation span data object from response data and input.
    
    This function creates a generation span data object that can be used in AgentOps
    instrumentation tests, using real response data and the provided input.
    
    Args:
        response_data: The response data from the OpenAI Responses API.
        input: The input prompt that was used to generate the response.
    
    Returns:
        A generation span data object suitable for use in AgentOps instrumentation tests.
    """
    generation_span_data = {
        "model": response_data.get("model", "gpt-4o"),
        "model_config": {
            "temperature": 0.7,
            "top_p": 1.0
        },
        "input": input,
        "output": response_data,
        "usage": {}
    }
    
    # Extract usage data if available
    if "usage" in response_data:
        usage = response_data["usage"]
        generation_span_data["usage"] = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    return generation_span_data

def extract_content(response_data: Dict[str, Any]) -> str:
    """
    Extract the text content from a response.
    
    This function extracts the text content from the first message in the response.
    
    Args:
        response_data: The response data from the OpenAI Responses API.
    
    Returns:
        The text content from the first message in the response, or an empty string if
        no text content is found.
    """
    if not response_data or 'output' not in response_data:
        return ""
    
    for item in response_data['output']:
        if item.get('type') == 'message' and 'content' in item:
            for content in item['content']:
                if content.get('type') == 'output_text' and 'text' in content:
                    return content['text']
    
    return ""