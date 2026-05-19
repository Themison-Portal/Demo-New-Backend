-- Migration: Add full-text search for hybrid retrieval
-- Run with: psql $SUPABASE_DB_URL -f migrations/add_fulltext_search.sql

-- Step 1: Add tsvector column for full-text search
ALTER TABLE document_chunks_docling
ADD COLUMN IF NOT EXISTS content_tsv tsvector;

-- Step 2: Populate tsvector from existing content
UPDATE document_chunks_docling
SET content_tsv = to_tsvector('english', content)
WHERE content_tsv IS NULL;

-- Step 3: Create GIN index for fast full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_content_gin
ON document_chunks_docling USING GIN (content_tsv);

-- Step 4: Create trigger to auto-update tsvector on insert/update
CREATE OR REPLACE FUNCTION update_content_tsv()
RETURNS trigger AS $$
BEGIN
  NEW.content_tsv := to_tsvector('english', NEW.content);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists, then create
DROP TRIGGER IF EXISTS chunks_content_tsv_trigger ON document_chunks_docling;

CREATE TRIGGER chunks_content_tsv_trigger
BEFORE INSERT OR UPDATE OF content ON document_chunks_docling
FOR EACH ROW EXECUTE FUNCTION update_content_tsv();

-- Verify setup
SELECT
    COUNT(*) as total_chunks,
    COUNT(content_tsv) as chunks_with_tsv
FROM document_chunks_docling;
