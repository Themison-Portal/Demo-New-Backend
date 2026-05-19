-- Migration to add visit activities and actual_date tracking

-- 1. Add actual_date to patient_visits
ALTER TABLE patient_visits ADD COLUMN IF NOT EXISTS actual_date DATE;

-- 2. Create visit_activities table
CREATE TABLE IF NOT EXISTS visit_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visit_id UUID NOT NULL REFERENCES patient_visits(id) ON DELETE CASCADE,
    activity_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'completed', 'not_applicable'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Add Index for performance
CREATE INDEX IF NOT EXISTS idx_visit_activities_visit_id ON visit_activities(visit_id);

-- 4. Verify grants
GRANT ALL PRIVILEGES ON TABLE visit_activities TO postgres;
