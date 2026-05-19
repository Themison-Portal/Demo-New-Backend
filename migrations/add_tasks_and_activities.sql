-- =====================================================
-- Migration: add tasks, activity_types, trial_activity_types
-- Safe to run against an existing database.
-- Uses CREATE TABLE IF NOT EXISTS so reruns are no-ops.
-- =====================================================

-- gen_random_uuid() is built into Postgres 13+; no extension required.

-- Activity Types (catalog of possible visit activities)
CREATE TABLE IF NOT EXISTS activity_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    deleted_at TIMESTAMPTZ
);

-- Trial Activity Types (per-trial customized activities)
CREATE TABLE IF NOT EXISTS trial_activity_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trial_id UUID REFERENCES trials(id),
    activity_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    is_custom BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMPTZ
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trial_id UUID NOT NULL REFERENCES trials(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT,
    assigned_to UUID REFERENCES members(id),
    due_date TIMESTAMP,
    patient_id UUID REFERENCES patients(id),
    visit_id UUID REFERENCES patient_visits(id),
    activity_type_id UUID REFERENCES activity_types(id),
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Verification
SELECT
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'activity_types')      AS activity_types_exists,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'trial_activity_types') AS trial_activity_types_exists,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'tasks')                AS tasks_exists;
