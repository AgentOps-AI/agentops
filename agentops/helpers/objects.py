from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentops.client.api.types import UploadedObjectResponse


def upload_object(body: bytes) -> 'UploadedObjectResponse':
    """Upload an object to the agentops server."""
    from agentops import get_client
    
    client = get_client()
    return client.api.v4.upload_object(body)


