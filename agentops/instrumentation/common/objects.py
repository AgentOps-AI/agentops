from agentops.client.api.types import UploadedObjectResponse
from . import AttributeMap, _extract_attributes_from_mapping


UPLOADED_OBJECT_ATTRIBUTES: AttributeMap = {
    "object_url": "url",
    "object_size": "size",
}


def get_uploaded_object_attributes(uploaded_object: UploadedObjectResponse, prefix: str) -> AttributeMap:
    """Extract attributes from an uploaded object.

    This is a common function so we can standardize the data format we serialize
    stored objects to.

    Args:
        uploaded_object: The uploaded object to extract attributes from.
        prefix: The prefix to use for the attribute keys. Keys will be concatenated
            with the prefix and a dot (.) separator.

    Returns:
        A dictionary of extracted attributes.
    """
    attribute_map = {f"{prefix}.{key}": value for key, value in UPLOADED_OBJECT_ATTRIBUTES.items()}
    return _extract_attributes_from_mapping(uploaded_object, attribute_map)
