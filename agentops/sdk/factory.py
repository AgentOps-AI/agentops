from __future__ import annotations

from typing import Any, Dict, Optional, Type, Union, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Span

from agentops.sdk.spanned import SpannedBase

# Type variable for span types
T = TypeVar('T', bound=SpannedBase)

class SpanFactory:
    """
    Factory for creating different types of spans.
    
    This class handles the creation of spans with the appropriate context and attributes.
    """
    
    _span_types: Dict[str, Type[SpannedBase]] = {}
    
    @classmethod
    def register_span_type(cls, kind: str, span_class: Type[SpannedBase]) -> None:
        """
        Register a span type with the factory.
        
        Args:
            kind: Kind of span (e.g., "session", "agent", "tool")
            span_class: Class to use for creating spans of this kind
        """
        cls._span_types[kind] = span_class
    
    @classmethod
    def auto_register_span_types(cls) -> None:
        """
        Automatically register all standard span types.
        
        This method should be called once during initialization to ensure
        that all standard span types are registered with the factory.
        """
        # Import here to avoid circular imports
        from agentops.sdk.spans import SessionSpan, AgentSpan, ToolSpan, CustomSpan
        
        # Register standard span types
        cls.register_span_type("session", SessionSpan)
        cls.register_span_type("agent", AgentSpan)
        cls.register_span_type("tool", ToolSpan)
        cls.register_span_type("custom", CustomSpan)
    
    @classmethod
    def create_span(
        cls,
        kind: str,
        name: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
        immediate_export: bool = False,
        **kwargs
    ) -> SpannedBase:
        """
        Create a span of the specified kind.
        
        Args:
            kind: Kind of span (e.g., "session", "agent", "tool")
            name: Name of the span
            parent: Optional parent span or spanned object
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new span of the specified kind
        
        Raises:
            ValueError: If the specified kind is not registered
        """
        # Get the span class for this kind
        span_class = cls._span_types.get(kind)
        if span_class is None:
            raise ValueError(f"Unknown span kind: {kind}")
        
        # Create the span
        span = span_class(
            name=name,
            kind=kind,
            parent=parent,
            attributes=attributes or {},
            immediate_export=immediate_export,
            **kwargs
        )
        
        # Start the span if requested
        if auto_start:
            span.start()
        
        return span
    
    @classmethod
    def create_session_span(
        cls,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
        immediate_export: bool = True,  # Sessions are typically exported immediately
        **kwargs
    ) -> SpannedBase:
        """
        Create a session span.
        
        Args:
            name: Name of the span
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new session span
        """
        return cls.create_span(
            kind="session",
            name=name,
            parent=None,  # Sessions are always root spans
            attributes=attributes,
            auto_start=auto_start,
            immediate_export=immediate_export,
            **kwargs
        )
    
    @classmethod
    def create_agent_span(
        cls,
        name: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
        immediate_export: bool = True,  # Agents are typically exported immediately
        **kwargs
    ) -> SpannedBase:
        """
        Create an agent span.
        
        Args:
            name: Name of the span
            parent: Optional parent span or spanned object
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new agent span
        """
        return cls.create_span(
            kind="agent",
            name=name,
            parent=parent,
            attributes=attributes,
            auto_start=auto_start,
            immediate_export=immediate_export,
            **kwargs
        )
    
    @classmethod
    def create_tool_span(
        cls,
        name: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
        immediate_export: bool = False,  # Tools are typically short-lived
        **kwargs
    ) -> SpannedBase:
        """
        Create a tool span.
        
        Args:
            name: Name of the span
            parent: Optional parent span or spanned object
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new tool span
        """
        return cls.create_span(
            kind="tool",
            name=name,
            parent=parent,
            attributes=attributes,
            auto_start=auto_start,
            immediate_export=immediate_export,
            **kwargs
        )
    
    @classmethod
    def create_llm_span(
        cls,
        name: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
        immediate_export: bool = True,  # LLM calls are typically long-running
        **kwargs
    ) -> SpannedBase:
        """
        Create an LLM span.
        
        Args:
            name: Name of the span
            parent: Optional parent span or spanned object
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new LLM span
        """
        return cls.create_span(
            kind="llm",
            name=name,
            parent=parent,
            attributes=attributes,
            auto_start=auto_start,
            immediate_export=immediate_export,
            **kwargs
        )
    
    @classmethod
    def create_custom_span(
        cls,
        kind: str,
        name: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        auto_start: bool = True,
        immediate_export: bool = False,
        **kwargs
    ) -> SpannedBase:
        """
        Create a custom span.
        
        Args:
            kind: Custom kind of span
            name: Name of the span
            parent: Optional parent span or spanned object
            attributes: Optional attributes to set on the span
            auto_start: Whether to automatically start the span
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments to pass to the span constructor
        
        Returns:
            A new custom span
        """
        return cls.create_span(
            kind=kind,
            name=name,
            parent=parent,
            attributes=attributes,
            auto_start=auto_start,
            immediate_export=immediate_export,
            **kwargs
        ) 