"""
Tests for foreign key constraint between document_chunks_docling and trial_documents.

Reproduces the production bug:
    ForeignKeyViolationError: insert or update on table "document_chunks_docling"
    violates foreign key constraint "document_chunks_docling_document_id_fkey"
    Key (document_id)=(...) is not present in table "trial_documents".
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunks_docling import DocumentChunkDocling


async def _insert_test_document(db_session: AsyncSession, doc_id: uuid.UUID) -> None:
    """Insert a test document using raw SQL to bypass the document_type_enum mismatch."""
    await db_session.execute(
        text("""
            INSERT INTO trial_documents (id, document_name, document_type, document_url, status, created_at)
            VALUES (:id, :name, 'protocol'::document_type_enum, :url, 'active', now())
        """),
        {"id": str(doc_id), "name": "test_fk.pdf", "url": "https://example.com/test_fk.pdf"},
    )
    await db_session.flush()


async def _cleanup_test_data(db_session: AsyncSession, doc_id: uuid.UUID) -> None:
    """Remove test data (chunks then document) via raw SQL."""
    await db_session.execute(
        text("DELETE FROM document_chunks_docling WHERE document_id = :id"),
        {"id": str(doc_id)},
    )
    await db_session.execute(
        text("DELETE FROM trial_documents WHERE id = :id"),
        {"id": str(doc_id)},
    )
    await db_session.commit()


class TestDocumentForeignKeyConstraint:
    """Test FK constraint between document_chunks_docling → trial_documents."""

    @pytest.mark.asyncio
    async def test_chunk_insert_fails_without_document(self, db_session: AsyncSession):
        """
        Insert a chunk with a document_id that doesn't exist in trial_documents.
        Expect IntegrityError with FK violation — reproduces the exact production bug.
        """
        fake_document_id = uuid.uuid4()

        chunk = DocumentChunkDocling(
            id=uuid.uuid4(),
            document_id=fake_document_id,
            content="Test chunk content for FK constraint test",
            page_number=1,
            chunk_metadata={"test": True},
            embedding=[0.1] * 1536,
            created_at=datetime.utcnow(),
        )
        db_session.add(chunk)

        with pytest.raises(IntegrityError, match="document_chunks_docling_document_id_fkey"):
            await db_session.flush()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_chunk_insert_succeeds_with_existing_document(self, db_session: AsyncSession):
        """
        Create a Document in trial_documents first, then insert a chunk referencing it.
        Expect success.
        """
        doc_id = uuid.uuid4()

        try:
            await _insert_test_document(db_session, doc_id)

            chunk = DocumentChunkDocling(
                id=uuid.uuid4(),
                document_id=doc_id,
                content="Chunk linked to a real document",
                page_number=1,
                chunk_metadata={"test": True},
                embedding=[0.2] * 1536,
                created_at=datetime.utcnow(),
            )
            db_session.add(chunk)
            await db_session.flush()

            # Verify the chunk was inserted
            result = await db_session.execute(
                select(DocumentChunkDocling).where(DocumentChunkDocling.document_id == doc_id)
            )
            inserted_chunk = result.scalars().first()
            assert inserted_chunk is not None
            assert inserted_chunk.document_id == doc_id
            assert inserted_chunk.content == "Chunk linked to a real document"
        finally:
            await _cleanup_test_data(db_session, doc_id)

    @pytest.mark.asyncio
    async def test_cascade_delete_removes_chunks(self, db_session: AsyncSession):
        """
        Create a document + chunk, delete the document, verify the chunk is also
        deleted. The FK has ON DELETE CASCADE.
        """
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()

        await _insert_test_document(db_session, doc_id)

        chunk = DocumentChunkDocling(
            id=chunk_id,
            document_id=doc_id,
            content="Chunk that should be cascade-deleted",
            page_number=1,
            chunk_metadata={"test": True},
            embedding=[0.3] * 1536,
            created_at=datetime.utcnow(),
        )
        db_session.add(chunk)
        await db_session.commit()

        # Verify chunk exists before delete
        result = await db_session.execute(
            text("SELECT count(*) FROM document_chunks_docling WHERE document_id = :id"),
            {"id": str(doc_id)},
        )
        assert result.scalar() == 1

        # Delete the parent document — CASCADE should remove the chunk
        await db_session.execute(
            text("DELETE FROM trial_documents WHERE id = :id"),
            {"id": str(doc_id)},
        )
        await db_session.commit()

        # Verify chunk was cascade-deleted
        result = await db_session.execute(
            text("SELECT count(*) FROM document_chunks_docling WHERE document_id = :id"),
            {"id": str(doc_id)},
        )
        assert result.scalar() == 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("docling"),
        reason="docling package not installed",
    )
    async def test_ingestion_service_fails_without_document(self, db_session: AsyncSession):
        """
        Call RagIngestionService._insert_docling_chunks() with a non-existent document_id.
        Expect RuntimeError("Failed to insert chunks: ...") — the exact error from production.
        """
        from langchain_core.documents import Document as LCDocument
        from app.services.doclingRag.rag_ingestion_service import RagIngestionService

        fake_document_id = uuid.uuid4()
        fake_url = "https://example.com/nonexistent.pdf"

        chunks = [
            LCDocument(
                page_content="Test chunk for ingestion FK test",
                metadata={
                    "dl_meta": {
                        "doc_items": [{"prov": [{"page_no": 1}]}],
                        "headings": ["Test"],
                    }
                },
            )
        ]
        embeddings = [[0.4] * 1536]

        service = RagIngestionService(db=db_session)

        # Mock the HTTP call inside _insert_docling_chunks (it fetches the PDF)
        mock_response = MagicMock()
        mock_response.content = b"%PDF-1.4 fake"
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            with pytest.raises(RuntimeError, match="Failed to insert chunks"):
                await service._insert_docling_chunks(
                    document_id=fake_document_id,
                    document_url=fake_url,
                    chunks=chunks,
                    embeddings=embeddings,
                )
