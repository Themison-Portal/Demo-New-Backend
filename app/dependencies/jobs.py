"""
Job service dependency injection.
"""

from fastapi import Depends

from app.dependencies.redis_client import get_redis_client
from app.services.jobs.job_status_service import JobStatusService


def get_job_status_service(
    redis=Depends(get_redis_client),
) -> JobStatusService:
    """Provide JobStatusService instance."""
    return JobStatusService(redis)
