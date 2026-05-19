-- =============================================================================
-- Seed data for testing: upload, upload-pdf, and query endpoints
-- Run: psql $SUPABASE_DB_URL -f migrations/seed_test_data.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Themison Admin (required by organizations.created_by FK)
-- ---------------------------------------------------------------------------
INSERT INTO themison_admins (id, email, name, active)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'admin@themison.com', 'Platform Admin', true)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Organization
-- ---------------------------------------------------------------------------
INSERT INTO organizations (id, name, created_by, onboarding_completed)
VALUES
  ('22222222-2222-2222-2222-222222222222', 'Acme Clinical Research', '11111111-1111-1111-1111-111111111111', true)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Profiles (auth lookup: email → profile → member)
-- ---------------------------------------------------------------------------
INSERT INTO profiles (id, first_name, last_name, email)
VALUES
  ('33333333-3333-3333-3333-333333333333', 'Test', 'User', 'test@themison.com'),
  ('33333333-3333-3333-3333-333333333334', 'Jane', 'Researcher', 'jane@themison.com')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Members (get_current_member returns first member when AUTH_DISABLED=true)
-- ---------------------------------------------------------------------------
INSERT INTO members (id, name, email, organization_id, profile_id, default_role, onboarding_completed)
VALUES
  ('44444444-4444-4444-4444-444444444444', 'Test User', 'test@themison.com',
   '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', 'admin', true),
  ('44444444-4444-4444-4444-444444444445', 'Jane Researcher', 'jane@themison.com',
   '22222222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333334', 'staff', true)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. Trials (needed for trial_id in upload endpoints)
-- ---------------------------------------------------------------------------
INSERT INTO trials (id, name, description, phase, location, sponsor, status, organization_id)
VALUES
  ('55555555-5555-5555-5555-555555555555', 'Oncology Phase III',
   'Randomized double-blind study of Drug X vs placebo in advanced NSCLC',
   'Phase 3', 'New York, USA', 'Acme Pharma', 'active',
   '22222222-2222-2222-2222-222222222222'),
  ('55555555-5555-5555-5555-555555555556', 'Cardiology Phase II',
   'Open-label study of Drug Y in heart failure patients',
   'Phase 2', 'London, UK', 'Acme Pharma', 'planning',
   '22222222-2222-2222-2222-222222222222'),
  ('55555555-5555-5555-5555-555555555557', 'Neurology Phase I',
   'First-in-human dose-escalation study of Drug Z',
   'Phase 1', 'Berlin, Germany', 'Acme Pharma', 'planning',
   '22222222-2222-2222-2222-222222222222')
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. Sample documents (for testing query and highlighted-pdf endpoints)
--    NOTE: upload and upload-pdf endpoints create their own records,
--    but these pre-existing docs let you test /query immediately.
-- ---------------------------------------------------------------------------
INSERT INTO trial_documents (id, document_name, document_type, document_url, trial_id, uploaded_by, status, file_size, mime_type, version, is_latest)
VALUES
  ('66666666-6666-6666-6666-666666666661', 'Study Protocol v1.0', 'protocol',
   'http://localhost:8000/local-files/trials/55555555-5555-5555-5555-555555555555/protocol_v1.pdf',
   '55555555-5555-5555-5555-555555555555', '44444444-4444-4444-4444-444444444444',
   'active', 524288, 'application/pdf', 1, true),
  ('66666666-6666-6666-6666-666666666662', 'Investigator Brochure', 'brochure',
   'http://localhost:8000/local-files/trials/55555555-5555-5555-5555-555555555555/brochure.pdf',
   '55555555-5555-5555-5555-555555555555', '44444444-4444-4444-4444-444444444444',
   'active', 1048576, 'application/pdf', 1, true),
  ('66666666-6666-6666-6666-666666666663', 'Informed Consent Form', 'icf',
   'http://localhost:8000/local-files/trials/55555555-5555-5555-5555-555555555556/icf.pdf',
   '55555555-5555-5555-5555-555555555556', '44444444-4444-4444-4444-444444444445',
   'active', 262144, 'application/pdf', 1, true)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 7. Chat session + messages (for testing chat history features)
-- ---------------------------------------------------------------------------
INSERT INTO chat_sessions (id, user_id, title, trial_id)
VALUES
  ('77777777-7777-7777-7777-777777777771', '44444444-4444-4444-4444-444444444444',
   'Questions about Protocol', '55555555-5555-5555-5555-555555555555')
ON CONFLICT (id) DO NOTHING;

INSERT INTO chat_messages (id, session_id, content, role)
VALUES
  ('88888888-8888-8888-8888-888888888881', '77777777-7777-7777-7777-777777777771',
   'What is the primary endpoint of this study?', 'user'),
  ('88888888-8888-8888-8888-888888888882', '77777777-7777-7777-7777-777777777771',
   'The primary endpoint is overall survival (OS) measured at 12 months.', 'assistant')
ON CONFLICT (id) DO NOTHING;

INSERT INTO chat_document_links (chat_session_id, document_id, usage_count)
VALUES
  ('77777777-7777-7777-7777-777777777771', '66666666-6666-6666-6666-666666666661', 1)
ON CONFLICT (chat_session_id, document_id) DO NOTHING;

COMMIT;

-- =============================================================================
-- Quick reference for testing:
--
-- POST /api/trial-documents/upload (Swagger/form upload):
--   trial_id: 55555555-5555-5555-5555-555555555555
--   document_type: protocol | brochure | icf | other | ...
--
-- POST /upload/upload-pdf (RAG ingestion, needs X-API-KEY header):
--   { "document_id": "66666666-6666-6666-6666-666666666661", "trial_id": "55555555-5555-5555-5555-555555555555" }
--
-- POST /query (RAG query, needs X-API-KEY header):
--   { "question": "What is the primary endpoint?", "document_id": "66666666-6666-6666-6666-666666666661" }
--
-- Available trial_ids:
--   55555555-5555-5555-5555-555555555555  (Oncology Phase III - active)
--   55555555-5555-5555-5555-555555555556  (Cardiology Phase II - planning)
--   55555555-5555-5555-5555-555555555557  (Neurology Phase I - planning)
-- =============================================================================
