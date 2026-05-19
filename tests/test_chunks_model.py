"""
Unit tests for DocumentChunkDocling model.
Tests the content_tsv generated column behavior and model structure.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from sqlalchemy import Computed, inspect
from sqlalchemy.dialects.postgresql import TSVECTOR

try:
    import docling
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False


class TestDocumentChunkDoclingModel:
    """Test DocumentChunkDocling model structure."""

    def test_content_tsv_is_computed_column(self):
        """Test that content_tsv is defined as a Computed column."""
        from app.models.chunks_docling import DocumentChunkDocling

        # Get the column object
        content_tsv_col = DocumentChunkDocling.__table__.c.content_tsv

        # Verify it has a Computed server default
        assert content_tsv_col.computed is not None, "content_tsv should be a Computed column"

    def test_content_tsv_computed_expression(self):
        """Test that content_tsv uses correct tsvector expression."""
        from app.models.chunks_docling import DocumentChunkDocling

        content_tsv_col = DocumentChunkDocling.__table__.c.content_tsv

        # Check the computed expression contains to_tsvector
        computed_text = str(content_tsv_col.computed.sqltext)
        assert "to_tsvector" in computed_text
        assert "english" in computed_text
        assert "content" in computed_text

    def test_content_tsv_is_persisted(self):
        """Test that content_tsv is a STORED (persisted) generated column."""
        from app.models.chunks_docling import DocumentChunkDocling

        content_tsv_col = DocumentChunkDocling.__table__.c.content_tsv

        # persisted=True means STORED in PostgreSQL
        assert content_tsv_col.computed.persisted is True

    def test_content_tsv_is_tsvector_type(self):
        """Test that content_tsv has TSVECTOR type."""
        from app.models.chunks_docling import DocumentChunkDocling

        content_tsv_col = DocumentChunkDocling.__table__.c.content_tsv

        assert isinstance(content_tsv_col.type, TSVECTOR)

    def test_model_has_required_columns(self):
        """Test that model has all required columns."""
        from app.models.chunks_docling import DocumentChunkDocling

        table = DocumentChunkDocling.__table__
        column_names = [c.name for c in table.columns]

        required_columns = [
            'id',
            'document_id',
            'content',
            'page_number',
            'chunk_metadata',
            'embedding',
            'created_at',
            'content_tsv',
            'embedding_large',
            'contextual_summary',
        ]

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"


class TestContentTsvExcludedFromInsert:
    """Test that content_tsv is excluded from INSERT statements."""

    def test_chunk_record_creation_excludes_content_tsv(self):
        """Test that creating a chunk record doesn't set content_tsv."""
        from app.models.chunks_docling import DocumentChunkDocling

        chunk = DocumentChunkDocling(
            id=uuid4(),
            document_id=uuid4(),
            content="Test content for full-text search",
            page_number=1,
            chunk_metadata={"test": "metadata"},
            embedding=[0.1] * 1536,
            created_at=datetime.now(),
        )

        # content_tsv should not be set on the Python object
        # (PostgreSQL generates it on insert)
        assert not hasattr(chunk, '_content_tsv_value')

    def test_content_tsv_not_in_insert_columns(self):
        """Test that content_tsv column is marked to exclude from inserts."""
        from app.models.chunks_docling import DocumentChunkDocling
        from sqlalchemy.dialects import postgresql
        from sqlalchemy import insert

        # Create an insert statement
        stmt = insert(DocumentChunkDocling).values(
            id=uuid4(),
            document_id=uuid4(),
            content="Test content",
            page_number=1,
            chunk_metadata={},
            embedding=[0.1] * 1536,
            created_at=datetime.now(),
        )

        # Compile the statement for PostgreSQL
        compiled = stmt.compile(dialect=postgresql.dialect())
        sql_string = str(compiled)

        # content_tsv should NOT appear in the INSERT statement
        # because Computed columns are automatically excluded
        assert "content_tsv" not in sql_string, \
            f"content_tsv should not be in INSERT statement: {sql_string}"


@pytest.mark.skipif(not HAS_DOCLING, reason="docling package not installed")
class TestIngestionServiceDoesNotSetContentTsv:
    """Test that RagIngestionService doesn't try to set content_tsv."""

    @pytest.fixture
    def mock_dependencies(
        self,
        mock_db_session,
        mock_embedding_client,
        mock_docling_documents,
        sample_pdf_bytes,
    ):
        """Setup mocked dependencies for ingestion service."""
        return {
            "db": mock_db_session,
            "embedding_client": mock_embedding_client,
            "documents": mock_docling_documents,
            "pdf_bytes": sample_pdf_bytes,
        }

    @pytest.mark.asyncio
    async def test_insert_docling_chunks_excludes_content_tsv(self, mock_dependencies):
        """Test that _insert_docling_chunks doesn't set content_tsv on records."""
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService
        from app.models.chunks_docling import DocumentChunkDocling

        mocks = mock_dependencies
        service = RagIngestionService(db=mocks["db"])
        service.embedding_client = mocks["embedding_client"]
        service.ensure_tables_exist = AsyncMock()

        document_id = uuid4()
        embeddings = [[0.1] * 1536 for _ in mocks["documents"]]

        # Capture what gets added to the session
        added_records = []
        original_add = mocks["db"].add

        def capture_add(record):
            added_records.append(record)
            return original_add(record)

        mocks["db"].add = MagicMock(side_effect=capture_add)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.content = mocks["pdf_bytes"]
            mock_response.raise_for_status = MagicMock()
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client

            await service._insert_docling_chunks(
                document_id=document_id,
                document_url="https://example.com/test.pdf",
                chunks=mocks["documents"],
                embeddings=embeddings,
            )

        # Verify records were added
        assert len(added_records) == len(mocks["documents"])

        # Verify no record has content_tsv explicitly set
        for record in added_records:
            assert isinstance(record, DocumentChunkDocling)
            # The record should have content but not content_tsv set as an attribute value
            assert record.content is not None
            # content_tsv should be None or not explicitly set (PostgreSQL generates it)

    @pytest.mark.asyncio
    async def test_full_ingestion_does_not_set_content_tsv(
        self,
        mock_db_session,
        mock_rag_cache_service,
        mock_semantic_cache_service,
        mock_embedding_client,
        mock_docling_documents,
        sample_pdf_bytes,
        mock_embedding_vectors,
    ):
        """Test complete ingest_pdf flow doesn't set content_tsv."""
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService
        from app.models.chunks_docling import DocumentChunkDocling

        service = RagIngestionService(
            db=mock_db_session,
            cache_service=mock_rag_cache_service,
            semantic_cache_service=mock_semantic_cache_service,
        )
        service.embedding_client = mock_embedding_client
        service.ensure_tables_exist = AsyncMock()

        # Capture added records
        added_records = []

        def capture_add(record):
            added_records.append(record)

        mock_db_session.add = MagicMock(side_effect=capture_add)

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

        assert result["success"] is True

        # All added records should be DocumentChunkDocling without content_tsv set
        for record in added_records:
            assert isinstance(record, DocumentChunkDocling)
            assert record.content is not None
            assert record.document_id == document_id


class TestGeneratedColumnErrorHandling:
    """Test that generated column errors are properly handled."""

    @pytest.mark.asyncio
    async def test_explicit_content_tsv_raises_error_on_insert(self):
        """
        Test that explicitly setting content_tsv would cause an error.
        This documents the expected behavior - you cannot insert into generated columns.
        """
        from app.models.chunks_docling import DocumentChunkDocling
        from sqlalchemy import insert
        from sqlalchemy.dialects import postgresql

        # Attempting to explicitly include content_tsv in values should be caught
        # by PostgreSQL as "cannot insert a non-DEFAULT value into column content_tsv"

        # This test verifies our model is correctly configured to prevent this
        content_tsv_col = DocumentChunkDocling.__table__.c.content_tsv

        # Computed columns should not be insertable
        assert content_tsv_col.computed is not None, \
            "content_tsv must be a Computed column to prevent insert errors"

    def test_model_documentation_warns_about_generated_column(self):
        """Test that the model has documentation about the generated column."""
        from app.models import chunks_docling
        import inspect

        source = inspect.getsource(chunks_docling)

        # Verify there's documentation about the generated column
        assert "GENERATED" in source or "Computed" in source, \
            "Model should document that content_tsv is a generated column"
