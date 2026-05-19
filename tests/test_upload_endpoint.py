"""
Comprehensive unit tests for the /upload/upload-pdf endpoint.

Tests cover:
- Authentication (API key validation)
- Request validation (required fields, formats, file types)
- Job creation and response schema
- Background task routing (gRPC vs local)
- Status endpoint
- Error handling
"""

import pytest
import json
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch, call

from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.api.routes.upload import (
    UploadDocumentRequest,
    _run_ingestion_task,
    _ingest_via_grpc,
    _ingest_via_local,
)
from app.services.jobs.job_status_service import JobStatusService, JobStatus


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def valid_upload_request():
    """Valid upload request data."""
    return {
        "document_url": "https://storage.example.com/documents/protocol.pdf",
        "document_id": str(uuid4()),
        "chunk_size": 750,
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock()
    redis.sadd = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def mock_job_service(mock_redis):
    """Mock JobStatusService."""
    service = JobStatusService(mock_redis)
    return service


# =============================================================================
# Authentication Tests
# =============================================================================

class TestUploadAuthentication:
    """Test API key authentication."""

    def test_missing_api_key_returns_422(self, client: TestClient, valid_upload_request):
        """Request without X-API-KEY header returns 422 (missing required header)."""
        response = client.post(
            "/upload/upload-pdf",
            json=valid_upload_request,
        )
        assert response.status_code == 422

    def test_invalid_api_key_returns_401(self, client: TestClient, valid_upload_request):
        """Request with invalid API key returns 401."""
        response = client.post(
            "/upload/upload-pdf",
            json=valid_upload_request,
            headers={"X-API-KEY": "wrong-key-12345"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_empty_api_key_returns_401(self, client: TestClient, valid_upload_request):
        """Request with empty API key returns 401."""
        response = client.post(
            "/upload/upload-pdf",
            json=valid_upload_request,
            headers={"X-API-KEY": ""}
        )
        assert response.status_code == 401

    def test_valid_api_key_accepted(self, client: TestClient, api_key: str, valid_upload_request, mock_redis):
        """Request with valid API key is accepted."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json=valid_upload_request,
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200


# =============================================================================
# Request Validation Tests
# =============================================================================

class TestUploadRequestValidation:
    """Test request body validation."""

    def test_missing_document_url_returns_422(self, client: TestClient, api_key: str):
        """Missing document_url field returns 422."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={"document_id": str(uuid4())},
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("document_url" in str(e) for e in errors)

    def test_missing_document_id_returns_422(self, client: TestClient, api_key: str):
        """Missing document_id field returns 422."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={"document_url": "https://example.com/test.pdf"},
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("document_id" in str(e) for e in errors)

    def test_invalid_uuid_format_returns_422(self, client: TestClient, api_key: str):
        """Invalid UUID format for document_id returns 422."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/test.pdf",
                "document_id": "not-a-valid-uuid"
            },
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 422

    def test_non_pdf_url_returns_400(self, client: TestClient, api_key: str):
        """Non-PDF file URL returns 400."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        non_pdf_urls = [
            "https://example.com/document.docx",
            "https://example.com/image.png",
            "https://example.com/data.json",
            "https://example.com/file.txt",
        ]

        for url in non_pdf_urls:
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": url,
                    "document_id": str(uuid4())
                },
                headers={"X-API-KEY": api_key}
            )

            assert response.status_code == 400, f"Expected 400 for {url}"
            assert "PDF" in response.json()["detail"].upper()

    def test_pdf_url_case_insensitive(self, client: TestClient, api_key: str, mock_redis):
        """PDF extension check is case-insensitive."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        pdf_urls = [
            "https://example.com/test.PDF",
            "https://example.com/test.Pdf",
            "https://example.com/test.pDf",
        ]

        with patch.object(app.state, "redis_client", mock_redis):
            for url in pdf_urls:
                response = client.post(
                    "/upload/upload-pdf",
                    json={
                        "document_url": url,
                        "document_id": str(uuid4())
                    },
                    headers={"X-API-KEY": api_key}
                )

                assert response.status_code == 200, f"Expected 200 for {url}"

    def test_empty_request_body_returns_422(self, client: TestClient, api_key: str):
        """Empty request body returns 422."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={},
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 422

    def test_chunk_size_optional_with_default(self, client: TestClient, api_key: str, mock_redis):
        """chunk_size is optional and defaults to 750."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": "https://example.com/test.pdf",
                    "document_id": str(uuid4()),
                    # chunk_size omitted
                },
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200

    def test_custom_chunk_size_accepted(self, client: TestClient, api_key: str, mock_redis):
        """Custom chunk_size values are accepted."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": "https://example.com/test.pdf",
                    "document_id": str(uuid4()),
                    "chunk_size": 500,
                },
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200


# =============================================================================
# Response Schema Tests
# =============================================================================

class TestUploadResponseSchema:
    """Test response schema for successful uploads."""

    def test_response_contains_job_id(self, client: TestClient, api_key: str, mock_redis, valid_upload_request):
        """Response contains job_id field."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json=valid_upload_request,
                headers={"X-API-KEY": api_key}
            )

        data = response.json()
        assert "job_id" in data
        # Validate job_id is a valid UUID
        UUID(data["job_id"])

    def test_response_contains_document_id(self, client: TestClient, api_key: str, mock_redis, valid_upload_request):
        """Response contains the same document_id from request."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json=valid_upload_request,
                headers={"X-API-KEY": api_key}
            )

        data = response.json()
        assert data["document_id"] == valid_upload_request["document_id"]

    def test_response_status_is_queued(self, client: TestClient, api_key: str, mock_redis, valid_upload_request):
        """Response status is 'queued'."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json=valid_upload_request,
                headers={"X-API-KEY": api_key}
            )

        data = response.json()
        assert data["status"] == "queued"

    def test_response_contains_message(self, client: TestClient, api_key: str, mock_redis, valid_upload_request):
        """Response contains helpful message about polling."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json=valid_upload_request,
                headers={"X-API-KEY": api_key}
            )

        data = response.json()
        assert "message" in data
        assert "status" in data["message"].lower() or "poll" in data["message"].lower()


# =============================================================================
# Background Task Routing Tests
# =============================================================================

class TestBackgroundTaskRouting:
    """Test routing between gRPC and local ingestion."""

    @pytest.mark.asyncio
    async def test_uses_grpc_when_flag_enabled(self):
        """Background task calls gRPC path when USE_GRPC_RAG=true."""
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        # Mock both paths, the job service import, and the docling import inside _run_ingestion_task
        with patch("app.api.routes.upload._ingest_via_grpc", new_callable=AsyncMock) as mock_grpc, \
             patch("app.api.routes.upload._ingest_via_local", new_callable=AsyncMock) as mock_local, \
             patch("app.api.routes.upload.JobStatusService") as mock_job_service_class, \
             patch.dict("sys.modules", {
                 "app.services.doclingRag.rag_ingestion_service": MagicMock(),
             }):
            mock_job_service = MagicMock()
            mock_job_service.fail_job = AsyncMock()
            mock_job_service_class.return_value = mock_job_service

            await _run_ingestion_task(
                job_id="test-job",
                document_url="https://example.com/test.pdf",
                document_id=uuid4(),
                chunk_size=750,
                redis_client=mock_redis,
                use_grpc=True,
                grpc_address="localhost:50051",
            )

            mock_grpc.assert_called_once()
            mock_local.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_local_when_flag_disabled(self):
        """Background task calls local path when USE_GRPC_RAG=false."""
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.api.routes.upload._ingest_via_grpc", new_callable=AsyncMock) as mock_grpc, \
             patch("app.api.routes.upload._ingest_via_local", new_callable=AsyncMock) as mock_local, \
             patch("app.api.routes.upload.JobStatusService") as mock_job_service_class, \
             patch.dict("sys.modules", {
                 "app.services.doclingRag.rag_ingestion_service": MagicMock(),
             }):
            mock_job_service = MagicMock()
            mock_job_service.fail_job = AsyncMock()
            mock_job_service_class.return_value = mock_job_service

            await _run_ingestion_task(
                job_id="test-job",
                document_url="https://example.com/test.pdf",
                document_id=uuid4(),
                chunk_size=750,
                redis_client=mock_redis,
                use_grpc=False,
                grpc_address="localhost:50051",
            )

            mock_local.assert_called_once()
            mock_grpc.assert_not_called()


# =============================================================================
# Job Status Tests
# =============================================================================

class TestJobStatusEndpoint:
    """Test the /upload/status/{job_id} endpoint."""

    @pytest.mark.asyncio
    async def test_status_returns_job_details(self, async_client: AsyncClient, mock_redis):
        """Status endpoint returns job details."""
        job_id = str(uuid4())
        job_data = {
            "job_id": job_id,
            "document_id": str(uuid4()),
            "status": "processing",
            "progress_percent": 45,
            "current_stage": "embedding",
            "message": "Generating embeddings...",
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(job_data))

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get(f"/upload/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "processing"
        assert data["progress_percent"] == 45

    @pytest.mark.asyncio
    async def test_status_unknown_job_returns_404(self, async_client: AsyncClient, mock_redis):
        """Status endpoint returns 404 for unknown job."""
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get("/upload/status/unknown-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_status_completed_job_includes_result(self, async_client: AsyncClient, mock_redis):
        """Completed job status includes result data."""
        job_id = str(uuid4())
        job_data = {
            "job_id": job_id,
            "document_id": str(uuid4()),
            "status": "complete",
            "progress_percent": 100,
            "current_stage": "complete",
            "message": "Processing complete",
            "result": {
                "success": True,
                "chunks_count": 42,
                "document_id": str(uuid4()),
            },
            "error": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(job_data))

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get(f"/upload/status/{job_id}")

        data = response.json()
        assert data["status"] == "complete"
        assert data["result"]["success"] is True
        assert data["result"]["chunks_count"] == 42

    @pytest.mark.asyncio
    async def test_status_failed_job_includes_error(self, async_client: AsyncClient, mock_redis):
        """Failed job status includes error message."""
        job_id = str(uuid4())
        job_data = {
            "job_id": job_id,
            "document_id": str(uuid4()),
            "status": "error",
            "progress_percent": 25,
            "current_stage": "error",
            "message": "Processing failed",
            "result": None,
            "error": "PDF download failed: 404 Not Found",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(job_data))

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get(f"/upload/status/{job_id}")

        data = response.json()
        assert data["status"] == "error"
        assert "404" in data["error"]


# =============================================================================
# Job Service Integration Tests
# =============================================================================

class TestJobServiceIntegration:
    """Test JobStatusService integration with upload endpoint."""

    @pytest.mark.asyncio
    async def test_job_created_on_upload(self, mock_redis):
        """Job is created in Redis when upload is requested."""
        job_service = JobStatusService(mock_redis)
        document_id = uuid4()

        job_id = await job_service.create_job(document_id)

        assert job_id is not None
        mock_redis.set.assert_called_once()

        # Verify stored data
        call_args = mock_redis.set.call_args
        stored_json = call_args[0][1]
        stored_data = json.loads(stored_json)

        assert stored_data["job_id"] == job_id
        assert stored_data["document_id"] == str(document_id)
        assert stored_data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_progress_updates_stored(self, mock_redis):
        """Progress updates are stored in Redis."""
        # Setup: create job first
        job_id = str(uuid4())
        initial_job = {
            "job_id": job_id,
            "document_id": str(uuid4()),
            "status": "queued",
            "progress_percent": 0,
            "current_stage": "queued",
            "message": "",
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(initial_job))

        job_service = JobStatusService(mock_redis)

        await job_service.update_progress(
            job_id=job_id,
            stage="embedding",
            progress_percent=60,
            message="Generating embeddings..."
        )

        # Verify update was stored
        assert mock_redis.set.called
        call_args = mock_redis.set.call_args
        stored_json = call_args[0][1]
        stored_data = json.loads(stored_json)

        assert stored_data["status"] == "processing"
        assert stored_data["progress_percent"] == 60
        assert stored_data["current_stage"] == "embedding"

    @pytest.mark.asyncio
    async def test_completion_stored_with_result(self, mock_redis):
        """Job completion is stored with result data."""
        job_id = str(uuid4())
        initial_job = {
            "job_id": job_id,
            "document_id": str(uuid4()),
            "status": "processing",
            "progress_percent": 85,
            "current_stage": "storing",
            "message": "",
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(initial_job))

        job_service = JobStatusService(mock_redis)
        result = {"success": True, "chunks_count": 42}

        await job_service.complete_job(job_id, result)

        call_args = mock_redis.set.call_args
        stored_json = call_args[0][1]
        stored_data = json.loads(stored_json)

        assert stored_data["status"] == "complete"
        assert stored_data["progress_percent"] == 100
        assert stored_data["result"]["chunks_count"] == 42

    @pytest.mark.asyncio
    async def test_failure_stored_with_error(self, mock_redis):
        """Job failure is stored with error message."""
        job_id = str(uuid4())
        initial_job = {
            "job_id": job_id,
            "document_id": str(uuid4()),
            "status": "processing",
            "progress_percent": 25,
            "current_stage": "downloading",
            "message": "",
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(initial_job))

        job_service = JobStatusService(mock_redis)

        await job_service.fail_job(job_id, "Connection timeout")

        call_args = mock_redis.set.call_args
        stored_json = call_args[0][1]
        stored_data = json.loads(stored_json)

        assert stored_data["status"] == "error"
        assert "Connection timeout" in stored_data["error"]


# =============================================================================
# Edge Cases
# =============================================================================

class TestUploadEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_url_with_query_params(self, client: TestClient, api_key: str, mock_redis):
        """PDF URL with query parameters is accepted."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": "https://storage.example.com/doc.pdf?token=abc123&expires=999",
                    "document_id": str(uuid4()),
                },
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200

    def test_url_with_encoded_characters(self, client: TestClient, api_key: str, mock_redis):
        """PDF URL with encoded characters is accepted."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": "https://storage.example.com/my%20document.pdf",
                    "document_id": str(uuid4()),
                },
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200

    def test_very_long_url(self, client: TestClient, api_key: str, mock_redis):
        """Very long PDF URL is accepted."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        long_path = "a" * 500
        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": f"https://storage.example.com/{long_path}.pdf",
                    "document_id": str(uuid4()),
                },
                headers={"X-API-KEY": api_key}
            )

        assert response.status_code == 200

    def test_concurrent_uploads_get_unique_job_ids(self, client: TestClient, api_key: str, mock_redis):
        """Multiple concurrent uploads get unique job IDs."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        job_ids = set()

        with patch.object(app.state, "redis_client", mock_redis):
            for _ in range(5):
                response = client.post(
                    "/upload/upload-pdf",
                    json={
                        "document_url": "https://example.com/test.pdf",
                        "document_id": str(uuid4()),
                    },
                    headers={"X-API-KEY": api_key}
                )
                job_ids.add(response.json()["job_id"])

        # All job IDs should be unique
        assert len(job_ids) == 5

    def test_same_document_id_creates_new_job(self, client: TestClient, api_key: str, mock_redis):
        """Re-uploading same document_id creates a new job (re-ingestion)."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        document_id = str(uuid4())
        job_ids = []

        with patch.object(app.state, "redis_client", mock_redis):
            for _ in range(2):
                response = client.post(
                    "/upload/upload-pdf",
                    json={
                        "document_url": "https://example.com/test.pdf",
                        "document_id": document_id,
                    },
                    headers={"X-API-KEY": api_key}
                )
                job_ids.append(response.json()["job_id"])

        # Each upload should create a new job
        assert job_ids[0] != job_ids[1]
