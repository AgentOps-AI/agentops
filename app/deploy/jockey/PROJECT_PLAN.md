# Jockey - Kubernetes Deployment Package

## Project Overview

Jockey is a Python package that implements Kubernetes-based deployment orchestration for AI agents, based on the patterns and features from the AgentStack TypeScript host project. It provides a clean, model-style interface for managing Kubernetes resources and deployment workflows.

## Architecture Goals

The jockey package is designed as a standalone Python library that can be embedded in other applications or used directly for Kubernetes deployment operations. It follows the repository's patterns for environment configuration and provides a clean abstraction over the Kubernetes Python client.

## Core Features to Implement

### 1. Kubernetes Resource Management

**Models to Implement:**
- `Deployment` - Kubernetes deployment management
- `Service` - Service discovery and load balancing  
- `ConfigMap` - Configuration management
- `Secret` - Sensitive data management
- `ResourceQuota` - Resource limit enforcement
- `Pod` - Individual pod management and monitoring

**Key Capabilities:**
- Dynamic deployment creation and updates
- Real-time status monitoring using Kubernetes Watch API
- Resource constraint management (CPU/Memory limits)
- Automatic rollback on deployment failures
- Pod lifecycle management and health checks

### 2. Docker Integration

**Components:**
- `DockerBuilder` - Docker image building and management
- `Registry` - Docker registry operations (push/pull)
- `ImageManager` - Version control and cleanup

**Features:**
- Dynamic Dockerfile generation from project templates
- Build progress streaming and logging
- Registry authentication and image pushing
- Image versioning and tag management
- Build artifact cleanup

### 3. Deployment Pipeline

**Pipeline Stages:**
1. **Upload/Extract** - Project code processing
2. **Build** - Docker image creation
3. **Deploy** - Kubernetes deployment
4. **Monitor** - Real-time status tracking
5. **Cleanup** - Resource management

**Data Structures:**
```python
@dataclass
class DeploymentConfig:
    project_id: str
    image_tag: str
    replicas: int = 1
    cpu_request: str = "100m"
    cpu_limit: str = "500m"
    memory_request: str = "128Mi"
    memory_limit: str = "256Mi"
    environment_vars: Dict[str, str] = field(default_factory=dict)
    
@dataclass
class BuildContext:
    project_path: str
    dockerfile_content: str
    image_name: str
    build_logs: List[str] = field(default_factory=list)
    
@dataclass
class DeploymentStatus:
    name: str
    status: Literal["pending", "building", "deploying", "running", "failed"]
    replicas_ready: int
    replicas_desired: int
    created_at: datetime
    last_updated: datetime
    error_message: Optional[str] = None
```

### 4. Multi-tenancy and Isolation

**Namespace Management:**
- Organization-based namespace isolation
- Project-specific resource labeling
- RBAC integration for access control
- Resource quota enforcement per namespace

**Security Features:**
- Secret management for registry credentials
- ConfigMap isolation between projects
- Network policies for pod isolation
- Service account management

### 5. Monitoring and Observability

**Metrics Collection:**
- Deployment status tracking
- Resource utilization monitoring
- Build time and success rate metrics
- Pod restart and failure tracking

**Logging Integration:**
- Structured logging with correlation IDs
- Build log streaming
- Pod log aggregation
- Error tracking and alerting

### 6. Real-time Communication

**WebSocket Support:**
- Build progress streaming
- Deployment status updates
- Pod log streaming
- Resource metric updates

**Event System:**
- Kubernetes watch event processing
- Custom event publishing
- Webhook integration for external notifications

## Implementation Plan

### Phase 1: Core Kubernetes Models (Completed)
- ✅ BaseModel with shared client access
- ✅ Deployment model with CRUD operations
- ✅ Environment configuration
- ✅ Client wrapper with proper typing

### Phase 2: Extended Resource Models
- `Service` model for load balancing
- `ConfigMap` model for configuration
- `Secret` model for sensitive data
- `Pod` model for individual pod management
- `ResourceQuota` model for limits

### Phase 3: Docker Integration
- `DockerBuilder` for image creation
- `Registry` client for push/pull operations
- Build context management
- Progress streaming utilities

### Phase 4: Deployment Pipeline
- `DeploymentPipeline` orchestrator
- Build and deploy workflow
- Status monitoring and reporting
- Error handling and rollback

### Phase 5: Advanced Features
- Multi-tenant namespace management
- Real-time event streaming
- Metrics collection and reporting
- Integration with external services

## Data Structures from Host Project

### Project Configuration
```python
@dataclass
class ProjectConfig:
    id: str
    name: str
    organization_id: str
    environment: str = "production"
    region: str = "us-east-1"
    framework: str = "agentstack"
    python_version: str = "3.12"
```

### Resource Specifications
```python
@dataclass
class ResourceSpec:
    cpu_request: str = "100m"
    cpu_limit: str = "500m"
    memory_request: str = "128Mi"
    memory_limit: str = "256Mi"
    storage_request: str = "1Gi"
    storage_limit: str = "10Gi"
```

### Deployment Metadata
```python
@dataclass
class DeploymentMetadata:
    project_id: str
    version: str
    deployed_at: datetime
    deployed_by: str
    build_hash: str
    environment_vars: Dict[str, str]
    labels: Dict[str, str]
```

## Kubernetes Concepts Integration

### 1. Deployment Patterns
- **Rolling Updates**: Zero-downtime deployments with configurable rollout strategy
- **Blue/Green**: Environment switching for testing and validation
- **Canary**: Gradual traffic shifting for risk mitigation
- **Resource Quotas**: CPU/Memory constraints per deployment

### 2. Service Discovery
- **ClusterIP**: Internal service communication
- **LoadBalancer**: External traffic distribution
- **Ingress**: HTTP/HTTPS routing and TLS termination
- **DNS**: Service name resolution

### 3. Configuration Management
- **ConfigMaps**: Non-sensitive configuration data
- **Secrets**: Sensitive data (API keys, passwords)
- **Environment Variables**: Runtime configuration
- **Volume Mounts**: File-based configuration

### 4. Observability
- **Pod Logs**: Application output streaming
- **Metrics**: Resource utilization tracking
- **Health Checks**: Liveness and readiness probes
- **Events**: Kubernetes system events

## Environment Configuration

Following the repository pattern, jockey uses top-level environment constants:

```python
# Kubernetes configuration
KUBERNETES_NAMESPACE = os.getenv("KUBERNETES_NAMESPACE", "default")
KUBECONFIG_PATH = os.getenv("KUBECONFIG")
KUBERNETES_CONTEXT = os.getenv("KUBERNETES_CONTEXT")

# Docker registry
DOCKER_REGISTRY = os.getenv("DOCKER_REGISTRY", "docker.io")
DOCKER_USERNAME = os.getenv("DOCKER_USERNAME")
DOCKER_PASSWORD = os.getenv("DOCKER_PASSWORD")

# Resource limits
DEFAULT_CPU_REQUEST = os.getenv("DEFAULT_CPU_REQUEST", "100m")
DEFAULT_CPU_LIMIT = os.getenv("DEFAULT_CPU_LIMIT", "500m")
DEFAULT_MEMORY_REQUEST = os.getenv("DEFAULT_MEMORY_REQUEST", "128Mi")
DEFAULT_MEMORY_LIMIT = os.getenv("DEFAULT_MEMORY_LIMIT", "256Mi")

# Build configuration
BUILD_TIMEOUT = int(os.getenv("BUILD_TIMEOUT", "900"))  # 15 minutes
MAX_BUILD_LOG_SIZE = int(os.getenv("MAX_BUILD_LOG_SIZE", "10485760"))  # 10MB
```

## Usage Examples

### Basic Deployment
```python
from jockey.models import Deployment
from jockey.pipeline import DeploymentPipeline

# Create deployment
deployment = Deployment.create(
    name="my-agent",
    image="myregistry/agent:v1.0.0",
    replicas=3
)

# Monitor status
status = deployment.get_status()
print(f"Ready replicas: {status.replicas_ready}/{status.replicas_desired}")
```

### Full Pipeline
```python
from jockey.pipeline import DeploymentPipeline
from jockey.models import DeploymentConfig

config = DeploymentConfig(
    project_id="my-project",
    image_tag="v1.2.0",
    replicas=2,
    environment_vars={"API_KEY": "secret-value"}
)

pipeline = DeploymentPipeline(config)
result = await pipeline.execute()
```

This project plan provides a comprehensive roadmap for implementing the jockey package with all the features and patterns identified from the host TypeScript project, adapted for Python and following the repository's established conventions.