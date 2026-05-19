"""
Error handling tests for the /upload/upload-pdf endpoint.

NOTE: With background tasks, the upload endpoint returns 200 immediately with a job_id.
Errors during processing are captured in the job status (accessible via /upload/status/{job_id}).
These tests verify the background task error handling behavior.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.jobs.job_status_service import JobStatusService, JobStatus


class TestUploadValidationErrors:
    """Test validation errors that happen synchronously before job creation."""

    def test_upload_invalid_api_key_returns_401(self, client: TestClient):
        """Test that invalid API key returns 401 immediately."""
        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/test.pdf",
                "document_id": "00000000-0000-0000-0000-000000000001",
            },
            headers={"X-API-KEY": "invalid-key"}
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json().get("detail", "")

    def test_upload_non_pdf_returns_400(self, client: TestClient, api_key: str):
        """Test that non-PDF URL returns 400 immediately."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/document.docx",
                "document_id": "00000000-0000-0000-0000-000000000001",
            },
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 400
        assert "PDF" in response.json().get("detail", "").upper()

    def test_upload_missing_fields_returns_422(self, client: TestClient, api_key: str):
        """Test that missing required fields returns 422 immediately."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={},
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 422


class TestBackgroundTaskErrorCapture:
    """Test that errors during background processing are captured in job status."""

    @pytest.mark.asyncio
    async def test_job_failure_captured_in_status(self):
        """Test that job failure is captured in Redis job status."""
        mock_redis = MagicMock()
        stored_data = {}

        async def mock_set(key, value, ex=None):
            stored_data[key] = value

        async def mock_get(key):
            return stored_data.get(key)

        mock_redis.set = mock_set
        mock_redis.get = mock_get

        job_service = JobStatusService(mock_redis)

        # Create a job
        job_id = await job_service.create_job("00000000-0000-0000-0000-000000000001")

        # Simulate failure
        await job_service.fail_job(job_id, "PDF download failed: 404 Not Found")

        # Verify failure is captured
        job = await job_service.get_job(job_id)
        assert job.status == JobStatus.ERROR
        assert "404 Not Found" in job.error

    @pytest.mark.asyncio
    async def test_job_progress_updates_captured(self):
        """Test that progress updates are captured during processing."""
        mock_redis = MagicMock()
        stored_data = {}

        async def mock_set(key, value, ex=None):
            stored_data[key] = value

        async def mock_get(key):
            return stored_data.get(key)

        mock_redis.set = mock_set
        mock_redis.get = mock_get

        job_service = JobStatusService(mock_redis)

        # Create a job
        job_id = await job_service.create_job("00000000-0000-0000-0000-000000000001")

        # Update progress
        await job_service.update_progress(
            job_id=job_id,
            stage="embedding",
            progress_percent=60,
            message="Generating embeddings..."
        )

        # Verify progress is captured
        job = await job_service.get_job(job_id)
        assert job.status == JobStatus.PROCESSING
        assert job.progress_percent == 60
        assert job.current_stage == "embedding"

    @pytest.mark.asyncio
    async def test_job_completion_captured(self):
        """Test that job completion is captured with result."""
        mock_redis = MagicMock()
        stored_data = {}

        async def mock_set(key, value, ex=None):
            stored_data[key] = value

        async def mock_get(key):
            return stored_data.get(key)

        mock_redis.set = mock_set
        mock_redis.get = mock_get

        job_service = JobStatusService(mock_redis)

        # Create a job
        job_id = await job_service.create_job("00000000-0000-0000-0000-000000000001")

        # Complete job
        result = {
            "success": True,
            "chunks_count": 42,
            "document_id": "00000000-0000-0000-0000-000000000001"
        }
        await job_service.complete_job(job_id, result)

        # Verify completion
        job = await job_service.get_job(job_id)
        assert job.status == JobStatus.COMPLETE
        assert job.progress_percent == 100
        assert job.result["chunks_count"] == 42


class TestStatusEndpointErrorResponses:
    """Test error responses from the status endpoint."""

    @pytest.mark.asyncio
    async def test_status_unknown_job_returns_404(self, async_client):
        """Test that status endpoint returns 404 for unknown job."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get("/upload/status/unknown-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_status_returns_error_details(self, async_client):
        """Test that status endpoint returns error details for failed jobs."""
        job_data = {
            "job_id": "test-job-id",
            "document_id": "doc-id",
            "status": "error",
            "progress_percent": 45,
            "current_stage": "error",
            "message": "Processing failed",
            "result": None,
            "error": "Connection timeout to embedding service",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }

        import json
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(job_data))

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get("/upload/status/test-job-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Connection timeout" in data["error"]


class TestUploadEndpointReturnsQuickly:
    """Test that upload endpoint returns immediately without waiting for processing."""

    def test_upload_returns_queued_status(self, client: TestClient, api_key: str):
        """Test that upload returns 'queued' status immediately."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": "https://example.com/test.pdf",
                    "document_id": "00000000-0000-0000-0000-000000000001",
                },
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data
        # Should contain polling instructions
        assert "status" in data["message"].lower() or "poll" in data["message"].lower()
