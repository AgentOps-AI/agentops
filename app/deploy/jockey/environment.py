import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

if os.getenv("LOCAL_DEV"):
    print("Loading environment variables from .env file for local development.")
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")

_kubeconfig_path = os.getenv("KUBECONFIG", "config/kubeconfig")
if _kubeconfig_path and not os.path.isabs(_kubeconfig_path):
    # make kubeconfig path absolute if it's relative
    KUBECONFIG_PATH: str = str(BASE_DIR / _kubeconfig_path)
else:
    KUBECONFIG_PATH = _kubeconfig_path or ""

JOCKEY_PATH = os.getenv("JOCKEY_PATH")

KUBERNETES_INTERNAL_NAMESPACE = os.getenv("KUBERNETES_INTERNAL_NAMESPACE", "agentops-deploy")
KUBERNETES_CONTEXT = os.getenv("KUBERNETES_CONTEXT")
BUILDER_NAMESPACE = os.getenv("BUILDER_NAMESPACE", "builder")

# AWS and EKS configuration
EKS_CLUSTER_NAME = os.getenv("EKS_CLUSTER_NAME")
AWS_REGION = os.getenv("AWS_REGION")
AWS_PROFILE = os.getenv("AWS_PROFILE")

# S3 configuration for build cache
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "agentops-deployment-storage")
S3_BUILD_CACHE_PREFIX = os.getenv("S3_BUILD_CACHE_PREFIX", "build-cache")

# Deployment configuration
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "agentops")
IMAGE_REGISTRY = os.getenv("IMAGE_REGISTRY", "315680545607.dkr.ecr.us-west-1.amazonaws.com")
IMAGE_REPOSITORY = os.getenv("IMAGE_REPOSITORY", "hosting/agent-images")
IMAGE_TAG = os.getenv("IMAGE_TAG", "latest")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-west-1")

# Service configuration
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8000"))
SERVICE_TYPE = os.getenv("SERVICE_TYPE", "ClusterIP")

# Resource limits
CPU_LIMIT = os.getenv("CPU_LIMIT", "1000m")
MEMORY_LIMIT = os.getenv("MEMORY_LIMIT", "1Gi")
CPU_REQUEST = os.getenv("CPU_REQUEST", "100m")
MEMORY_REQUEST = os.getenv("MEMORY_REQUEST", "128Mi")

# Builder-specific resource limits
BUILDER_CPU_LIMIT = os.getenv("BUILDER_CPU_LIMIT", "2000m")
BUILDER_MEMORY_LIMIT = os.getenv("BUILDER_MEMORY_LIMIT", "4Gi")
BUILDER_CPU_REQUEST = os.getenv("BUILDER_CPU_REQUEST", "1000m")
BUILDER_MEMORY_REQUEST = os.getenv("BUILDER_MEMORY_REQUEST", "2Gi")

# Replica configuration
REPLICA_COUNT = int(os.getenv("REPLICA_COUNT", "1"))
MAX_REPLICAS = int(os.getenv("MAX_REPLICAS", "10"))
MIN_REPLICAS = int(os.getenv("MIN_REPLICAS", "1"))

# Health check configuration
HEALTH_CHECK_PATH = os.getenv("HEALTH_CHECK_PATH", "/health")
READINESS_PROBE_PATH = os.getenv("READINESS_PROBE_PATH", "/health")
LIVENESS_PROBE_PATH = os.getenv("LIVENESS_PROBE_PATH", "/health")

# Working directory configuration
WORKING_DIRECTORY = os.getenv("JOCKEY_WORKING_DIR", "/tmp/jockey")

# Redis configuration
REDIS_HOST = os.getenv("DEPLOY_REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("DEPLOY_REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("DEPLOY_REDIS_DB", "0"))
REDIS_USER = os.getenv("DEPLOY_REDIS_USER", "default")
REDIS_PASSWORD = os.getenv("DEPLOY_REDIS_PASSWORD", "")

# Worker configuration
WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "5"))

# Docker configuration
DOCKER_HOST = os.getenv("DOCKER_HOST")  # If not set, uses local Docker daemon

# Environment-specific settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("JOCKEY_LOG_LEVEL", "INFO").upper()

# Ingress configuration
INGRESS_ENABLED = os.getenv("INGRESS_ENABLED", "false").lower() in ("true", "1", "yes")
INGRESS_HOST = os.getenv("INGRESS_HOST")
INGRESS_CLASS = os.getenv("INGRESS_CLASS", "nginx")

# ALB configuration
ALB_SHARED_GROUP_NAME = os.getenv("ALB_SHARED_GROUP_NAME", "alb-deployments")

# Domain configuration for user deployments
DEPLOYMENT_DOMAIN = os.getenv("DEPLOYMENT_DOMAIN", "deploy.agentops.ai")
