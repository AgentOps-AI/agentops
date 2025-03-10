from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from opentelemetry.trace import Span, StatusCode

from agentops.sdk.spanned import SpannedBase


class LLMSpan(SpannedBase):
    """
    Represents an LLM span, which tracks LLM operations.
    
    LLM spans are typically long-running operations that involve sending a prompt
    to an LLM and receiving a response.
    """
    
    def __init__(
        self,
        name: str,
        model: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        **kwargs
    ):
        """
        Initialize an LLM span.
        
        Args:
            name: Name of the operation
            model: Name of the LLM model
            parent: Optional parent span or spanned object
            **kwargs: Additional keyword arguments
        """
        # Set default values
        kwargs.setdefault("kind", "llm")
        kwargs.setdefault("immediate_export", True)  # LLM calls are typically exported immediately
        
        # Initialize base class
        super().__init__(name=name, kind="llm", parent=parent, **kwargs)
        
        # Store LLM-specific attributes
        self._model = model
        self._prompt = None
        self._response = None
        self._tokens_prompt = 0
        self._tokens_completion = 0
        self._tokens_total = 0
        self._cost = 0.0
        
        # Set attributes
        self._attributes.update({
            "llm.name": name,
            "llm.model": model,
        })
    
    def set_prompt(self, prompt: Union[str, List[Dict[str, str]]]) -> None:
        """
        Set the LLM prompt.
        
        Args:
            prompt: Prompt sent to the LLM (string or chat messages)
        """
        self._prompt = prompt
        
        # Convert prompt to string if it's a list of messages
        if isinstance(prompt, list):
            prompt_str = str(prompt)
        else:
            prompt_str = prompt
        
        self.set_attribute("llm.prompt", prompt_str)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def set_response(self, response: str) -> None:
        """
        Set the LLM response.
        
        Args:
            response: Response from the LLM
        """
        self._response = response
        self.set_attribute("llm.response", response)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def set_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        """
        Set token usage information.
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
        """
        self._tokens_prompt = prompt_tokens
        self._tokens_completion = completion_tokens
        self._tokens_total = prompt_tokens + completion_tokens
        
        self.set_attribute("llm.tokens.prompt", prompt_tokens)
        self.set_attribute("llm.tokens.completion", completion_tokens)
        self.set_attribute("llm.tokens.total", self._tokens_total)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def set_cost(self, cost: float) -> None:
        """
        Set the cost of the LLM call.
        
        Args:
            cost: Cost in USD
        """
        self._cost = cost
        self.set_attribute("llm.cost", cost)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update({
            "model": self._model,
            "prompt": self._prompt,
            "response": self._response,
            "tokens_prompt": self._tokens_prompt,
            "tokens_completion": self._tokens_completion,
            "tokens_total": self._tokens_total,
            "cost": self._cost,
        })
        return result 