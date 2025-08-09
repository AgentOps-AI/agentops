from uuid import UUID
from jockey.backend.models.secret import Secret


def create_secret(namespace: str, deployment_id: str | UUID, key: str, value: str) -> Secret:
    """Create a new secret in the cluster.

    Args:
        namespace: Kubernetes namespace
        deployment_id: Deployment ID to attach the secret to
        key: Secret key name (lowercase with dashes, e.g., 'agentops-api-key')
        value: Secret value to store

    Returns:
        Secret: The created secret object
    """
    # Transform key to uppercase with underscores for the data key
    data_key = key.upper().replace('-', '_')
    secret_data = {data_key: value}
    labels = {
        "deployment": str(deployment_id),
        "original-key": key,  # Store original key name for retrieval
    }

    secret = Secret(name=key, namespace=namespace, string_data=secret_data, labels=labels)
    return secret.create()


def delete_secret(namespace: str, deployment_id: str | UUID, key: str) -> bool:
    """Delete a secret by key name for a specific deployment.

    Args:
        namespace: Kubernetes namespace
        deployment_id: Deployment ID to verify ownership
        key: Secret key name

    Returns:
        True if deletion was successful, False otherwise
    """
    # First verify the secret belongs to this deployment using label selector
    try:
        label_selector = f"deployment={deployment_id}"
        secret = Secret.get(key, namespace, label_selector=label_selector)
        if not secret:
            return False
    except Exception:
        return False

    return Secret.delete_by_name(key, namespace)


def list_secrets(namespace: str, deployment_id: str) -> list[str]:
    """List all secret names for a specific deployment.

    Args:
        namespace: Kubernetes namespace
        deployment_id: Deployment ID to filter by

    Returns:
        List of original secret key names for the deployment
    """
    try:
        label_selector = f"deployment={deployment_id}"
        secrets = Secret.filter(namespace, label_selector=label_selector)
        # Try to get original key from label, otherwise reverse the transformation
        result = []
        for secret in secrets:
            if "original-key" in secret.labels:
                result.append(secret.labels["original-key"])
            else:
                # Reverse transformation: agentops-api-key -> AGENTOPS_API_KEY
                result.append(secret.name.upper().replace('-', '_'))
        return result
    except Exception:
        return []
