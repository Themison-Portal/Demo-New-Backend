-- Database update script for local DB (Sylwester)
-- Date: 2026-04-16

-- 1. Ensure organization_member_type ENUM exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'organization_member_type') THEN
        CREATE TYPE organization_member_type AS ENUM ('admin', 'staff');
    END IF;
END$$;

-- 2. Update Invitations table
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS token TEXT;
-- Populate tokens if they are NULL
UPDATE invitations SET token = MD5(random()::text) WHERE token IS NULL;
ALTER TABLE invitations ALTER COLUMN token SET NOT NULL;

ALTER TABLE invitations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS invited_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMP WITH TIME ZONE;

-- 3. Update Profiles table
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 4. Update Members table
ALTER TABLE members ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 5. Update Trials table
ALTER TABLE trials ADD COLUMN IF NOT EXISTS visit_schedule_template JSONB DEFAULT '{}';
ALTER TABLE trials ADD COLUMN IF NOT EXISTS budget_data JSONB DEFAULT '{}';

-- 6. Update Patient Visits table
ALTER TABLE patient_visits ADD COLUMN IF NOT EXISTS cost_data JSONB DEFAULT '{}';

-- 7. Update Trial Members table
ALTER TABLE trial_members ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{}';

-- 8. Update Tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category TEXT;
