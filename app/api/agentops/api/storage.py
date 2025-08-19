from typing import Optional
from abc import ABC
from io import BytesIO
from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
import boto3
from botocore.client import Config

from agentops.api.log_config import logger
from agentops.api.environment import (
    SUPABASE_URL,
    SUPABASE_S3_ACCESS_KEY_ID,
    SUPABASE_S3_SECRET_ACCESS_KEY,
)
from agentops.api.auth import get_jwt_token, JWTPayload
from agentops.common.route_config import BaseView


_s3_client_instance: Optional[boto3.client] = None


def get_s3_client() -> boto3.client:
    """Maintain a single global instance of the S3 client"""
    global _s3_client_instance

    if _s3_client_instance is None:
        _s3_client_instance = boto3.client(
            's3',
            endpoint_url=f"{SUPABASE_URL}/storage/v1/s3",
            aws_access_key_id=SUPABASE_S3_ACCESS_KEY_ID,
            aws_secret_access_key=SUPABASE_S3_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='us-west-1',
        )
    return _s3_client_instance


class ObjectUploadResponse(BaseModel):
    url: str
    size: int


class BaseObjectUploadView(BaseView, ABC):
    """
    Abstract base class for handling object uploads to S3-compatible storage.
    This class provides a framework for uploading objects to a storage bucket
    and generating public URLs for the uploaded objects. Subclasses must
    implement or override the `filename` property to define a unique naming
    convention for the uploaded files.

    Attributes:
        bucket_name (str): The name of the S3 bucket where the object will be uploaded.
        max_size (int): The maximum allowed size for the uploaded object in bytes.
            Defaults to 10 MB (10 * 1024 * 1024).
        token (dict): A dictionary containing authentication or metadata
            information, such as project-specific identifiers.
        client (boto3.client): An S3 client instance for interacting with the
            storage service.

    Methods:
        __call__() -> ObjectUploadResponse:
            Handles the upload process by reading the request body, uploading
            the object, and returning a response with the public URL and size
            of the uploaded object.
        upload_body(body: BytesIO) -> None:
            Uploads the object to the storage bucket using the provided body.
        filename() -> str:
            Generates or retrieves a unique filename for the object. This
            property must be implemented or overridden in subclasses.
        public_url() -> str:
            Generates a public URL for accessing the uploaded object.
    """

    bucket_name: str
    max_size: int = 25 * 1024 * 1024  # 25 MB

    token: dict
    client: boto3.client

    async def __call__(self, token: JWTPayload = Depends(get_jwt_token)) -> ObjectUploadResponse:
        assert self.bucket_name is not None, "`bucket_name` must be provided"

        self.token = token
        self.client = get_s3_client()

        body = BytesIO()
        total_size = 0

        # read the body in chunks so we don't ever load an entire oversized file into memory
        async for chunk in self.request.stream():
            total_size += len(chunk)

            if total_size > self.max_size:
                logger.error("Uploaded file exceeds maximum size limit")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds the maximum limit of {self.max_size} bytes",
                )

            body.write(chunk)

        body.seek(0)
        await self.upload_body(body)
        return ObjectUploadResponse(
            url=self.public_url,
            size=total_size,
        )

    async def upload_body(self, body: BytesIO) -> None:
        """Upload the object to S3."""
        self.client.upload_fileobj(body, self.bucket_name, self.filename)

    @property
    def filename(self) -> str:
        """Generate a unique filename for the object"""
        ...

    @property
    def public_url(self) -> str:
        """Generate a public URL for the object"""
        return f"{SUPABASE_URL}/storage/v1/object/public/{self.bucket_name}/{self.filename}"
