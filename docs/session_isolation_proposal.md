# Session Configuration Isolation Proposal

## Problem Statement

Currently, the AgentOps SDK uses a singleton `TracingCore` that gets initialized with a single global configuration. This architecture doesn't support per-session configuration isolation, which is a requirement for allowing different sessions to have different tracing configurations.

## Current Architecture Limitations

1. `TracingCore` is a singleton with a single configuration
2. The `SessionSpan` initializes the core with its config, but this affects all sessions
3. There's no way to have different sessions use different exporters, processors, or other configuration parameters
4. All spans share the same tracer provider, regardless of which session they belong to

## Proposed Solution

We need to modify the architecture to support session-specific tracing contexts while maintaining the hierarchical relationship between spans. This will allow each session to have its own isolated configuration without affecting other sessions.

### Key Components to Modify

1. **TracingCore**: Add support for session-specific tracer providers
2. **SessionSpan**: Update to create and use session-specific providers
3. **SpanFactory**: Update to accept and use session-specific tracers
4. **SpannedBase**: Update to store and use session IDs and tracers
5. **Decorators**: Update to propagate session IDs to child spans

## Resource-Efficient Implementation Approach

After careful consideration of real-world use cases, creating a new TracerProvider for every session would be excessive in many scenarios, especially in high-traffic applications like FastAPI services that handle many concurrent requests.

### When Separate TracerProviders Are Needed

Separate TracerProviders are only necessary when:
1. Sessions need to export to completely different destinations
2. Sessions need fundamentally different processor configurations 
3. Sessions require different sampling rates or other core TraceProvider settings

### Resource-Efficient Alternative

For most use cases, we can achieve session isolation with a more efficient approach:

1. **Shared TracerProvider with Context Propagation**: Use a single TracerProvider by default, and rely on context propagation and session-specific span attributes to maintain isolation.

2. **Lazy Creation of TracerProviders**: Only create a separate TracerProvider when a session's configuration is significantly different from the default.

3. **Configuration Registry**: Maintain a small registry of TracerProviders based on unique configurations, not sessions. Multiple sessions with the same configuration can share a TracerProvider.

```python
class TracingCore:
    # Instead of one provider per session, maintain a registry of providers by config hash
    _provider_registry = {}  
    
    def get_or_create_provider(self, config: Config) -> Tuple[str, TracerProvider]:
        """Get an existing provider for this config or create a new one."""
        # Create a hash of the relevant config properties
        config_hash = hash_config(config)
        
        with self._lock:
            if config_hash in self._provider_registry:
                return config_hash, self._provider_registry[config_hash]["provider"]
            
            # Only create a new provider if needed
            provider = TracerProvider(...)
            self._provider_registry[config_hash] = {
                "provider": provider,
                "processors": [],
                "config": config,
                "reference_count": 0  # Track how many sessions use this provider
            }
            
            return config_hash, provider
            
    def get_tracer_for_session(self, session_id: str) -> trace.Tracer:
        """Get the appropriate tracer for a session."""
        # Look up the config for this session
        session_config = self._session_configs.get(session_id)
        if not session_config:
            # No specific config for this session, use default
            return self._default_provider.get_tracer("agentops")
            
        # Get the provider for this config
        config_hash = self._session_provider_map.get(session_id)
        if config_hash in self._provider_registry:
            return self._provider_registry[config_hash]["provider"].get_tracer("agentops")
            
        # Fallback to default
        return self._default_provider.get_tracer("agentops")
```

### FastAPI Use Case Optimization

For the FastAPI use case, sessions (requests) would typically:

1. Share the same basic export configuration
2. Need isolation for context propagation and span relationships
3. Need unique session IDs to differentiate between requests

In this scenario, we would:

1. Use a single TracerProvider for all requests by default
2. Create session-specific spans with the request's session ID as an attribute
3. Use context propagation to maintain the parent-child relationship within each request
4. Only create a new TracerProvider if a specific request needs a different export destination

This approach provides the necessary isolation while being much more resource-efficient for high-traffic applications.

### Detailed Implementation Plan

#### 1. TracingCore Modifications

```python
class TracingCore:
    """
    Central component for tracing in AgentOps.
    
    This class manages the creation, processing, and export of spans.
    It handles provider management, span creation, and context propagation.
    """
    
    _instance: Optional[TracingCore] = None
    _lock = threading.Lock()
    _provider_registry = {}  # Store providers by config hash
    _session_configs = {}  # Store configs by session ID
    _session_provider_map = {}  # Map session IDs to provider config hashes
    
    # ... existing code ...
    
    def register_session_config(self, session_id: str, config: Config) -> str:
        """
        Register a configuration for a session and get or create an appropriate provider.
        
        Args:
            session_id: Unique identifier for the session
            config: Configuration for the session
            
        Returns:
            The config hash for the provider
        """
        with self._lock:
            # Store the config for this session
            self._session_configs[session_id] = config
            
            # Only create a new provider if this config is significantly different
            if self._needs_separate_provider(config):
                # Get or create a provider for this config
                config_hash, _ = self._get_or_create_provider(config)
                
                # Map this session to the provider config
                self._session_provider_map[session_id] = config_hash
                
                # Increment reference count
                self._provider_registry[config_hash]["reference_count"] += 1
                
                return config_hash
            
            # Use the default provider
            return "default"
    
    def _needs_separate_provider(self, config: Config) -> bool:
        """
        Determine if a configuration needs a separate provider from the default.
        
        Args:
            config: Configuration to check
            
        Returns:
            True if a separate provider is needed, False otherwise
        """
        # Check if the exporter endpoint is different
        if config.exporter_endpoint and config.exporter_endpoint != self._default_config.exporter_endpoint:
            return True
            
        # Check if a custom exporter or processor is specified
        if config.exporter is not None or config.processor is not None:
            return True
            
        # Other criteria could be added here
        
        return False
    
    def _get_or_create_provider(self, config: Config) -> Tuple[str, TracerProvider]:
        """
        Get an existing provider for this config or create a new one.
        
        Args:
            config: Configuration to get or create a provider for
            
        Returns:
            A tuple of (config_hash, provider)
        """
        # Create a hash of the relevant config properties
        config_hash = self._hash_config(config)
        
        # Check if we already have a provider for this config
        if config_hash in self._provider_registry:
            return config_hash, self._provider_registry[config_hash]["provider"]
        
        # Create a new provider for this config
        provider = TracerProvider(
            resource=Resource({SERVICE_NAME: "agentops"})
        )
        
        processors = []
        
        # Configure the provider based on the config
        # ... same as before ...
        
        # Store the provider in the registry
        self._provider_registry[config_hash] = {
            "provider": provider,
            "processors": processors,
            "config": config,
            "reference_count": 0
        }
        
        return config_hash, provider
    
    def _hash_config(self, config: Config) -> str:
        """
        Create a hash of the relevant configuration properties.
        
        Args:
            config: Configuration to hash
            
        Returns:
            A string hash of the configuration
        """
        # Only include properties that affect the provider creation
        hash_source = {
            "exporter_endpoint": config.exporter_endpoint,
            "has_custom_exporter": config.exporter is not None,
            "has_custom_processor": config.processor is not None,
            "max_queue_size": config.max_queue_size,
            "max_wait_time": config.max_wait_time
        }
        
        # Create a hash of the properties
        return hashlib.md5(json.dumps(hash_source, sort_keys=True).encode()).hexdigest()
    
    def get_tracer(self, name: str = "agentops", session_id: Optional[str] = None) -> trace.Tracer:
        """
        Get a tracer with the given name.
        
        Args:
            name: Name of the tracer
            session_id: Optional session ID to get a session-specific tracer
        
        Returns:
            A tracer with the given name
        """
        if not self._initialized:
            raise RuntimeError("Tracing core not initialized")
        
        if session_id and session_id in self._session_provider_map:
            # Get the provider for this session's configuration
            config_hash = self._session_provider_map[session_id]
            if config_hash in self._provider_registry:
                return self._provider_registry[config_hash]["provider"].get_tracer(name)
        
        # Use the default provider
        return self._default_provider.get_tracer(name)
    
    def unregister_session(self, session_id: str) -> None:
        """
        Unregister a session and decrement reference counts for its provider.
        
        Args:
            session_id: Unique identifier for the session
        """
        with self._lock:
            # Check if this session has a custom provider
            if session_id in self._session_provider_map:
                config_hash = self._session_provider_map[session_id]
                
                # Decrement reference count
                if config_hash in self._provider_registry:
                    self._provider_registry[config_hash]["reference_count"] -= 1
                    
                    # Clean up if no more references
                    if self._provider_registry[config_hash]["reference_count"] <= 0:
                        self._cleanup_provider(config_hash)
                
                # Remove session mapping
                del self._session_provider_map[session_id]
            
            # Remove session config
            if session_id in self._session_configs:
                del self._session_configs[session_id]
    
    def _cleanup_provider(self, config_hash: str) -> None:
        """
        Clean up a provider and its resources.
        
        Args:
            config_hash: Hash of the provider configuration
        """
        if config_hash not in self._provider_registry:
            return
            
        provider_data = self._provider_registry[config_hash]
        
        # Flush processors
        for processor in provider_data["processors"]:
            try:
                processor.force_flush()
            except Exception as e:
                logger.warning(f"Error flushing processor for provider {config_hash}: {e}")
        
        # Shutdown provider
        try:
            provider_data["provider"].shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down provider {config_hash}: {e}")
        
        # Remove from registry
        del self._provider_registry[config_hash]
    
    def shutdown(self) -> None:
        """Shutdown the tracing core and all providers."""
        if not self._initialized:
            return
        
        with self._lock:
            if not self._initialized:
                return
            
            # Flush default processors
            for processor in self._default_processors:
                try:
                    processor.force_flush()
                except Exception as e:
                    logger.warning(f"Error flushing default processor: {e}")
            
            # Shutdown default provider
            if self._default_provider:
                try:
                    self._default_provider.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down default provider: {e}")
            
            # Shutdown all registered providers
            for config_hash in list(self._provider_registry.keys()):
                self._cleanup_provider(config_hash)
            
            # Clear session mappings
            self._session_configs.clear()
            self._session_provider_map.clear()
            
            self._initialized = False
            logger.debug("Tracing core shutdown")
```

#### 2. SessionSpan Modifications

```python
def __init__(
    self,
    name: str,
    config: Config,
    tags: Optional[List[str]] = None,
    host_env: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Initialize a session span.
    
    Args:
        name: Name of the session
        config: Configuration for the session
        tags: Optional tags for the session
        host_env: Optional host environment information
        **kwargs: Additional keyword arguments
    """
    # Initialize tracing core with config
    core = TracingCore.get_instance()
    core.initialize(config)
    
    # Generate a session ID
    self._session_id = str(uuid4())
    
    # Register this session's configuration
    core.register_session_config(self._session_id, config)
    
    # Set default values
    kwargs.setdefault("kind", "session")
    kwargs.setdefault("session_id", self._session_id)
    
    # Initialize base class
    super().__init__(name=name, parent=None, **kwargs)
    
    # Store session-specific attributes
    self._config = config
    self._tags = tags or []
    self._host_env = host_env or {}
    self._state = "INITIALIZING"
    self._state_reason = None
    
    # Set attributes on span when started
    self._attributes.update({
        "session.name": name,
        "session.tags": self._tags,
        "session.state": self._state,
        "session.id": self._session_id,
    })
    
    # Add host environment as attributes
    if self._host_env:
        for key, value in self._host_env.items():
            self._attributes[f"host.{key}"] = value
    
    # Register this session with the context
    SessionContext.set_current_session_id(self._session_id)

def __exit__(self, exc_type, exc_val, exc_tb):
    # Call parent implementation first
    super().__exit__(exc_type, exc_val, exc_tb)
    
    # Unregister this session
    core = TracingCore.get_instance()
    core.unregister_session(self._session_id)
    
    # Clear session from context
    SessionContext.set_current_session_id(None)
```

## Phased Implementation Plan

To implement this architecture, we'll take a phased approach:

### Phase 1: Core Session Context Infrastructure

1. **Create SessionContext Class**
```python
class SessionContext:
    _thread_local = threading.local()
    
    @classmethod
    def get_current_session_id(cls) -> Optional[str]:
        """Get the current session ID from thread-local storage."""
        return getattr(cls._thread_local, "current_session_id", None)
    
    @classmethod
    def set_current_session_id(cls, session_id: Optional[str]) -> None:
        """Set the current session ID in thread-local storage."""
        cls._thread_local.current_session_id = session_id
```

2. **Add Session Configuration Management to TracingCore**
```python
# Add session configuration tracking
_session_configs = {}
_session_provider_map = {}
_provider_registry = {}

def register_session_config(self, session_id: str, config: Config) -> str:
    """Register a configuration for a session."""
    # Implementation as shown above
```

### Phase 2: Provider Registry and Management

3. **Implement Provider Registry and Resource Sharing**
```python
def _get_or_create_provider(self, config: Config) -> Tuple[str, TracerProvider]:
    """Get or create a provider based on configuration."""
    # Implementation as shown above
```

4. **Add Session-Aware Tracer Retrieval**
```python
def get_tracer(self, name: str = "agentops", session_id: Optional[str] = None) -> trace.Tracer:
    """Get the appropriate tracer for a session."""
    # Implementation as shown above
```

### Phase 3: SessionSpan and Context Propagation

5. **Update SessionSpan to Register with Context**
```python
def __init__(self, name: str, config: Config, ...):
    # Generate unique session ID
    self._session_id = str(uuid4())
    
    # Register with context
    SessionContext.set_current_session_id(self._session_id)
    
    # Register configuration
    core.register_session_config(self._session_id, config)
    
    # Rest of initialization
```

6. **Update SpannedBase to Track Session ID**
```python
def __init__(self, name: str, kind: str, ..., session_id: Optional[str] = None, **kwargs):
    # Store session ID from context if not provided
    self._session_id = session_id or SessionContext.get_current_session_id()
    
    # Add session ID to attributes
    if self._session_id:
        self._attributes['session.id'] = self._session_id
```

### Phase 4: Resource Cleanup and Session Management

7. **Add Session Lifecycle Management**
```python
def unregister_session(self, session_id: str) -> None:
    """Unregister a session and manage provider reference counts."""
    # Implementation as shown above
```

8. **Implement Resource Cleanup**
```python
def _cleanup_provider(self, config_hash: str) -> None:
    """Clean up provider resources when no longer needed."""
    # Implementation as shown above
```

### Phase 5: Decorator Updates

9. **Update Decorators to Propagate Session Context**
```python
# Ensure session ID is propagated
agent_span = core.create_span(
    kind="agent",
    name=span_name,
    parent=session.span,
    # Let the session ID come from context if available
    # No need to explicitly pass session_id in most cases
)
```

## Implementation Strategy

1. **Build core session context infrastructure** (SessionContext, configuration tracking)
2. **Implement provider registry with reference counting** for efficient resource management
3. **Update session span and context propagation** for automatic session tracking
4. **Add resource cleanup** for proper session teardown
5. **Update decorators** to work with the context-based approach
6. **Create comprehensive tests** focusing on resource efficiency and isolation

## Testing Strategy

1. **Unit Tests**:
   - Test session context propagation
   - Test configuration-based provider sharing
   - Test reference counting and resource cleanup
   - Test span attribute propagation

2. **Integration Tests**:
   - Test concurrent sessions with shared and distinct configurations
   - Test that spans are properly associated with their sessions
   - Test that configuration differences are respected appropriately

3. **Performance Tests**:
   - Benchmark overhead of context propagation
   - Compare resource usage with many concurrent sessions
   - Verify provider sharing works efficiently at scale

4. **Multi-threading Tests**:
   - Test session isolation in multi-threaded environments
   - Test context propagation across threads
   - Test resource cleanup with concurrent sessions

## Migration Plan

1. Implement the changes in a new branch
2. Add tests to verify the functionality
3. Update documentation to reflect the new capabilities
4. Release a new version with the changes
5. Communicate the changes to users

## Future Enhancements

1. **Session Context Manager**: Provide a context manager for sessions to make it easier to create and manage sessions
2. **Session Registry**: Add a registry to keep track of active sessions and their configurations
3. **Session Configuration API**: Provide an API to update session configurations at runtime
4. **Session Metrics**: Add metrics to track session-specific information (e.g., number of spans, export latency)
5. **Dynamic Configuration**: Allow changing certain configuration parameters at runtime

## Conclusion

This proposal outlines a resource-efficient approach to implementing session-specific configuration isolation in the AgentOps SDK. By sharing TracerProviders when appropriate and only creating new ones when necessary, we can achieve the isolation we need while being mindful of resource usage in high-throughput applications like FastAPI services.

The implementation will focus on context propagation and session ID tracking for most cases, with the ability to use separate providers when truly different configurations are needed. This approach aligns well with OpenTelemetry best practices while meeting our requirements for session isolation.