-- =====================================================
-- Migration: add ingestion_status to trial_documents
-- Plus a one-shot backfill: any document that already has
-- chunks in document_chunks_docling is marked 'ready'.
-- Safe to run multiple times (uses IF NOT EXISTS + guarded UPDATE).
-- =====================================================

ALTER TABLE trial_documents
  ADD COLUMN IF NOT EXISTS ingestion_status TEXT;

UPDATE trial_documents td
   SET ingestion_status = 'ready'
 WHERE ingestion_status IS NULL
   AND EXISTS (
       SELECT 1 FROM document_chunks_docling dcd
        WHERE dcd.document_id = td.id
   );

-- Verification
SELECT ingestion_status, COUNT(*) AS docs
  FROM trial_documents
 GROUP BY ingestion_status
 ORDER BY ingestion_status NULLS FIRST;
