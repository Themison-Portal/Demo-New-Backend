"""
Tests for job status service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.jobs.job_status_service import (
    JobStatus,
    JobProgress,
    JobStatusService,
)


class TestJobStatusService:
    """Tests for JobStatusService."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis = MagicMock()
        redis.set = AsyncMock()
        redis.get = AsyncMock()
        return redis

    @pytest.fixture
    def job_service(self, mock_redis):
        """Create JobStatusService with mock Redis."""
        return JobStatusService(mock_redis)

    @pytest.mark.asyncio
    async def test_create_job_returns_job_id(self, job_service, mock_redis):
        """Test that create_job returns a job ID."""
        document_id = uuid4()
        job_id = await job_service.create_job(document_id)

        assert job_id is not None
        assert len(job_id) == 36  # UUID length
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_stores_initial_state(self, job_service, mock_redis):
        """Test that create_job stores correct initial state."""
        document_id = uuid4()
        await job_service.create_job(document_id)

        # Check the stored data
        call_args = mock_redis.set.call_args
        stored_data = call_args[0][1]  # Second positional arg is the value

        assert "queued" in stored_data
        assert str(document_id) in stored_data

    @pytest.mark.asyncio
    async def test_get_job_returns_job_progress(self, job_service, mock_redis):
        """Test that get_job returns JobProgress."""
        job_id = str(uuid4())
        document_id = str(uuid4())

        mock_redis.get.return_value = f'''{{
            "job_id": "{job_id}",
            "document_id": "{document_id}",
            "status": "processing",
            "progress_percent": 50,
            "current_stage": "embedding",
            "message": "Processing...",
            "result": null,
            "error": null,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }}'''

        job = await job_service.get_job(job_id)

        assert job is not None
        assert job.job_id == job_id
        assert job.status == JobStatus.PROCESSING
        assert job.progress_percent == 50

    @pytest.mark.asyncio
    async def test_get_job_returns_none_for_missing_job(self, job_service, mock_redis):
        """Test that get_job returns None for non-existent job."""
        mock_redis.get.return_value = None

        job = await job_service.get_job("non-existent")

        assert job is None

    @pytest.mark.asyncio
    async def test_update_progress_updates_state(self, job_service, mock_redis):
        """Test that update_progress updates job state."""
        job_id = str(uuid4())
        document_id = str(uuid4())

        # Mock get_job to return existing job
        mock_redis.get.return_value = f'''{{
            "job_id": "{job_id}",
            "document_id": "{document_id}",
            "status": "queued",
            "progress_percent": 0,
            "current_stage": "queued",
            "message": "",
            "result": null,
            "error": null,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }}'''

        await job_service.update_progress(
            job_id=job_id,
            stage="embedding",
            progress_percent=60,
            message="Generating embeddings..."
        )

        # Verify set was called with updated data
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        stored_data = call_args[0][1]

        assert "embedding" in stored_data
        assert "60" in stored_data

    @pytest.mark.asyncio
    async def test_complete_job_sets_complete_status(self, job_service, mock_redis):
        """Test that complete_job sets status to complete."""
        job_id = str(uuid4())
        document_id = str(uuid4())

        mock_redis.get.return_value = f'''{{
            "job_id": "{job_id}",
            "document_id": "{document_id}",
            "status": "processing",
            "progress_percent": 85,
            "current_stage": "storing",
            "message": "",
            "result": null,
            "error": null,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }}'''

        result = {"success": True, "chunks_count": 42}
        await job_service.complete_job(job_id, result)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        stored_data = call_args[0][1]

        assert "complete" in stored_data
        assert "100" in stored_data
        assert "42" in stored_data

    @pytest.mark.asyncio
    async def test_fail_job_sets_error_status(self, job_service, mock_redis):
        """Test that fail_job sets status to error."""
        job_id = str(uuid4())
        document_id = str(uuid4())

        mock_redis.get.return_value = f'''{{
            "job_id": "{job_id}",
            "document_id": "{document_id}",
            "status": "processing",
            "progress_percent": 45,
            "current_stage": "embedding",
            "message": "",
            "result": null,
            "error": null,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }}'''

        await job_service.fail_job(job_id, "Something went wrong")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        stored_data = call_args[0][1]

        assert "error" in stored_data
        assert "Something went wrong" in stored_data


class TestJobProgress:
    """Tests for JobProgress model."""

    def test_job_progress_creation(self):
        """Test JobProgress model creation."""
        progress = JobProgress(
            job_id="test-id",
            document_id="doc-id",
            status=JobStatus.QUEUED,
            progress_percent=0,
            current_stage="queued",
            message="Waiting...",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        assert progress.job_id == "test-id"
        assert progress.status == JobStatus.QUEUED
        assert progress.progress_percent == 0

    def test_job_progress_serialization(self):
        """Test JobProgress JSON serialization."""
        progress = JobProgress(
            job_id="test-id",
            document_id="doc-id",
            status=JobStatus.PROCESSING,
            progress_percent=50,
            current_stage="embedding",
            message="Processing...",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        json_str = progress.model_dump_json()

        assert "test-id" in json_str
        assert "processing" in json_str
        assert "50" in json_str


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_job_status_values(self):
        """Test JobStatus enum values."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETE.value == "complete"
        assert JobStatus.ERROR.value == "error"

    def test_job_status_is_string(self):
        """Test JobStatus inherits from str."""
        assert isinstance(JobStatus.QUEUED, str)
        assert JobStatus.QUEUED == "queued"
