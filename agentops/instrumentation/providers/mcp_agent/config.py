"""Configuration for MCP Agent instrumentation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration for MCP Agent instrumentation.
    
    This configuration controls how AgentOps instruments MCP Agent,
    including what data to capture and how to integrate with its
    existing telemetry system.
    """
    
    # Data capture settings
    capture_prompts: bool = True
    """Whether to capture prompts sent to agents."""
    
    capture_completions: bool = True
    """Whether to capture agent completions/responses."""
    
    capture_errors: bool = True
    """Whether to capture and report errors."""
    
    capture_tool_calls: bool = True
    """Whether to capture MCP tool calls and their results."""
    
    capture_workflows: bool = True
    """Whether to capture workflow execution details."""
    
    # Integration settings
    integrate_with_existing_telemetry: bool = True
    """Whether to integrate with MCP Agent's existing OpenTelemetry setup."""
    
    override_tracer_config: bool = False
    """Whether to override MCP Agent's tracer configuration."""
    
    # Performance settings
    max_prompt_length: Optional[int] = 10000
    """Maximum length of prompts to capture (None for unlimited)."""
    
    max_completion_length: Optional[int] = 10000
    """Maximum length of completions to capture (None for unlimited)."""
    
    # Filtering settings
    excluded_tools: Optional[list[str]] = None
    """List of tool names to exclude from instrumentation."""
    
    excluded_workflows: Optional[list[str]] = None
    """List of workflow names to exclude from instrumentation."""
    
    def should_capture_tool(self, tool_name: str) -> bool:
        """Check if a tool should be captured."""
        if not self.capture_tool_calls:
            return False
        if self.excluded_tools and tool_name in self.excluded_tools:
            return False
        return True
    
    def should_capture_workflow(self, workflow_name: str) -> bool:
        """Check if a workflow should be captured."""
        if not self.capture_workflows:
            return False
        if self.excluded_workflows and workflow_name in self.excluded_workflows:
            return False
        return True
    
    def truncate_prompt(self, prompt: str) -> str:
        """Truncate prompt if needed."""
        if self.max_prompt_length and len(prompt) > self.max_prompt_length:
            return prompt[:self.max_prompt_length] + "... [truncated]"
        return prompt
    
    def truncate_completion(self, completion: str) -> str:
        """Truncate completion if needed."""
        if self.max_completion_length and len(completion) > self.max_completion_length:
            return completion[:self.max_completion_length] + "... [truncated]"
        return completion