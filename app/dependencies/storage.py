"""
FastAPI dependency for the storage service (singleton).

Auto-selects GCS when ``gcs_bucket_trial_documents`` is configured,
otherwise falls back to local filesystem storage.
"""

import logging
from functools import lru_cache

from app.config import get_settings
from app.services.storage.base import StorageService

logger = logging.getLogger(__name__)


@lru_cache()
def _singleton() -> StorageService:
    settings = get_settings()

    if settings.gcs_bucket_trial_documents:
        from app.services.storage.gcs_service import GCSStorageService

        logger.info("Using GCS storage (bucket=%s)", settings.gcs_bucket_trial_documents)
        return GCSStorageService()

    from app.services.storage.local_service import LocalStorageService

    logger.info("GCS not configured — using local filesystem storage (./uploads/)")
    return LocalStorageService()


def get_storage_service() -> StorageService:
    return _singleton()
