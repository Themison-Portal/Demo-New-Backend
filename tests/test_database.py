"""
Database connection and schema tests.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestDatabaseConnection:
    """Test database connectivity and basic operations."""

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session: AsyncSession):
        """Test that we can connect to the database."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_pgvector_extension_exists(self, db_session: AsyncSession):
        """Test that pgvector extension is installed."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_uuid_extension_exists(self, db_session: AsyncSession):
        """Test that uuid-ossp extension is installed."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp')")
        )
        assert result.scalar() is True


class TestDatabaseSchema:
    """Test that required tables exist."""

    @pytest.mark.asyncio
    async def test_profiles_table_exists(self, db_session: AsyncSession):
        """Test profiles table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'profiles')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_organizations_table_exists(self, db_session: AsyncSession):
        """Test organizations table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_members_table_exists(self, db_session: AsyncSession):
        """Test members table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'members')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_trials_table_exists(self, db_session: AsyncSession):
        """Test trials table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'trials')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_trial_documents_table_exists(self, db_session: AsyncSession):
        """Test trial_documents table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'trial_documents')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_document_chunks_docling_table_exists(self, db_session: AsyncSession):
        """Test document_chunks_docling table exists (RAG vector store)."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'document_chunks_docling')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_semantic_cache_table_exists(self, db_session: AsyncSession):
        """Test semantic_cache_responses table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'semantic_cache_responses')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_chat_sessions_table_exists(self, db_session: AsyncSession):
        """Test chat_sessions table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_sessions')")
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_chat_messages_table_exists(self, db_session: AsyncSession):
        """Test chat_messages table exists."""
        result = await db_session.execute(
            text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'chat_messages')")
        )
        assert result.scalar() is True


class TestVectorColumns:
    """Test pgvector column configuration."""

    @pytest.mark.asyncio
    async def test_chunks_embedding_column_exists(self, db_session: AsyncSession):
        """Test that document_chunks_docling has embedding column."""
        result = await db_session.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'document_chunks_docling'
                    AND column_name = 'embedding'
                )
            """)
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_semantic_cache_embedding_column_exists(self, db_session: AsyncSession):
        """Test that semantic_cache_responses has query_embedding column."""
        result = await db_session.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'semantic_cache_responses'
                    AND column_name = 'query_embedding'
                )
            """)
        )
        assert result.scalar() is True


class TestIndexes:
    """Test that required indexes exist."""

    @pytest.mark.asyncio
    async def test_hnsw_index_exists(self, db_session: AsyncSession):
        """Test that HNSW index exists on document_chunks_docling."""
        result = await db_session.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'document_chunks_docling'
                    AND indexname LIKE '%hnsw%'
                )
            """)
        )
        # Note: Index might have different name, so we check for any HNSW index
        # or just check the table has some index on embedding
        exists = result.scalar()
        if not exists:
            # Fallback: check for any index with 'embedding' in the name
            result2 = await db_session.execute(
                text("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = 'document_chunks_docling'
                        AND indexname LIKE '%embedding%'
                    )
                """)
            )
            exists = result2.scalar()
        assert exists is True
