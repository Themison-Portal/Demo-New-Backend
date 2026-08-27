"""
This module contains the document chunk model.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Computed, DateTime, ForeignKey, Index, Integer, Text, Boolean, String
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, relationship

from .base import Base
from .documents import Document

# New table for individual chunks
class DocumentChunkDocling(Base):
    """
    A model that represents a document chunk.
    """
    __tablename__ = 'document_chunks_docling'

    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[UUID] = Column(UUID(as_uuid=True), ForeignKey('trial_documents.id'), nullable=False)

    # Bare UUID, not a local FK - no `organizations` table exists in this DB
    # (confirmed via information_schema.columns). Org identity is owned by
    # another service and passed in at ingestion time. Column already
    # existed as NOT NULL in prod - this was just missing from the model,
    # added here to remove model/DB drift, no schema change needed for this
    # part.
    organization_id: Mapped[UUID] = Column(UUID(as_uuid=True), nullable=False)

    content: Mapped[str] = Column(Text, nullable=False)
    page_number: Mapped[int] = Column(Integer, nullable=True)
    chunk_metadata: Mapped[Dict] = Column("chunk_metadata", JSON)
    embedding: Mapped[List[float]] = Column(Vector(1536))
    created_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Phase 1: Hybrid search - tsvector for BM25 full-text search
    # This is a PostgreSQL GENERATED ALWAYS column - Computed() excludes it from INSERT/UPDATE
    content_tsv = Column(TSVECTOR, Computed("to_tsvector('english', content)", persisted=True))

    # Phase 3: Larger embedding model (2000 dimensions - HNSW index limit)
    embedding_large: Mapped[List[float]] = Column(Vector(2000), nullable=True)

    # Phase 4: Contextual retrieval
    contextual_summary: Mapped[str] = Column(Text, nullable=True)

    # Phase 5: content hash for re-ingestion dedup - sha256 of raw
    # (pre-overlap) chunk content. NEW COLUMN - needs migration.
    content_hash: Mapped[str] = Column(String(64), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="docling_chunks")

    __table_args__ = (
        # Original HNSW index for 1536-dim embeddings
        Index(
            'idx_chunks_embedding_hnsw',
            'embedding',
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 64},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
        Index('idx_chunks_document_id', 'document_id'),
        # Phase 1: GIN index for full-text search
        Index('idx_chunks_content_gin', 'content_tsv', postgresql_using='gin'),
        # Phase 3: HNSW index for 3072-dim embeddings
        Index(
            'idx_chunks_embedding_large_hnsw',
            'embedding_large',
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 64},
            postgresql_ops={'embedding_large': 'vector_cosine_ops'}
        ),
        # Phase 5: lookup index for hash-based dedup on re-ingestion. NEW.
        Index('idx_chunks_content_hash', 'content_hash'),
        # Tenant isolation: direct index on org_id (queries in
        # retrieval_service.py already filter on this column). NEW.
        Index('idx_chunks_organization_id', 'organization_id'),
    )