ALTER TABLE patient_visits ADD COLUMN IF NOT EXISTS actual_date DATE;

CREATE TABLE IF NOT EXISTS visit_activities (
    id UUID PRIMARY KEY,
    visit_id UUID REFERENCES patient_visits(id) ON DELETE CASCADE,
    activity_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
