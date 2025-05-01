"""Attributes for IBM watsonx.ai model instrumentation.

This module provides attribute extraction functions for IBM watsonx.ai model operations,
focusing on token usage recording.
"""
from typing import Any, Dict, Optional, Tuple
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.instrumentation.ibm_watsonx_ai.attributes.common import extract_params_attributes

def get_generate_attributes(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None) -> AttributeMap:
    """Extract token usage attributes from generate method calls.
    
    Args:
        args: Positional arguments passed to the method
        kwargs: Keyword arguments passed to the method
        return_value: Return value from the method
        
    Returns:
        Dictionary of token usage attributes to set on the span
    """
    attributes = {}
    
    # Extract prompt from args or kwargs
    prompt = None
    if args and len(args) > 0:
        prompt = args[0]
    elif kwargs and 'prompt' in kwargs:
        prompt = kwargs['prompt']
        
    if prompt:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = prompt
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"
    
    # Extract parameters from args or kwargs
    params = None
    if args and len(args) > 1:
        params = args[1]
    elif kwargs and 'params' in kwargs:
        params = kwargs['params']
        
    if params:
        attributes.update(extract_params_attributes(params))
                
    # Extract response information
    if return_value:
        if isinstance(return_value, dict):
            # Extract model information
            if 'model_id' in return_value:
                attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value['model_id']
                
            # Handle results
            if 'results' in return_value:
                for idx, result in enumerate(return_value['results']):
                    # Extract completion
                    if 'generated_text' in result:
                        attributes[MessageAttributes.COMPLETION_CONTENT.format(i=idx)] = result['generated_text']
                        attributes[MessageAttributes.COMPLETION_ROLE.format(i=idx)] = "assistant"
                        attributes[MessageAttributes.COMPLETION_TYPE.format(i=idx)] = "text"
                    
                    # Extract token usage
                    if 'input_token_count' in result:
                        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = result['input_token_count']
                    if 'generated_token_count' in result:
                        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = result['generated_token_count']
                    if 'input_token_count' in result and 'generated_token_count' in result:
                        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = result['input_token_count'] + result['generated_token_count']
                        
                    if 'stop_reason' in result:
                        attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = result['stop_reason']
                
    return attributes

def get_tokenize_attributes(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None) -> AttributeMap:
    """Extract attributes from tokenize method calls.
    
    Args:
        args: Positional arguments passed to the method
        kwargs: Keyword arguments passed to the method
        return_value: Return value from the method
        
    Returns:
        Dictionary of attributes to set on the span
    """
    attributes = {}
    
    # Extract input from args or kwargs
    prompt = None
    if args and len(args) > 0:
        prompt = args[0]
    elif kwargs and "prompt" in kwargs:
        prompt = kwargs["prompt"]
        
    if prompt:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = prompt
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"
        
    # Extract response information
    if return_value and isinstance(return_value, dict):
        if "model_id" in return_value:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value["model_id"]
        if "result" in return_value:
            attributes["ibm.watsonx.tokenize.result"] = str(return_value["result"])
            if "token_count" in return_value["result"]:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = return_value["result"]["token_count"]
            
    return attributes

def get_model_details_attributes(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None) -> AttributeMap:
    """Extract attributes from get_details method calls.
    
    Args:
        args: Positional arguments passed to the method
        kwargs: Keyword arguments passed to the method
        return_value: Return value from the method
        
    Returns:
        Dictionary of attributes to set on the span
    """
    if not isinstance(return_value, dict):
        return {}
        
    # Basic model information
    attributes = {
        f"ibm.watsonx.model.{key}": value
        for key, value in return_value.items()
        if key in ["model_id", "label", "provider", "source", "short_description", "long_description", 
                  "number_params", "input_tier", "output_tier"]
    }
    
    # Model functions
    if "functions" in return_value:
        attributes["ibm.watsonx.model.functions"] = str([func["id"] for func in return_value["functions"]])
        
    # Model tasks
    if "tasks" in return_value:
        task_info = [
            {k: v for k, v in task.items() if k in ["id", "ratings", "tags"]}
            for task in return_value["tasks"]
        ]
        attributes["ibm.watsonx.model.tasks"] = str(task_info)
        
    # Model limits
    if "model_limits" in return_value:
        limits = return_value["model_limits"]
        attributes.update({
            f"ibm.watsonx.model.{key}": value
            for key, value in limits.items()
            if key in ["max_sequence_length", "max_output_tokens", "training_data_max_records"]
        })
        
    # Service tier limits
    if "limits" in return_value:
        for tier, tier_limits in return_value["limits"].items():
            attributes.update({
                f"ibm.watsonx.model.limits.{tier}.{key}": value
                for key, value in tier_limits.items()
                if key in ["call_time", "max_output_tokens"]
            })
            
    # Model lifecycle
    if "lifecycle" in return_value:
        attributes.update({
            f"ibm.watsonx.model.lifecycle.{stage['id']}": stage["start_date"]
            for stage in return_value["lifecycle"]
            if "id" in stage and "start_date" in stage
        })
        
    # Training parameters
    if "training_parameters" in return_value:
        attributes.update({
            f"ibm.watsonx.model.training.{key}": str(value) if isinstance(value, dict) else value
            for key, value in return_value["training_parameters"].items()
        })
        
    return attributes

def get_generate_text_stream_attributes(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Optional[Any] = None) -> AttributeMap:
    """Extract token usage attributes from generate_text_stream method calls.
    
    Args:
        args: Positional arguments passed to the method
        kwargs: Keyword arguments passed to the method
        return_value: Return value from the method
        
    Returns:
        Dictionary of token usage attributes to set on the span
    """
    attributes = {}
    
    # Extract prompt from args or kwargs
    prompt = None
    if args and len(args) > 0:
        prompt = args[0]
    elif kwargs and 'prompt' in kwargs:
        prompt = kwargs['prompt']
        
    if prompt:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = prompt
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"
    
    # Extract parameters from args or kwargs
    params = None
    if args and len(args) > 1:
        params = args[1]
    elif kwargs and 'params' in kwargs:
        params = kwargs['params']
        
    if params:
        attributes.update(extract_params_attributes(params))
                
    # For streaming responses, we'll update the attributes as we receive chunks
    if return_value and isinstance(return_value, dict):
        # Extract model information
        if 'model_id' in return_value:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = return_value['model_id']
            
        # Handle results
        if 'results' in return_value:
            for idx, result in enumerate(return_value['results']):
                # Extract completion
                if 'generated_text' in result:
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=idx)] = result['generated_text']
                    attributes[MessageAttributes.COMPLETION_ROLE.format(i=idx)] = "assistant"
                    attributes[MessageAttributes.COMPLETION_TYPE.format(i=idx)] = "text"
                
                # Extract token usage
                if 'input_token_count' in result:
                    attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = result['input_token_count']
                if 'generated_token_count' in result:
                    attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = result['generated_token_count']
                if 'input_token_count' in result and 'generated_token_count' in result:
                    attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = result['input_token_count'] + result['generated_token_count']
                    
                if 'stop_reason' in result:
                    attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = result['stop_reason']
                
    return attributes 