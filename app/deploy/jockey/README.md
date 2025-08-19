# Jockey - Kubernetes Deployment Tool

Jockey is a Python-based tool for building container images and deploying them to Kubernetes clusters. It uses Kaniko for secure, rootless image building and supports AWS ECR for container registry.

## Prerequisites

- Python virtual environment activated (`source ../api/.venv/bin/activate`)
- Kubeconfig file configured at `./config/kubeconfig`
- AWS credentials secret deployed to Kubernetes
- ECR repository available

## Environment Variables

Configure these in your environment or `.env` file:

```bash
# Kubernetes Configuration
KUBECONFIG=./config/kubeconfig
KUBERNETES_NAMESPACE=default

# Container Registry
IMAGE_REGISTRY=315680545607.dkr.ecr.us-west-1.amazonaws.com
AWS_DEFAULT_REGION=us-west-1

# AWS Credentials (for kubectl secret)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Setup Commands

### 1. Setup Kubeconfig
```bash
# From the jockey directory
export KUBECONFIG=./config/kubeconfig
python -m jockey setup-kubeconfig
```

### 2. Setup Builder Namespace and AWS Credentials
```bash
# Create builder namespace and AWS credentials secret from local AWS CLI
python -m jockey setup-builder
```

This command will:
- Create a dedicated `builder` namespace for image building operations
- Extract AWS credentials from your local AWS CLI configuration
- Create the `aws-credentials` secret in the builder namespace

**Why this matters**: Builder pods need AWS credentials to push images to ECR, but deployment pods don't need these credentials since they only pull images. By isolating builder operations in their own namespace, we maintain better security separation.

## Testing Commands

All commands should be run from the deploy directory with the virtual environment activated:

```bash
# Activate virtual environment and set kubeconfig
source ../api/.venv/bin/activate
export KUBECONFIG=./config/kubeconfig
```

### Build and Push Image Only
```bash
# Test image building and pushing to ECR
python -m jockey test-build

# The test-build command uses default configured values (hosting/agent-images)
# and doesn't require additional parameters for basic testing
```

### Complete Build and Deploy
```bash
# Build image, push to ECR, and deploy to Kubernetes (uses default namespace)
python -m jockey deploy-test

# Deploy with custom namespace (must exist first!)
python -m jockey deploy-test --namespace test-namespace

# Deploy with custom template
python -m jockey deploy-test --template simple-api
```

### Management Commands
```bash
# List running instances in a specific project namespace
python -m jockey list-instances --namespace PROJECT_ID

# List builder pods
python -m jockey list-instances --namespace builder

# Stop a deployment (note: deployment name comes BEFORE --namespace)
python -m jockey stop-deployment DEPLOYMENT_NAME --namespace PROJECT_ID

# Stop a specific pod
python -m jockey stop-pod pod-name-12345 --namespace PROJECT_ID

# View builder logs across all namespaces
python -m jockey logs-builder -f
```

## CLI Usage Tips

### Command Discovery
```bash
# See all available commands
python -m jockey --help

# Get help for specific commands
python -m jockey deploy-test --help
python -m jockey stop-deployment --help
```

### Common CLI Patterns
1. **Parameter Order**: For commands that take a resource name, the name comes FIRST, then flags:
   ```bash
   # ✅ Correct
   python -m jockey stop-deployment hosting-agent-images --namespace default
   
   # ❌ Wrong
   python -m jockey stop-deployment --namespace default hosting-agent-images
   ```

2. **Namespace Requirements**: Custom namespaces must exist in Kubernetes before use:
   ```bash
   # Create namespace first if needed
   kubectl create namespace test-namespace
   
   # Then deploy to it
   python -m jockey deploy-test --namespace test-namespace
   ```

3. **Deployment Conflicts**: If a deployment already exists, stop it first:
   ```bash
   # Clean up existing deployment
   python -m jockey stop-deployment hosting-agent-images --namespace default
   
   # Then deploy fresh
   python -m jockey deploy-test
   ```

4. **Error Recovery**: If a command fails, check the specific error:
   - `namespaces "X" not found` → Create the namespace first
   - `deployments.apps "X" already exists` → Stop the existing deployment
   - `ModuleNotFoundError` → Check you're in the right directory and venv is activated

### Direct Kubernetes Commands
```bash
# Check deployments
kubectl get deployments --namespace default

# Check pods
kubectl get pods --namespace default -l app=hosting-agent-images

# Check pod logs
kubectl logs pod-name --namespace default

# Describe pod for troubleshooting
kubectl describe pod pod-name --namespace default

# Delete deployment
kubectl delete deployment hosting-agent-images --namespace default
```

## Available Templates

Templates are located in `./templates/docker/`:

- **test**: Simple HTTP server for testing (Alpine + netcat)
- **python-agent**: Python application with AgentStack (incomplete)

## Architecture

### Namespace Strategy

Jockey uses a multi-namespace approach for security and isolation:

#### 1. Builder Namespace (`builder`)
- **Purpose**: Houses all image building operations
- **Contains**: Kaniko builder pods, AWS credentials secret, build-related ConfigMaps
- **Access**: Only builder pods can access AWS credentials for ECR pushing
- **Lifecycle**: Persistent namespace, created during setup

#### 2. Project Namespaces (`project-id`)
- **Purpose**: Isolates individual project deployments
- **Contains**: Application pods, project-specific secrets (AgentOps API keys), services
- **Access**: No AWS credentials needed - only pulls images from ECR
- **Lifecycle**: Created automatically when deploying a project

#### 3. Default Namespace (`default`)
- **Purpose**: Legacy operations and cluster-wide resources
- **Contains**: May contain shared resources for backward compatibility
- **Access**: Limited use in current architecture

### Secret Management

#### Cross-Namespace Secret Limitations
Kubernetes secrets are namespace-scoped and **cannot be referenced across namespaces**. This is a security feature that maintains namespace isolation.

#### Our Secret Strategy
1. **AWS Credentials**: Only stored in `builder` namespace
   - Builder pods authenticate with ECR to push images
   - Deployment pods don't need AWS credentials (ECR pull is cluster-level)

2. **Project Secrets**: Stored in each project namespace
   - AgentOps API keys automatically injected from project configuration
   - Environment-specific secrets isolated per project

3. **Shared Resources**: Must be replicated to each namespace that needs them
   - No cross-namespace secret sharing by design
   - Tools like `kubernetes-reflector` can automate secret replication if needed

### Image Building
- Uses **Kaniko** for secure, rootless container builds in Kubernetes
- Builds run as Kubernetes Jobs in the `builder` namespace
- Images are pushed directly to AWS ECR with AWS credentials from builder namespace
- Built images are referenced by full ECR URL from any namespace

### Deployment
- Creates Kubernetes Deployments in project-specific namespaces
- Pulls images from ECR using cluster-level permissions
- Automatically includes project-specific secrets (AgentOps API keys)
- Supports health checks, environment variables, and volume mounts
- Watches deployment progress with real-time events

### Security
- AWS credentials isolated in builder namespace only
- Project secrets isolated per namespace
- No Docker daemon required (uses Kaniko)
- Namespace-based access control and resource isolation

## Troubleshooting

### Common Issues

1. **Image pull errors**: Check AWS credentials secret exists and is correctly formatted
2. **Build failures**: Verify ECR repository exists and AWS credentials have push permissions
3. **CrashLoopBackOff**: Check container logs and ensure the application runs as a long-lived process
4. **Job name errors**: Kubernetes names can't contain `/` or `:` - they're automatically sanitized

### Debug Commands
```bash
# Check recent builder pods (now in builder namespace)
kubectl get pods --namespace builder | grep builder

# Check builder logs (use logs-builder command for convenience)
python -m jockey logs-builder -f

# Check AWS credentials secret in builder namespace
kubectl get secret aws-credentials --namespace builder -o yaml

# Check project deployment pods
kubectl get pods --namespace PROJECT_ID

# Check project secrets
kubectl get secrets --namespace PROJECT_ID

# Verify ECR repository exists
aws ecr describe-repositories --region us-west-1 --registry-id 315680545607
```

## Development Notes

### TODO Items
- **Missing crash event feedback**: Deploy command doesn't report container crashes (CrashLoopBackOff) - it just times out silently
- **Image pull security**: Consider implementing image pull secrets or IRSA for more secure ECR authentication
- **Layer caching**: Implement persistent layer caching for faster builds

### File Structure
```
jockey/
├── README.md                 # This file
├── __main__.py              # CLI commands
├── api.py                   # Public API
├── environment.py           # Configuration
├── backend/models/
│   ├── image.py            # Image building with Kaniko
│   ├── deployment.py       # Kubernetes deployments
│   └── pod.py             # Pod management
├── templates/docker/       # Dockerfile templates
└── config/
    └── kubeconfig         # Kubernetes config
```

## Example Workflow

Complete end-to-end example:

```bash
# 1. Initial setup (one-time)
source ../api/.venv/bin/activate
export KUBECONFIG=./config/kubeconfig

# Setup kubeconfig
python -m jockey setup-kubeconfig

# Setup builder namespace and AWS credentials
python -m jockey setup-builder

# 2. Build and deploy
python -m jockey deploy-test --name hosting/agent-images --template test

# 3. Verify deployment
kubectl get pods -l app=hosting-agent-images

# 4. Monitor build progress
python -m jockey logs-builder -f

# 5. Cleanup
kubectl delete deployment hosting-agent-images
```

## Worker Deployment

The jockey worker can be deployed as a Docker container to process deployment jobs from a Redis queue.

### Building the Worker Image

```bash
# Build from the jockey directory
cd /path/to/jockey
docker build -f worker/Dockerfile -t jockey-worker .
```

### Running the Worker Container

```bash
# Check worker and queue status
docker run --rm jockey-worker python -m jockey.worker status

# Start the worker (requires Redis connection)
docker run --rm \
  -e DEPLOY_REDIS_HOST=redis.example.com \
  -e DEPLOY_REDIS_PORT=6379 \
  -e DEPLOY_REDIS_DB=0 \
  jockey-worker

# Run with Redis linked container
docker run --rm \
  --link redis:redis \
  -e DEPLOY_REDIS_HOST=redis \
  jockey-worker

# Health check command (used by Docker HEALTHCHECK)
docker run --rm jockey-worker python -m jockey.worker health
```

### Worker Commands

- `python -m jockey.worker start` - Start the deployment worker
- `python -m jockey.worker status` - Show queue status and connection info
- `python -m jockey.worker health` - Health check (exit 0 = healthy, exit 1 = unhealthy)

### Environment Variables

Required for worker operation:

```bash
# Redis Configuration (required)
DEPLOY_REDIS_HOST=localhost          # Redis server hostname
DEPLOY_REDIS_PORT=6379              # Redis server port
DEPLOY_REDIS_DB=0                   # Redis database number

# Worker Configuration (optional)
WORKER_POLL_INTERVAL=5       # Seconds between queue polls

# Kubernetes Configuration (required for deployments)
KUBECONFIG=/path/to/kubeconfig
KUBERNETES_NAMESPACE=default

# AWS Configuration (required for ECR)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-west-1
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  jockey-worker:
    image: jockey-worker
    depends_on:
      - redis
    environment:
      - DEPLOY_REDIS_HOST=redis
      - DEPLOY_REDIS_PORT=6379
      - DEPLOY_REDIS_DB=0
      - WORKER_POLL_INTERVAL=5
    volumes:
      - /path/to/kubeconfig:/app/config/kubeconfig:ro
```