"""
Unit tests for RagIngestionService.
Tests the ingestion pipeline including cache invalidation, chunk deletion,
embedding generation, and database persistence.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

docling = pytest.importorskip("docling", reason="docling package not installed")

from langchain_core.documents import Document


class TestRagIngestionServiceIngestPdf:
    """Test the ingest_pdf method of RagIngestionService."""

    @pytest.fixture
    def service_with_mocks(
        self,
        mock_db_session,
        mock_rag_cache_service,
        mock_semantic_cache_service,
        mock_embedding_client,
        mock_docling_documents,
        mock_embedding_vectors,
        sample_pdf_bytes,
    ):
        """Create a RagIngestionService with all dependencies mocked."""
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService

        service = RagIngestionService(
            db=mock_db_session,
            cache_service=mock_rag_cache_service,
            semantic_cache_service=mock_semantic_cache_service,
        )
        # Replace the embedding client
        service.embedding_client = mock_embedding_client

        return {
            "service": service,
            "db": mock_db_session,
            "cache": mock_rag_cache_service,
            "semantic_cache": mock_semantic_cache_service,
            "embedding_client": mock_embedding_client,
            "documents": mock_docling_documents,
            "embeddings": mock_embedding_vectors,
            "pdf_bytes": sample_pdf_bytes,
        }

    @pytest.mark.asyncio
    async def test_ingest_pdf_invalidates_redis_cache(self, service_with_mocks):
        """Test that ingest_pdf calls cache_service.invalidate_document()."""
        mocks = service_with_mocks
        document_id = uuid4()

        # Patch DoclingLoader and httpx to avoid real network calls
        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            # Setup DoclingLoader mock
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            # Setup httpx mock
            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            # Patch ensure_tables_exist to avoid DB calls
            mocks["service"].ensure_tables_exist = AsyncMock()

            await mocks["service"].ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            # Verify cache invalidation was called
            mocks["cache"].invalidate_document.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_ingest_pdf_invalidates_semantic_cache(self, service_with_mocks):
        """Test that ingest_pdf calls semantic_cache_service.invalidate_document()."""
        mocks = service_with_mocks
        document_id = uuid4()

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            mocks["service"].ensure_tables_exist = AsyncMock()

            await mocks["service"].ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            mocks["semantic_cache"].invalidate_document.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_ingest_pdf_deletes_existing_chunks(self, service_with_mocks):
        """Test that ingest_pdf deletes existing chunks before re-ingestion."""
        mocks = service_with_mocks
        document_id = uuid4()

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            mocks["service"].ensure_tables_exist = AsyncMock()

            await mocks["service"].ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            # Verify DB execute was called (for DELETE statement)
            mocks["db"].execute.assert_called()
            # Verify commit was called after delete
            assert mocks["db"].commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_ingest_pdf_creates_embeddings(self, service_with_mocks):
        """Test that ingest_pdf calls OpenAI to generate embeddings."""
        mocks = service_with_mocks
        document_id = uuid4()

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            mocks["service"].ensure_tables_exist = AsyncMock()

            await mocks["service"].ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            # Verify embedding client was called with chunk texts
            mocks["embedding_client"].aembed_documents.assert_called_once()
            call_args = mocks["embedding_client"].aembed_documents.call_args[0][0]
            # Should be called with the text content from documents
            assert len(call_args) == len(mocks["documents"])

    @pytest.mark.asyncio
    async def test_ingest_pdf_stores_chunks_in_db(self, service_with_mocks):
        """Test that ingest_pdf adds chunk records to the database."""
        mocks = service_with_mocks
        document_id = uuid4()

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            mocks["service"].ensure_tables_exist = AsyncMock()

            await mocks["service"].ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            # Verify db.add was called for each chunk
            assert mocks["db"].add.call_count == len(mocks["documents"])

    @pytest.mark.asyncio
    async def test_ingest_pdf_returns_success_response(self, service_with_mocks):
        """Test that ingest_pdf returns correct success response."""
        mocks = service_with_mocks
        document_id = uuid4()

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            mocks["service"].ensure_tables_exist = AsyncMock()

            result = await mocks["service"].ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            assert result["success"] is True
            assert result["document_id"] == document_id
            assert result["status"] == "ready"
            assert result["chunks_count"] == len(mocks["documents"])
            assert "created_at" in result
            assert isinstance(result["created_at"], datetime)

    @pytest.mark.asyncio
    async def test_ingest_pdf_rollback_on_insert_error(self, service_with_mocks):
        """Test that ingest_pdf rolls back transaction on database error."""
        mocks = service_with_mocks
        document_id = uuid4()

        # Make db.add raise an exception
        mocks["db"].add.side_effect = Exception("Database insert failed")

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mocks["documents"]
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            mocks["service"].ensure_tables_exist = AsyncMock()

            with pytest.raises(RuntimeError) as exc_info:
                await mocks["service"].ingest_pdf(
                    document_url="https://example.com/test.pdf",
                    document_id=document_id,
                )

            assert "Failed to insert chunks" in str(exc_info.value) or "PDF ingestion failed" in str(exc_info.value)
            # Verify rollback was called
            mocks["db"].rollback.assert_called()


class TestRagIngestionServiceHelpers:
    """Test helper methods of RagIngestionService."""

    @pytest.fixture
    def service(self, mock_db_session):
        """Create a RagIngestionService with minimal mocks."""
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService
        return RagIngestionService(db=mock_db_session)

    def test_extract_docling_citation_metadata_with_valid_data(self, service):
        """Test citation metadata extraction with valid Docling metadata."""
        metadata = {
            "dl_meta": {
                "doc_items": [{"prov": [{"page_no": 5}]}],
                "headings": ["Introduction", "Background"]
            }
        }

        result = service._extract_docling_citation_metadata(metadata)

        assert result["page_number"] == 5
        assert result["headings"] == ["Introduction", "Background"]

    def test_extract_docling_citation_metadata_with_empty_data(self, service):
        """Test citation metadata extraction with empty metadata."""
        metadata = {}

        result = service._extract_docling_citation_metadata(metadata)

        assert result["page_number"] is None
        assert result["headings"] == []

    def test_extract_docling_citation_metadata_with_missing_fields(self, service):
        """Test citation metadata extraction with partial metadata."""
        metadata = {
            "dl_meta": {
                "doc_items": [],
                "headings": None
            }
        }

        result = service._extract_docling_citation_metadata(metadata)

        assert result["page_number"] is None
        assert result["headings"] == []

    @pytest.mark.asyncio
    async def test_delete_existing_chunks(self, mock_db_session):
        """Test _delete_existing_chunks executes DELETE and commits."""
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService

        # Setup mock to return rowcount
        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = RagIngestionService(db=mock_db_session)
        document_id = uuid4()

        result = await service._delete_existing_chunks(document_id)

        assert result == 10
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestRagIngestionServiceWithoutCaches:
    """Test RagIngestionService behavior when caches are not configured."""

    @pytest.mark.asyncio
    async def test_ingest_pdf_without_redis_cache(
        self, mock_db_session, mock_embedding_client, mock_docling_documents, sample_pdf_bytes
    ):
        """Test ingest_pdf works without Redis cache service."""
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService

        # Create service without cache
        service = RagIngestionService(
            db=mock_db_session,
            cache_service=None,
            semantic_cache_service=None,
        )
        service.embedding_client = mock_embedding_client
        service.ensure_tables_exist = AsyncMock()

        document_id = uuid4()

        with patch("app.services.doclingRag.rag_ingestion_service.DoclingLoader") as mock_loader_cls, \
             patch("httpx.AsyncClient") as mock_httpx:
            mock_loader = MagicMock()
            mock_loader.load.return_value = mock_docling_documents
            mock_loader_cls.return_value = mock_loader

            mock_response = MagicMock()
            mock_response.content = sample_pdf_bytes
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            result = await service.ingest_pdf(
                document_url="https://example.com/test.pdf",
                document_id=document_id,
            )

            # Should complete successfully without cache
            assert result["success"] is True
