-- =====================================================
-- Themison Seed Data — Developer Test Setup
-- =====================================================
--
-- Run after init.sql to populate the minimum data needed
-- for testing the upload → ingest → query flow.
--
-- Usage:
--   docker exec -i themison-db psql -U postgres -d postgres < docker/seed.sql
--
-- Or add to docker-compose as a second init script:
--   volumes:
--     - ./docker/seed.sql:/docker-entrypoint-initdb.d/02-seed.sql
--
-- Prerequisites:
--   - AUTH_DISABLED=true in .env (bypasses Auth0 JWT, uses first member)
--   - UPLOAD_API_KEY set in .env (used as X-API-KEY header)
--
-- =====================================================

-- Use fixed UUIDs so they're easy to copy-paste into Swagger
-- and so this script is idempotent (re-runnable).

-- ===================
-- 1. ADMIN
-- ===================
INSERT INTO themison_admins (id, email, name, active, created_at)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@themison.com',
    'System Admin',
    TRUE,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- 2. ORGANIZATION
-- ===================
INSERT INTO organizations (id, name, created_by, onboarding_completed, created_at, updated_at)
VALUES (
    '10000000-0000-0000-0000-000000000001',
    'Themison Dev Org',
    '00000000-0000-0000-0000-000000000001',
    TRUE,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- 3. PROFILE (matches AUTH_DISABLED mock user email)
-- ===================
INSERT INTO profiles (id, email, first_name, last_name, created_at, updated_at)
VALUES (
    '20000000-0000-0000-0000-000000000001',
    'test@themison.com',
    'Test',
    'Developer',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- 4. MEMBER (links profile to organization)
-- ===================
INSERT INTO members (id, name, email, organization_id, profile_id, default_role, onboarding_completed, created_at, updated_at)
VALUES (
    '30000000-0000-0000-0000-000000000001',
    'Test Developer',
    'test@themison.com',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    'admin',
    TRUE,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- 5. ROLE (needed for trial_members)
-- ===================
INSERT INTO roles (id, name, description, permission_level, organization_id, created_by, created_at, updated_at)
VALUES (
    '40000000-0000-0000-0000-000000000001',
    'Admin',
    'Full access to trial',
    'admin',
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- 6. TRIAL
-- ===================
INSERT INTO trials (id, name, description, phase, location, sponsor, status, organization_id, created_by, created_at, updated_at)
VALUES (
    '50000000-0000-0000-0000-000000000001',
    'BEACON-1 Phase III Study',
    'A randomized, double-blind, placebo-controlled study evaluating the efficacy and safety of compound XR-42 in patients with moderate-to-severe condition.',
    'Phase III',
    'United States',
    'Themison Therapeutics',
    'active',
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- 7. TRIAL MEMBER (assign dev user to trial)
-- ===================
INSERT INTO trial_members (id, trial_id, member_id, role_id, is_active, created_at)
VALUES (
    '60000000-0000-0000-0000-000000000001',
    '50000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001',
    TRUE,
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- ===================
-- VERIFICATION
-- ===================
DO $$
DECLARE
    v_admin_count   INT;
    v_org_count     INT;
    v_profile_count INT;
    v_member_count  INT;
    v_trial_count   INT;
BEGIN
    SELECT COUNT(*) INTO v_admin_count   FROM themison_admins WHERE id = '00000000-0000-0000-0000-000000000001';
    SELECT COUNT(*) INTO v_org_count     FROM organizations   WHERE id = '10000000-0000-0000-0000-000000000001';
    SELECT COUNT(*) INTO v_profile_count FROM profiles        WHERE id = '20000000-0000-0000-0000-000000000001';
    SELECT COUNT(*) INTO v_member_count  FROM members         WHERE id = '30000000-0000-0000-0000-000000000001';
    SELECT COUNT(*) INTO v_trial_count   FROM trials          WHERE id = '50000000-0000-0000-0000-000000000001';

    RAISE NOTICE '';
    RAISE NOTICE '==========================================';
    RAISE NOTICE '  Themison Seed Data Loaded';
    RAISE NOTICE '==========================================';
    RAISE NOTICE '  Admin:        % (expected 1)', v_admin_count;
    RAISE NOTICE '  Organization: % (expected 1)', v_org_count;
    RAISE NOTICE '  Profile:      % (expected 1)', v_profile_count;
    RAISE NOTICE '  Member:       % (expected 1)', v_member_count;
    RAISE NOTICE '  Trial:        % (expected 1)', v_trial_count;
    RAISE NOTICE '==========================================';
    RAISE NOTICE '';
    RAISE NOTICE '  Trial ID (use in Swagger):';
    RAISE NOTICE '    50000000-0000-0000-0000-000000000001';
    RAISE NOTICE '';
    RAISE NOTICE '  Quick-start:';
    RAISE NOTICE '    1. POST /api/trial-documents/upload';
    RAISE NOTICE '       trial_id = 50000000-0000-0000-0000-000000000001';
    RAISE NOTICE '       (attach any PDF file)';
    RAISE NOTICE '    2. POST /upload/upload-pdf';
    RAISE NOTICE '       { document_url, document_id } from step 1';
    RAISE NOTICE '    3. GET  /upload/status/{job_id}';
    RAISE NOTICE '       (poll until status = completed)';
    RAISE NOTICE '    4. POST /query';
    RAISE NOTICE '       { query, document_id, document_name }';
    RAISE NOTICE '==========================================';
END $$;
