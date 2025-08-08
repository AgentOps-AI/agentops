# AgentOps Deployment Infrastructure

Multi-tenant Kubernetes deployment system for CrewAI agents with ALB ingress routing.

## Architecture Overview

- **Kubernetes Cluster**: EKS cluster running agent deployments
- **Application Load Balancer**: Shared ALB with host-based routing for multi-tenant isolation  
- **Instance Files**: ConfigMap-based deployment with content hashing
- **Container Registry**: ECR for storing built agent images
- **Build System**: Kaniko-based image building with S3 cache in dedicated builder namespace

## Load Balancer Setup

The deployment system uses AWS Application Load Balancer (ALB) with the AWS Load Balancer Controller for internet-facing traffic routing.

### Architecture

```
Internet → ALB (host-based routing) → Kubernetes Services → Pods
```

- Each project gets its own hostname: `{project-uuid}.deploy.agentops.ai`
- **Shared ALB**: All deployments use a single ALB instance (`alb-deployments` group) providing one IP address for wildcard DNS routing
- ALB routes traffic based on hostname to the correct service using host-based routing
- Services use `ClusterIP` type (not LoadBalancer) for cost efficiency
- ALB Ingress Controller manages ALB lifecycle automatically
- Deployments are tagged with `deployment` and `hostname` labels for routing

### Prerequisites

1. **EKS Cluster** with appropriate IAM permissions
2. **AWS CLI** configured with ELB permissions
3. **Domain** configured for wildcard DNS (*.deploy.agentops.ai)
4. **Subnets** tagged with `kubernetes.io/role/elb=1` for ALB creation
5. **AWS credentials** available via `aws-credentials` secret in `kube-system` namespace
6. **Builder namespace** configured for image building operations

### Step 1: Install AWS Load Balancer Controller

Install the AWS Load Balancer Controller to manage ALBs:

```bash
# Install cert-manager (required dependency)
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.5.4/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -l app=cert-manager -n cert-manager --timeout=60s

# Install required CRDs for ALB controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/config/crd/bases/elbv2.k8s.aws_targetgroupbindings.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/config/crd/bases/elbv2.k8s.aws_ingressclassparams.yaml

# Copy AWS credentials to kube-system namespace
kubectl get secret aws-credentials -n default -o yaml | sed 's/namespace: default/namespace: kube-system/' | kubectl apply -f -

# Apply the ALB controller and webhook configurations
kubectl apply -f configs/aws-load-balancer-controller.yaml
kubectl apply -f configs/aws-load-balancer-webhook.yaml

# Tag public subnets for ALB creation (replace with your subnet IDs)
aws ec2 create-tags --resources subnet-07bb9663fa1d8f572 subnet-0b0bc494208f4d020 --tags Key=kubernetes.io/role/elb,Value=1
```

### Step 2: Configure Services

Services should use `ClusterIP` type to work with ALB ingress:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: svc-{project-uuid}
spec:
  type: ClusterIP  # Important: NOT LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: {project-uuid}
```

### Step 3: Ingress Configuration

The deployment system automatically creates ingress resources with proper ALB annotations:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ing-{project-uuid}
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/group.name: group-ing-{project-uuid}  # Ensures separate ALB per project
spec:
  rules:
  - host: {project-uuid}.deploy.agentops.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: svc-{project-uuid}
            port:
              number: 80
```

### Key Features

- **Project Isolation**: Each project gets its own ALB group for complete isolation
- **Host-based Routing**: Traffic routed by hostname to correct service
- **SSL Termination**: ALB handles HTTPS with automatic redirects
- **Health Checks**: ALB performs HTTP health checks on `/health` endpoint
- **Cost Effective**: One ALB per project vs individual Classic ELBs

## Instance Files Management

Instance files (server.py, providers/) are managed via Kubernetes ConfigMaps with content hashing.

### How It Works

1. **Content Hashing**: Files are hashed to create unique ConfigMap names
2. **Tar Archive**: All instance files packaged into base64-encoded tar.gz
3. **ConfigMap**: Tar archive stored in ConfigMap with hash-based name
4. **Build Process**: ConfigMap mounted to builder and extracted into image
5. **Immutable Deployments**: Hash changes force new ConfigMap creation

### Benefits

- **No Stale Files**: Hash-based naming prevents stale file reuse
- **Fast Updates**: Only changed files create new ConfigMaps  
- **Version Control**: Each deployment gets exactly the files it was built with
- **No External Dependencies**: No EFS or external storage required

## Deployment Process

The deployment system automatically handles ALB creation:

1. **Service Creation**: Creates ClusterIP service for each deployment
2. **Ingress Creation**: Creates ingress with unique group name for ALB isolation  
3. **ALB Provisioning**: AWS Load Balancer Controller creates dedicated ALB
4. **DNS Configuration**: Update DNS to point hostname to ALB IP addresses

### Verifying ALB Creation

```bash
# Check ALB controller status
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Check ingress status (should show ALB address when ready)
kubectl get ingress

# Check ingress events for troubleshooting
kubectl describe ingress ing-{project-uuid}

# List ALBs via AWS CLI
aws elbv2 describe-load-balancers --query 'LoadBalancers[*].[LoadBalancerName,DNSName,State.Code]' --output table

# Get ALB IP addresses for /etc/hosts
nslookup {alb-dns-name}
```

### Troubleshooting

Common issues and solutions:

- **Subnet discovery failed**: Ensure public subnets are tagged with `kubernetes.io/role/elb=1`
- **No credentials**: Verify `aws-credentials` secret exists in `kube-system` namespace
- **Certificate errors**: Use HTTP-only ingress or configure SSL certificates
- **Permission errors**: Check ALB controller logs and ensure all CRDs are installed

## Environment Configuration

### Builder Namespace

The deployment system uses a dedicated namespace for image building operations to simplify management and logging.

**Environment Variable**: `BUILDER_NAMESPACE` (default: `builder`)

All Kaniko builder jobs run in this namespace, which allows for:
- Centralized builder pod management
- Simplified logging with `jockey logs-builder`
- Cleaner separation between build and deployment concerns
- Easy builder resource monitoring

### Setup Builder Namespace

Use the built-in command to create the builder namespace and AWS credentials:

```bash
# Create builder namespace and AWS credentials secret
jockey setup-builder

# View builder logs (automatically uses builder namespace)
jockey logs-builder

# Or specify a different namespace
jockey logs-builder --namespace custom-builder
```

The builder namespace requires the `aws-credentials` secret to authenticate with ECR for image pushing.

## Shared ALB Management

The deployment system uses a shared ALB (`alb-deployments` group) for all deployments to enable wildcard DNS routing with a single IP address. This allows `*.deploy.agentops.ai` to point to one ALB that handles all subdomain routing. All deployments automatically use the shared ALB configuration.

### ALB Configuration

- **Group Name**: `alb-deployments` (configurable via `ALB_SHARED_GROUP_NAME` environment variable)
- **Host-based Routing**: Each deployment gets its own hostname for traffic routing
- **Tagging**: Each ingress is tagged with `deployment` and `hostname` for identification
- **Health Checks**: Configured to use `/health` endpoint with fast deregistration (30s)

### Management Commands

```bash
# Check the status of the shared ALB
jockey alb-status

# List all ingresses using the shared ALB
jockey list-alb-ingresses --namespace default

# Validate ALB routing for a specific hostname
jockey validate-alb-routing yourdomain.deploy.agentops.ai
```

### Environment Variables

- `ALB_SHARED_GROUP_NAME`: Name of the shared ALB group (default: `alb-deployments`)
- `DEPLOYMENT_DOMAIN`: Base domain for deployments (default: `deploy.agentops.ai`)

The shared ALB is automatically provisioned when the first ingress is created and will handle all subsequent deployments through host-based routing. This provides a single IP address that can be used for wildcard DNS records (`*.deploy.agentops.ai`), simplifying DNS management and enabling seamless subdomain routing.