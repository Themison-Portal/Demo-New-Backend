"""
Local filesystem storage service — drop-in replacement for GCS during local development.

Files are saved under ``./uploads/`` and served via the ``/local-files/`` HTTP endpoint.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from app.services.storage.base import StorageService

logger = logging.getLogger(__name__)

UPLOADS_ROOT = Path("uploads")


class LocalStorageService(StorageService):
    """Stores files on the local filesystem and returns HTTP URLs."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base_url = base_url.rstrip("/")
        UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self,
        bucket_name: str,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: Optional[str] = None,
    ) -> dict:
        rel_path = f"{folder}/{filename}" if folder else filename
        dest = UPLOADS_ROOT / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_data)

        url = self._url_for(rel_path)
        logger.info("Saved local file: %s -> %s", dest, url)

        return {
            "path": url,
            "signed_url": url,
            "file_size": len(file_data),
        }

    def get_signed_url(
        self,
        bucket_name: str,
        blob_path: str,
        expiration_hours: int = 1,
    ) -> str:
        return self._url_for(blob_path)

    def delete_file(self, bucket_name: str, blob_path: str) -> None:
        # blob_path may be a full URL or a relative path
        if blob_path.startswith(("http://", "https://")):
            prefix = f"{self._base_url}/local-files/"
            if blob_path.startswith(prefix):
                blob_path = blob_path[len(prefix):]
            else:
                logger.warning("Cannot delete non-local URL: %s", blob_path)
                return

        target = UPLOADS_ROOT / blob_path
        try:
            target.unlink(missing_ok=True)
            logger.info("Deleted local file: %s", target)
        except Exception:
            logger.warning("Failed to delete local file: %s", target)

    def _url_for(self, rel_path: str) -> str:
        safe_path = quote(rel_path, safe="/")
        return f"{self._base_url}/local-files/{safe_path}"
