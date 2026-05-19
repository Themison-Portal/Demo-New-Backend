"""
Abstract base class for storage services.
"""

from abc import ABC, abstractmethod
from typing import Optional


class StorageService(ABC):
    """Interface that both GCS and local-filesystem storage implement."""

    @abstractmethod
    def upload_file(
        self,
        bucket_name: str,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: Optional[str] = None,
    ) -> dict:
        """Store *file_data* and return ``{path, signed_url, file_size}``."""
        ...

    @abstractmethod
    def get_signed_url(
        self,
        bucket_name: str,
        blob_path: str,
        expiration_hours: int = 1,
    ) -> str:
        """Return a download URL for *blob_path*."""
        ...

    @abstractmethod
    def delete_file(self, bucket_name: str, blob_path: str) -> None:
        """Delete the object identified by *blob_path*."""
        ...
