# AgentOps HTTP Client Architecture

This directory contains the HTTP client architecture for the AgentOps SDK. The architecture follows a clean separation of concerns design principle.

## Components

### HttpClient

The `HttpClient` class provides low-level HTTP functionality:
- Connection pooling
- Retry logic
- Basic HTTP methods (GET, POST, PUT, DELETE)

### AuthManager

The `AuthManager` class handles authentication concerns:
- Token acquisition and storage
- Token refresh logic
- Authentication header preparation
- Thread-safe token operations

## Design Principles

1. **Separation of Concerns**
   - HTTP concerns are isolated from authentication concerns
   - Each component has a single responsibility

2. **Composition over Inheritance**
   - Components use composition rather than inheritance
   - `ApiClient` composes `HttpClient` and `AuthManager`

3. **Clear Interfaces**
   - Each component has a well-defined interface
   - Implementation details are hidden

4. **Dependency Flow**
   - Dependencies flow in one direction
   - Lower-level components (HTTP, Auth) don't depend on higher-level components

## Usage

The HTTP client architecture is used by the `ApiClient` class, which provides a high-level interface for making API calls. Specific API versions (like `V3Client`) extend the `ApiClient` to provide version-specific functionality.

```python
# Example usage
from agentops.client.v3_client import V3Client

client = V3Client(endpoint="https://api.agentops.ai")
response = client.authenticated_request(
    method="get",
    path="/v3/some/endpoint",
    api_key="your-api-key"
) 