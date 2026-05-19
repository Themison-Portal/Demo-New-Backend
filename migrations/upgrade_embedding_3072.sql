-- Migration: Upgrade to 2000-dimension embeddings (text-embedding-3-large)
-- Note: Using 2000 dims instead of 3072 due to HNSW index limit in pgvector
-- Run with: psql $SUPABASE_DB_URL -f migrations/upgrade_embedding_3072.sql
-- Or paste in Supabase SQL Editor (this version works with SQL Editor)

-- Step 1: Add new 2000-dim embedding column to document chunks
ALTER TABLE document_chunks_docling
ADD COLUMN IF NOT EXISTS embedding_large vector(2000);

-- Step 2: Add contextual summary column (for Phase 4)
ALTER TABLE document_chunks_docling
ADD COLUMN IF NOT EXISTS contextual_summary TEXT;

-- Step 3: Create HNSW index for new embedding column
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_large_hnsw
ON document_chunks_docling
USING hnsw (embedding_large vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Step 4: Update semantic cache table for 2000-dim embeddings
ALTER TABLE semantic_cache_responses
ADD COLUMN IF NOT EXISTS query_embedding_large vector(2000);

-- Step 5: Create HNSW index for semantic cache large embeddings
CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding_large_hnsw
ON semantic_cache_responses
USING hnsw (query_embedding_large vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Verify setup
SELECT
    'document_chunks_docling' as table_name,
    COUNT(*) as total_rows,
    COUNT(embedding) as rows_with_small_embedding,
    COUNT(embedding_large) as rows_with_large_embedding
FROM document_chunks_docling
UNION ALL
SELECT
    'semantic_cache_responses' as table_name,
    COUNT(*) as total_rows,
    COUNT(query_embedding) as rows_with_small_embedding,
    COUNT(query_embedding_large) as rows_with_large_embedding
FROM semantic_cache_responses;
