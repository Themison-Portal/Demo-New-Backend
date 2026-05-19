"""
Unit tests for RAG gRPC client.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.clients.rag_client import RagClient, get_rag_client, close_rag_client


class TestRagClient:
    """Tests for RagClient gRPC wrapper."""

    @pytest.fixture
    def client(self):
        """Create a RAG client with mocked channel."""
        with patch("app.clients.rag_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rag_service_address="localhost:50051")
            return RagClient()

    @pytest.mark.asyncio
    async def test_ensure_connected_creates_channel(self, client):
        """Test that _ensure_connected creates a gRPC channel."""
        with patch("app.clients.rag_client.aio.insecure_channel") as mock_channel:
            mock_channel.return_value = MagicMock()

            await client._ensure_connected()

            mock_channel.assert_called_once()
            assert client._channel is not None

    @pytest.mark.asyncio
    async def test_ensure_connected_reuses_channel(self, client):
        """Test that _ensure_connected reuses existing channel."""
        with patch("app.clients.rag_client.aio.insecure_channel") as mock_channel:
            mock_channel.return_value = MagicMock()

            await client._ensure_connected()
            await client._ensure_connected()

            # Should only create channel once
            mock_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_channel(self, client):
        """Test closing the gRPC channel."""
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._stub = MagicMock()

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stub is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, client):
        """Test closing when no channel exists."""
        # Should not raise
        await client.close()

    def test_parse_ingest_result(self, client):
        """Test parsing IngestResult protobuf."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.document_id = "test-id"
        mock_result.status = "ready"
        mock_result.chunks_count = 10
        mock_result.created_at = "2024-01-01T00:00:00"
        mock_result.error = ""

        parsed = client._parse_ingest_result(mock_result)

        assert parsed["success"] is True
        assert parsed["document_id"] == "test-id"
        assert parsed["status"] == "ready"
        assert parsed["chunks_count"] == 10
        assert parsed["error"] is None

    def test_parse_ingest_result_with_error(self, client):
        """Test parsing IngestResult with error."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.document_id = "test-id"
        mock_result.status = "error"
        mock_result.chunks_count = 0
        mock_result.created_at = ""
        mock_result.error = "PDF parsing failed"

        parsed = client._parse_ingest_result(mock_result)

        assert parsed["success"] is False
        assert parsed["error"] == "PDF parsing failed"

    def test_parse_query_response(self, client):
        """Test parsing QueryResponse protobuf."""
        # Create mock response
        mock_bbox = MagicMock()
        mock_bbox.x0 = 10.0
        mock_bbox.y0 = 20.0
        mock_bbox.x1 = 100.0
        mock_bbox.y1 = 50.0

        mock_source = MagicMock()
        mock_source.name = "Test Doc"
        mock_source.page = 1
        mock_source.section = "Introduction"
        mock_source.exact_text = "Sample text"
        mock_source.bboxes = [mock_bbox]
        mock_source.relevance = 1  # RELEVANCE_HIGH

        mock_answer = MagicMock()
        mock_answer.response = "Test answer"
        mock_answer.sources = [mock_source]

        mock_timing = MagicMock()
        mock_timing.embedding_ms = 10.0
        mock_timing.retrieval_ms = 50.0
        mock_timing.generation_ms = 1000.0
        mock_timing.total_ms = 1100.0
        mock_timing.chunks_retrieved = 5
        mock_timing.chunks_compressed = 3

        mock_cache_info = MagicMock()
        mock_cache_info.embedding_cache_hit = False
        mock_cache_info.semantic_cache_hit = False
        mock_cache_info.chunk_cache_hit = False
        mock_cache_info.response_cache_hit = False
        mock_cache_info.semantic_similarity = 0.0

        mock_response = MagicMock()
        mock_response.answer = mock_answer
        mock_response.timing = mock_timing
        mock_response.cache_info = mock_cache_info

        parsed = client._parse_query_response(mock_response)

        assert parsed["result"]["response"] == "Test answer"
        assert len(parsed["result"]["sources"]) == 1
        assert parsed["result"]["sources"][0]["name"] == "Test Doc"
        assert parsed["result"]["sources"][0]["bboxes"] == [[10.0, 20.0, 100.0, 50.0]]
        assert parsed["timing"]["embedding_ms"] == 10.0
        assert parsed["timing"]["generation_total_ms"] == 1100.0


class TestRagClientSingleton:
    """Tests for RAG client singleton management."""

    def test_get_rag_client_returns_singleton(self):
        """Test that get_rag_client returns the same instance."""
        with patch("app.clients.rag_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rag_service_address="localhost:50051")

            # Reset singleton
            import app.clients.rag_client as module
            module._rag_client = None

            client1 = get_rag_client()
            client2 = get_rag_client()

            assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_rag_client(self):
        """Test closing the singleton client."""
        with patch("app.clients.rag_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rag_service_address="localhost:50051")

            import app.clients.rag_client as module
            module._rag_client = None

            client = get_rag_client()
            client._channel = AsyncMock()

            await close_rag_client()

            assert module._rag_client is None


class TestRagClientIntegration:
    """Integration-style tests for RAG client (with mocked gRPC)."""

    @pytest.mark.asyncio
    async def test_ingest_pdf_yields_progress(self, mock_rag_grpc_client):
        """Test that ingest_pdf yields progress updates."""
        stages = []

        async for progress in mock_rag_grpc_client.ingest_pdf(
            document_url="https://example.com/test.pdf",
            document_id=uuid4()
        ):
            stages.append(progress["stage"])

        assert "DOWNLOADING" in stages
        assert "COMPLETE" in stages

    @pytest.mark.asyncio
    async def test_ingest_pdf_returns_result(self, mock_rag_grpc_client):
        """Test that ingest_pdf returns final result."""
        final_result = None

        async for progress in mock_rag_grpc_client.ingest_pdf(
            document_url="https://example.com/test.pdf",
            document_id=uuid4()
        ):
            if progress.get("result"):
                final_result = progress["result"]

        assert final_result is not None
        assert final_result["success"] is True
        assert final_result["chunks_count"] == 10

    @pytest.mark.asyncio
    async def test_query_returns_answer(self, mock_rag_grpc_client):
        """Test that query returns structured answer."""
        result = await mock_rag_grpc_client.query(
            query="What are the inclusion criteria?",
            document_id=uuid4(),
            document_name="Test.pdf"
        )

        assert "result" in result
        assert "timing" in result
        assert "inclusion criteria" in result["result"]["response"].lower()
        assert len(result["result"]["sources"]) > 0

    @pytest.mark.asyncio
    async def test_get_highlighted_pdf_returns_bytes(self, mock_rag_grpc_client):
        """Test that get_highlighted_pdf returns PDF bytes."""
        pdf_bytes = await mock_rag_grpc_client.get_highlighted_pdf(
            document_url="https://example.com/test.pdf",
            page=1,
            bboxes=[[10, 20, 100, 50]]
        )

        assert isinstance(pdf_bytes, bytes)
        assert b"%PDF" in pdf_bytes

    @pytest.mark.asyncio
    async def test_invalidate_document_returns_counts(self, mock_rag_grpc_client):
        """Test that invalidate_document returns deletion counts."""
        result = await mock_rag_grpc_client.invalidate_document(uuid4())

        assert result["success"] is True
        assert result["chunks_deleted"] == 42
        assert result["cache_entries_deleted"] == 5

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, mock_rag_grpc_client):
        """Test that health_check returns service status."""
        result = await mock_rag_grpc_client.health_check()

        assert result["status"] == "SERVING"
        assert result["version"] == "0.1.0"
        assert len(result["components"]) > 0
