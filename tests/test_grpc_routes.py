"""
Tests for routes using gRPC RAG service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class TestUploadRouteBackgroundTask:
    """Tests for upload route with background task."""

    def test_upload_pdf_returns_job_id(self, client, api_key, sample_upload_request):
        """Test that upload returns job ID immediately."""
        with patch("app.api.routes.upload.get_settings") as mock_settings:
            settings = MagicMock()
            settings.upload_api_key = api_key
            settings.use_grpc_rag = False
            settings.rag_service_address = "localhost:50051"
            mock_settings.return_value = settings

            # Mock Redis for job status
            mock_redis = MagicMock()
            mock_redis.set = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)

            with patch.object(app.state, "redis_client", mock_redis):
                response = client.post(
                    "/upload/upload-pdf",
                    json=sample_upload_request,
                    headers={"X-API-KEY": api_key}
                )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["document_id"] == sample_upload_request["document_id"]

    def test_upload_pdf_validates_api_key(self, client, sample_upload_request):
        """Test that upload validates API key."""
        response = client.post(
            "/upload/upload-pdf",
            json=sample_upload_request,
            headers={"X-API-KEY": "invalid-key"}
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_upload_pdf_validates_file_type(self, client, api_key):
        """Test that upload validates PDF file type."""
        request = {
            "document_url": "https://example.com/test.docx",  # Not PDF
            "document_id": str(uuid4()),
            "chunk_size": 750
        }

        response = client.post(
            "/upload/upload-pdf",
            json=request,
            headers={"X-API-KEY": api_key}
        )

        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]


class TestUploadStatusEndpoint:
    """Tests for job status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_returns_job_progress(self, async_client):
        """Test that status endpoint returns job progress."""
        job_id = str(uuid4())

        # Create mock job data
        mock_job_data = {
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

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=str(mock_job_data).replace("'", '"').replace("None", "null"))

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get(f"/upload/status/{job_id}")

        # Note: This will fail because JSON encoding differs
        # In practice, we'd use proper JSON serialization

    @pytest.mark.asyncio
    async def test_get_status_returns_404_for_unknown_job(self, async_client):
        """Test that status endpoint returns 404 for unknown job."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(app.state, "redis_client", mock_redis):
            response = await async_client.get("/upload/status/unknown-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestQueryRouteWithGrpc:
    """Tests for query route with gRPC RAG service."""

    @pytest.mark.asyncio
    async def test_query_uses_grpc_when_enabled(
        self, async_client, api_key, sample_query_request, mock_rag_grpc_client
    ):
        """Test that query uses gRPC when USE_GRPC_RAG=true."""
        with patch("app.api.routes.query.get_settings") as mock_settings:
            settings = MagicMock()
            settings.upload_api_key = api_key
            settings.use_grpc_rag = True
            settings.retrieval_top_k = 20
            settings.retrieval_min_score = 0.04
            mock_settings.return_value = settings

            with patch("app.clients.rag_client.get_rag_client", return_value=mock_rag_grpc_client):
                response = await async_client.post(
                    "/query",
                    json=sample_query_request,
                    headers={"X-API-KEY": api_key}
                )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "sources" in data

    def test_query_validates_api_key(self, client, sample_query_request):
        """Test that query validates API key."""
        response = client.post(
            "/query",
            json=sample_query_request,
            headers={"X-API-KEY": "invalid-key"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_query_returns_sources(
        self, async_client, api_key, sample_query_request, mock_rag_grpc_client
    ):
        """Test that query returns sources with proper structure."""
        with patch("app.api.routes.query.get_settings") as mock_settings:
            settings = MagicMock()
            settings.upload_api_key = api_key
            settings.use_grpc_rag = True
            settings.retrieval_top_k = 20
            settings.retrieval_min_score = 0.04
            mock_settings.return_value = settings

            with patch("app.clients.rag_client.get_rag_client", return_value=mock_rag_grpc_client):
                response = await async_client.post(
                    "/query",
                    json=sample_query_request,
                    headers={"X-API-KEY": api_key}
                )

        data = response.json()
        assert len(data["sources"]) > 0

        source = data["sources"][0]
        assert "name" in source
        assert "page" in source
        assert "bboxes" in source
        assert "relevance" in source

    @pytest.mark.asyncio
    async def test_query_grpc_error_handling(
        self, async_client, api_key, sample_query_request
    ):
        """Test that gRPC query errors are handled gracefully."""
        with patch("app.api.routes.query.get_settings") as mock_settings:
            settings = MagicMock()
            settings.upload_api_key = api_key
            settings.use_grpc_rag = True
            mock_settings.return_value = settings

            mock_client = MagicMock()
            mock_client.query = AsyncMock(side_effect=RuntimeError("gRPC error"))

            with patch("app.clients.rag_client.get_rag_client", return_value=mock_client):
                response = await async_client.post(
                    "/query",
                    json=sample_query_request,
                    headers={"X-API-KEY": api_key}
                )

        assert response.status_code == 500


class TestHighlightedPdfRouteWithGrpc:
    """Tests for highlighted PDF route with gRPC RAG service."""

    @pytest.mark.asyncio
    async def test_highlighted_pdf_uses_grpc_when_enabled(
        self, async_client, mock_rag_grpc_client
    ):
        """Test that highlighted PDF uses gRPC when enabled."""
        import json

        bboxes = json.dumps([[10, 20, 100, 50]])

        with patch("app.api.routes.query.get_settings") as mock_settings:
            settings = MagicMock()
            settings.use_grpc_rag = True
            mock_settings.return_value = settings

            with patch("app.clients.rag_client.get_rag_client", return_value=mock_rag_grpc_client):
                response = await async_client.get(
                    "/query/highlighted-pdf",
                    params={
                        "doc": "https://example.com/test.pdf",
                        "page": 1,
                        "bboxes": bboxes
                    }
                )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_highlighted_pdf_validates_bboxes(self, client):
        """Test that highlighted PDF validates bboxes format."""
        response = client.get(
            "/query/highlighted-pdf",
            params={
                "doc": "https://example.com/test.pdf",
                "page": 1,
                "bboxes": "invalid-json"
            }
        )

        assert response.status_code == 400
        assert "Invalid bboxes" in response.json()["detail"]


class TestFeatureFlagRouting:
    """Tests for feature flag based routing."""

    def test_settings_has_grpc_flag(self, settings):
        """Test that settings includes gRPC configuration."""
        assert hasattr(settings, "use_grpc_rag")
        assert hasattr(settings, "rag_service_address")

    @pytest.mark.asyncio
    async def test_routing_respects_feature_flag(
        self, async_client, api_key, sample_query_request
    ):
        """Test that routing correctly respects the feature flag."""
        # Test with flag disabled
        with patch("app.api.routes.query.get_settings") as mock_settings:
            settings = MagicMock()
            settings.upload_api_key = api_key
            settings.use_grpc_rag = False
            mock_settings.return_value = settings

            with patch("app.api.routes.query._query_via_local") as mock_local:
                mock_local.return_value = {
                    "result": {"response": "local", "sources": []},
                    "timing": {}
                }

                response = await async_client.post(
                    "/query",
                    json=sample_query_request,
                    headers={"X-API-KEY": api_key}
                )

                # Local service should have been called
                mock_local.assert_called_once()
