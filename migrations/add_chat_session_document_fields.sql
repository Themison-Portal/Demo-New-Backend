-- =====================================================
-- Migration: add document_id + document_name to chat_sessions
-- Safe to run against an existing database.
-- Uses ADD COLUMN IF NOT EXISTS so reruns are no-ops.
-- =====================================================

ALTER TABLE chat_sessions
  ADD COLUMN IF NOT EXISTS document_id UUID REFERENCES trial_documents(id);

ALTER TABLE chat_sessions
  ADD COLUMN IF NOT EXISTS document_name TEXT;

-- Verification
SELECT column_name
  FROM information_schema.columns
 WHERE table_name = 'chat_sessions'
   AND column_name IN ('document_id', 'document_name');
