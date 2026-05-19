"""
Job status service for tracking background tasks.
Uses Redis for fast status updates and polling.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from redis.asyncio import Redis


logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class JobProgress(BaseModel):
    """Job progress data stored in Redis."""
    job_id: str
    document_id: str
    status: JobStatus
    progress_percent: int = 0
    current_stage: str = ""
    message: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class JobStatusService:
    """
    Service for tracking background job status in Redis.

    Key Pattern: job:{job_id}
    TTL: 1 hour after completion (allows client to retrieve final status)
    """

    PREFIX = "job"
    TTL_ACTIVE = 3600       # 1 hour for active jobs
    TTL_COMPLETE = 3600     # 1 hour after completion

    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, job_id: str) -> str:
        """Generate Redis key for job."""
        return f"{self.PREFIX}:{job_id}"

    async def create_job(self, document_id: UUID) -> str:
        """
        Create a new job and return job ID.
        """
        job_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        progress = JobProgress(
            job_id=job_id,
            document_id=str(document_id),
            status=JobStatus.QUEUED,
            progress_percent=0,
            current_stage="queued",
            message="Job queued for processing",
            created_at=now,
            updated_at=now,
        )

        await self.redis.set(
            self._key(job_id),
            progress.model_dump_json(),
            ex=self.TTL_ACTIVE
        )

        logger.info(f"Created job {job_id} for document {document_id}")
        return job_id

    async def get_job(self, job_id: str) -> Optional[JobProgress]:
        """
        Get job status by ID.
        """
        data = await self.redis.get(self._key(job_id))
        if not data:
            return None

        return JobProgress.model_validate_json(data)

    async def update_progress(
        self,
        job_id: str,
        stage: str,
        progress_percent: int,
        message: str = "",
    ) -> None:
        """
        Update job progress during processing.
        """
        job = await self.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for progress update")
            return

        job.status = JobStatus.PROCESSING
        job.current_stage = stage
        job.progress_percent = min(progress_percent, 99)  # Reserve 100 for complete
        job.message = message
        job.updated_at = datetime.utcnow().isoformat()

        await self.redis.set(
            self._key(job_id),
            job.model_dump_json(),
            ex=self.TTL_ACTIVE
        )

    async def complete_job(
        self,
        job_id: str,
        result: dict,
    ) -> None:
        """
        Mark job as complete with result.
        """
        job = await self.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for completion")
            return

        job.status = JobStatus.COMPLETE
        job.progress_percent = 100
        job.current_stage = "complete"
        job.message = "Processing complete"
        job.result = result
        job.updated_at = datetime.utcnow().isoformat()

        await self.redis.set(
            self._key(job_id),
            job.model_dump_json(),
            ex=self.TTL_COMPLETE
        )

        logger.info(f"Job {job_id} completed successfully")

    async def fail_job(
        self,
        job_id: str,
        error: str,
    ) -> None:
        """
        Mark job as failed with error.
        """
        job = await self.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for failure")
            return

        job.status = JobStatus.ERROR
        job.current_stage = "error"
        job.message = "Processing failed"
        job.error = error
        job.updated_at = datetime.utcnow().isoformat()

        await self.redis.set(
            self._key(job_id),
            job.model_dump_json(),
            ex=self.TTL_COMPLETE
        )

        logger.error(f"Job {job_id} failed: {error}")
