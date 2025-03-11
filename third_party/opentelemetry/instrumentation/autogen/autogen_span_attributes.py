from opentelemetry.trace import Span
from typing import Any, Dict, List, Optional, Sequence, Union

# Define semantic conventions for AutoGen spans
class AutoGenSpanAttributes:
    """Class to set span attributes for AutoGen components."""

    def __init__(self, span: Span, instance) -> None:
        """Initialize with a span and an AutoGen instance."""
        self.span = span
        self.instance = instance
        self.autogen_data = {
            "agents": [],
            "tools": [],
            "messages": [],
            "llm_config": {}
        }
        self.process_instance()

    def process_instance(self):
        """Process the instance based on its type."""
        instance_type = self.instance.__class__.__name__
        method_mapping = {
            "AssistantAgent": self._process_assistant_agent,
            "UserProxyAgent": self._process_user_proxy_agent,
            "GroupChat": self._process_group_chat,
            "GroupChatManager": self._process_group_chat_manager,
        }
        method = method_mapping.get(instance_type)
        if method:
            method()

    def _process_assistant_agent(self):
        """Process an AssistantAgent instance."""
        self._set_attribute("agent.type", "assistant")
        self._set_attribute("agent.name", getattr(self.instance, "name", "unknown"))
        
        # Extract LLM config if available
        llm_config = getattr(self.instance, "llm_config", {})
        if llm_config:
            self._set_attribute("agent.llm_config.model", llm_config.get("model", "unknown"))
            self._set_attribute("agent.llm_config.temperature", llm_config.get("temperature", 0.7))
            
        # Extract system message if available
        system_message = getattr(self.instance, "system_message", "")
        if system_message:
            self._set_attribute("agent.system_message", system_message)
            
        # Extract tools if available
        tools = []
        if hasattr(self.instance, "function_map"):
            tools = list(getattr(self.instance, "function_map", {}).keys())
            self._set_attribute("agent.tools", tools)

    def _process_user_proxy_agent(self):
        """Process a UserProxyAgent instance."""
        self._set_attribute("agent.type", "user_proxy")
        self._set_attribute("agent.name", getattr(self.instance, "name", "unknown"))
        
        # Extract code execution config if available
        code_execution_config = getattr(self.instance, "code_execution_config", {})
        if code_execution_config:
            self._set_attribute("agent.code_execution.use_docker", 
                               code_execution_config.get("use_docker", False))
            self._set_attribute("agent.code_execution.work_dir", 
                               code_execution_config.get("work_dir", ""))

    def _process_group_chat(self):
        """Process a GroupChat instance."""
        self._set_attribute("team.type", "group_chat")
        
        # Extract agents if available
        agents = getattr(self.instance, "agents", [])
        agent_names = [getattr(agent, "name", "unknown") for agent in agents]
        self._set_attribute("team.agents", agent_names)
        
        # Extract speaker selection method if available
        selection_method = getattr(self.instance, "speaker_selection_method", "")
        if selection_method:
            self._set_attribute("team.speaker_selection_method", selection_method)

    def _process_group_chat_manager(self):
        """Process a GroupChatManager instance."""
        self._set_attribute("team.type", "group_chat_manager")
        self._set_attribute("team.name", getattr(self.instance, "name", "unknown"))
        
        # Extract group chat if available
        group_chat = getattr(self.instance, "groupchat", None)
        if group_chat:
            self._process_group_chat_from_manager(group_chat)

    def _process_group_chat_from_manager(self, group_chat):
        """Process a GroupChat instance from a manager."""
        agents = getattr(group_chat, "agents", [])
        agent_names = [getattr(agent, "name", "unknown") for agent in agents]
        self._set_attribute("team.agents", agent_names)
        
        selection_method = getattr(group_chat, "speaker_selection_method", "")
        if selection_method:
            self._set_attribute("team.speaker_selection_method", selection_method)

    def _set_attribute(self, key, value):
        """Set an attribute on the span if the value is not None."""
        if value is not None:
            if isinstance(value, (list, dict)):
                # Convert complex types to strings to ensure they can be stored as span attributes
                self.span.set_attribute(key, str(value))
            else:
                self.span.set_attribute(key, value)


def set_span_attribute(span: Span, name, value):
    """Helper function to set a span attribute if the value is not None."""
    if value is not None:
        if isinstance(value, (list, dict)):
            # Convert complex types to strings
            span.set_attribute(name, str(value))
        else:
            span.set_attribute(name, value)


def extract_message_attributes(message):
    """Extract attributes from a message."""
    attributes = {}
    
    # Extract content
    if hasattr(message, "content"):
        content = message.content
        if isinstance(content, str):
            # Truncate long content to avoid excessive span size
            attributes["message.content"] = (
                content[:1000] + "..." if len(content) > 1000 else content
            )
    
    # Extract role
    if hasattr(message, "role"):
        attributes["message.role"] = message.role
    
    # Extract name
    if hasattr(message, "name"):
        attributes["message.name"] = message.name
    
    # Extract tool calls
    if hasattr(message, "tool_calls") and message.tool_calls:
        tool_names = []
        for tool_call in message.tool_calls:
            if hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
                tool_names.append(tool_call.function.name)
        if tool_names:
            attributes["message.tool_calls"] = str(tool_names)
    
    return attributes


def extract_token_usage(response):
    """Extract token usage from a response."""
    usage = {}
    
    if hasattr(response, "usage"):
        response_usage = response.usage
        if hasattr(response_usage, "prompt_tokens"):
            usage["prompt_tokens"] = response_usage.prompt_tokens
        if hasattr(response_usage, "completion_tokens"):
            usage["completion_tokens"] = response_usage.completion_tokens
        if hasattr(response_usage, "total_tokens"):
            usage["total_tokens"] = response_usage.total_tokens
    
    return usage 