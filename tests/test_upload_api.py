"""
API contract tests for the /upload/upload-pdf endpoint.
Tests request validation, authentication, and response schema.

NOTE: The upload endpoint now uses background tasks and returns a job ID immediately.
Actual processing happens asynchronously. Use /upload/status/{job_id} to check progress.
"""

import pytest

docling = pytest.importorskip("docling", reason="docling package not installed")

from datetime import datetime
from uuid import UUID
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.dependencies.rag import get_rag_ingestion_service


class TestUploadAuthentication:
    """Test API key authentication for upload endpoint."""

    def test_upload_missing_api_key(self, client: TestClient):
        """Test upload endpoint rejects requests without X-API-KEY header."""
        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/test.pdf",
                "document_id": "00000000-0000-0000-0000-000000000001",
            }
        )
        # FastAPI returns 422 when required header is missing
        assert response.status_code in [401, 422]

    def test_upload_invalid_api_key(self, client: TestClient):
        """Test upload endpoint rejects invalid API key."""
        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/test.pdf",
                "document_id": "00000000-0000-0000-0000-000000000001",
            },
            headers={"X-API-KEY": "invalid-key-12345"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json().get("detail", "")

    def test_upload_valid_api_key_passes_auth(
        self, client: TestClient, api_key: str
    ):
        """Test upload endpoint accepts valid API key (does not return 401)."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        # Mock Redis for job status
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
            # Should not be 401 (unauthorized)
            assert response.status_code != 401


class TestUploadRequestValidation:
    """Test request body validation for upload endpoint."""

    def test_upload_missing_document_url(self, client: TestClient, api_key: str):
        """Test upload endpoint requires document_url field."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_id": "00000000-0000-0000-0000-000000000001",
            },
            headers={"X-API-KEY": api_key}
        )
        assert response.status_code == 422
        detail = response.json().get("detail", [])
        # Pydantic validation error for missing field
        assert any("document_url" in str(err) for err in detail)

    def test_upload_missing_document_id(self, client: TestClient, api_key: str):
        """Test upload endpoint requires document_id field."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/test.pdf",
            },
            headers={"X-API-KEY": api_key}
        )
        assert response.status_code == 422
        detail = response.json().get("detail", [])
        assert any("document_id" in str(err) for err in detail)

    def test_upload_invalid_document_id_format(self, client: TestClient, api_key: str):
        """Test upload endpoint rejects non-UUID document_id."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={
                "document_url": "https://example.com/test.pdf",
                "document_id": "not-a-uuid",
            },
            headers={"X-API-KEY": api_key}
        )
        assert response.status_code == 422
        detail = response.json().get("detail", [])
        # Pydantic UUID validation error
        assert any("document_id" in str(err) or "uuid" in str(err).lower() for err in detail)

    def test_upload_non_pdf_url(self, client: TestClient, api_key: str):
        """Test upload endpoint rejects URLs not ending in .pdf."""
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

    def test_upload_empty_request_body(self, client: TestClient, api_key: str):
        """Test upload endpoint rejects empty request body."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        response = client.post(
            "/upload/upload-pdf",
            json={},
            headers={"X-API-KEY": api_key}
        )
        assert response.status_code == 422


class TestUploadJobResponse:
    """Test upload endpoint returns job response for async processing."""

    def test_upload_returns_job_id(self, client: TestClient, api_key: str):
        """Test successful upload returns job_id for async tracking."""
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

            # Verify response schema matches UploadJobResponse
            assert "job_id" in data
            assert "document_id" in data
            assert "status" in data
            assert data["status"] == "queued"
            assert "message" in data

    def test_upload_preserves_document_id(self, client: TestClient, api_key: str):
        """Test upload response contains the same document_id from request."""
        if not api_key:
            pytest.skip("UPLOAD_API_KEY not configured")

        test_uuid = "11111111-2222-3333-4444-555555555555"

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(app.state, "redis_client", mock_redis):
            response = client.post(
                "/upload/upload-pdf",
                json={
                    "document_url": "https://example.com/test.pdf",
                    "document_id": test_uuid,
                },
                headers={"X-API-KEY": api_key}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == test_uuid

    def test_upload_with_custom_chunk_size(self, client: TestClient, api_key: str):
        """Test upload accepts optional chunk_size parameter."""
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
                    "chunk_size": 500,
                },
                headers={"X-API-KEY": api_key}
            )

            # Should not fail validation
            assert response.status_code == 200

    def test_upload_job_id_is_valid_uuid(self, client: TestClient, api_key: str):
        """Test that returned job_id is a valid UUID."""
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

            data = response.json()
            # Validate job_id is a valid UUID
            job_id = data["job_id"]
            UUID(job_id)  # Will raise if invalid
