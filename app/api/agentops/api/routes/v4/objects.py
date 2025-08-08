"""
API for storing object data.

Authorized by JWT.
Accept a body of content to store.
Returns the public URL where the data can be accessed.

Uses Supabase Bucket storage (via the AWS S3 interface).
"""

import uuid

from agentops.api.environment import SUPABASE_S3_BUCKET
from agentops.api.storage import BaseObjectUploadView
from agentops.auth.views import public_route


@public_route
class ObjectUploadView(BaseObjectUploadView):
    bucket_name: str = SUPABASE_S3_BUCKET

    @property
    def filename(self) -> str:
        """Generate a unique filename for the object"""
        if not hasattr(self, '_filename'):
            self._filename = f"{self.token['project_id']}/{uuid.uuid4().hex}"
        return self._filename
