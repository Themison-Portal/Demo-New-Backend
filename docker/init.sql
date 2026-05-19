-- =====================================================
-- Themison Database Schema - Docker Initialization
-- 22 Tables (2 RAG + 20 Business)
-- =====================================================

-- ===================
-- 1. EXTENSIONS
-- ===================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ===================
-- 2. ENUMS
-- ===================
CREATE TYPE organization_member_type AS ENUM ('admin', 'staff');

CREATE TYPE document_type_enum AS ENUM (
    'protocol', 'brochure', 'consent_form', 'report', 'manual',
    'plan', 'amendment', 'icf', 'case_report_form',
    'standard_operating_procedure', 'other'
);

CREATE TYPE patient_document_type_enum AS ENUM (
    'medical_record', 'lab_result', 'imaging', 'consent_form',
    'assessment', 'questionnaire', 'adverse_event_report',
    'medication_record', 'visit_note', 'discharge_summary', 'other'
);

CREATE TYPE permission_level AS ENUM ('read', 'edit', 'admin');

CREATE TYPE userrole AS ENUM ('ADMIN', 'USER');

CREATE TYPE visit_document_type_enum AS ENUM (
    'visit_note', 'lab_results', 'blood_test', 'vital_signs',
    'invoice', 'billing_statement', 'medication_log',
    'adverse_event_form', 'assessment_form', 'imaging_report',
    'procedure_note', 'data_export', 'consent_form',
    'insurance_document', 'other'
);

CREATE TYPE visit_status_enum AS ENUM (
    'scheduled', 'in_progress', 'completed',
    'cancelled', 'no_show', 'rescheduled'
);

CREATE TYPE visit_type_enum AS ENUM (
    'screening', 'baseline', 'follow_up', 'treatment',
    'assessment', 'monitoring', 'adverse_event',
    'unscheduled', 'study_closeout', 'withdrawal'
);

-- ===================
-- 3. CORE TABLES (no dependencies)
-- ===================

-- Profiles (linked to Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name TEXT,
    last_name TEXT,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (local user table)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255),
    password TEXT,
    role userrole,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    onboarding_completed BOOLEAN DEFAULT FALSE
);

-- Themison Admins (super admins)
CREATE TABLE IF NOT EXISTS themison_admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- ===================
-- 4. DEPENDENT TABLES (with FKs)
-- ===================

-- Members (organization members)
CREATE TABLE IF NOT EXISTS members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    default_role organization_member_type NOT NULL,
    invited_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    onboarding_completed BOOLEAN DEFAULT FALSE NOT NULL
);

-- Invitations
CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    initial_role organization_member_type NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'cancelled')),
    invited_by UUID,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    accepted_at TIMESTAMPTZ
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    permission_level permission_level DEFAULT 'read' NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trials
CREATE TABLE IF NOT EXISTS trials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    phase TEXT NOT NULL,
    location TEXT NOT NULL,
    sponsor TEXT NOT NULL,
    status TEXT DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'completed', 'paused', 'cancelled')),
    image_url TEXT,
    study_start TEXT,
    estimated_close_out TEXT,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    budget_data JSONB DEFAULT '{}'::jsonb
);

-- Trial Members
CREATE TABLE IF NOT EXISTS trial_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id UUID NOT NULL REFERENCES trials(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trial Members Pending
CREATE TABLE IF NOT EXISTS trial_members_pending (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id UUID NOT NULL REFERENCES trials(id) ON DELETE CASCADE,
    invitation_id UUID NOT NULL REFERENCES invitations(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    invited_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

-- Trial Documents
CREATE TABLE IF NOT EXISTS trial_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_name TEXT NOT NULL,
    document_type document_type_enum NOT NULL,
    document_url VARCHAR NOT NULL,
    trial_id UUID REFERENCES trials(id) ON DELETE CASCADE,
    uploaded_by UUID,
    status TEXT CHECK (status IN ('active', 'archived')),
    file_size BIGINT,
    mime_type VARCHAR(255),
    version INTEGER DEFAULT 1,
    amendment_number INTEGER,
    is_latest BOOLEAN DEFAULT TRUE,
    description TEXT,
    tags TEXT[],
    warning BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Patients
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_code TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    date_of_birth DATE,
    gender TEXT CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT,
    email TEXT,
    street_address TEXT,
    city TEXT,
    state_province TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'United States',
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    emergency_contact_relationship TEXT,
    height_cm NUMERIC(5,2),
    weight_kg NUMERIC(5,2),
    blood_type TEXT CHECK (blood_type IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'unknown')),
    medical_history TEXT,
    current_medications TEXT,
    known_allergies TEXT,
    primary_physician_name TEXT,
    primary_physician_phone TEXT,
    insurance_provider TEXT,
    insurance_policy_number TEXT,
    consent_signed BOOLEAN DEFAULT FALSE,
    consent_date DATE,
    screening_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Trial Patients (junction)
CREATE TABLE IF NOT EXISTS trial_patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id UUID NOT NULL REFERENCES trials(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    enrollment_date DATE DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'enrolled' CHECK (status IN ('enrolled', 'completed', 'withdrawn', 'screening')),
    randomization_code TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID,
    cost_data JSONB DEFAULT '{}'::jsonb,
    patient_data JSONB DEFAULT '{}'::jsonb
);

-- Patient Visits
CREATE TABLE IF NOT EXISTS patient_visits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    trial_id UUID NOT NULL REFERENCES trials(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    visit_date DATE NOT NULL,
    visit_time TIME,
    visit_type visit_type_enum DEFAULT 'follow_up' NOT NULL,
    status visit_status_enum DEFAULT 'scheduled' NOT NULL,
    duration_minutes INTEGER,
    visit_number INTEGER,
    notes TEXT,
    next_visit_date DATE,
    location TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    cost_data JSONB DEFAULT '{}'::jsonb
);

-- Patient Documents
CREATE TABLE IF NOT EXISTS patient_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_name TEXT NOT NULL,
    document_type patient_document_type_enum NOT NULL,
    document_url VARCHAR NOT NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    uploaded_by UUID,
    status TEXT CHECK (status IN ('pending', 'approved', 'signed', 'submitted', 'active', 'rejected', 'archived')),
    file_size BIGINT,
    mime_type VARCHAR,
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Visit Documents
CREATE TABLE IF NOT EXISTS visit_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visit_id UUID NOT NULL REFERENCES patient_visits(id) ON DELETE CASCADE,
    document_name TEXT NOT NULL,
    document_type visit_document_type_enum NOT NULL,
    file_type TEXT,
    document_url VARCHAR(500) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    uploaded_by UUID,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    description TEXT,
    tags TEXT[],
    amount NUMERIC(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- QA Repository
CREATE TABLE IF NOT EXISTS qa_repository (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id UUID NOT NULL REFERENCES trials(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    tags TEXT[],
    is_verified BOOLEAN DEFAULT FALSE,
    source TEXT,
    sources JSONB DEFAULT '[]'::jsonb
);

-- Chat Sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    title VARCHAR(255),
    trial_id UUID REFERENCES trials(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    content TEXT,
    role VARCHAR(50) CHECK (role IN ('user', 'assistant', 'system')),
    document_chunk_ids VARCHAR[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat Document Links (junction)
CREATE TABLE IF NOT EXISTS chat_document_links (
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES trial_documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP,
    usage_count INTEGER,
    first_used_at TIMESTAMP,
    last_used_at TIMESTAMP,
    PRIMARY KEY (chat_session_id, document_id)
);

-- Activity Types (catalog of possible visit activities)
CREATE TABLE IF NOT EXISTS activity_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    deleted_at TIMESTAMPTZ
);

-- Trial Activity Types (per-trial customized activities)
CREATE TABLE IF NOT EXISTS trial_activity_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- ===================
-- 5. RAG TABLES
-- ===================

-- Document Chunks (vector store)
CREATE TABLE IF NOT EXISTS document_chunks_docling (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES trial_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_metadata JSONB,
    embedding vector(1536),
    embedding_large vector(2000),
    content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    contextual_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Semantic Cache Responses
CREATE TABLE IF NOT EXISTS semantic_cache_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_embedding vector(1536) NOT NULL,
    document_id UUID NOT NULL REFERENCES trial_documents(id) ON DELETE CASCADE,
    response_data JSONB NOT NULL,
    context_hash VARCHAR(64),
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===================
-- 6. INDEXES
-- ===================

-- Vector search indexes (HNSW for fast ANN search)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON document_chunks_docling USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_large_hnsw
ON document_chunks_docling USING hnsw (embedding_large vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding_hnsw
ON semantic_cache_responses USING hnsw (query_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- BM25 full-text search index
CREATE INDEX IF NOT EXISTS idx_chunks_content_gin
ON document_chunks_docling USING GIN (content_tsv);

-- Foreign key indexes
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks_docling(document_id);
CREATE INDEX IF NOT EXISTS idx_semantic_cache_document_id ON semantic_cache_responses(document_id);

-- Chat indexes
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);

-- Business indexes
CREATE INDEX IF NOT EXISTS idx_members_organization ON members(organization_id);
CREATE INDEX IF NOT EXISTS idx_trials_organization ON trials(organization_id);
CREATE INDEX IF NOT EXISTS idx_trial_documents_trial ON trial_documents(trial_id);
CREATE INDEX IF NOT EXISTS idx_patients_organization ON patients(organization_id);
CREATE INDEX IF NOT EXISTS idx_trial_patients_trial ON trial_patients(trial_id);
CREATE INDEX IF NOT EXISTS idx_trial_patients_patient ON trial_patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_visits_patient ON patient_visits(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_visits_trial ON patient_visits(trial_id);

-- ===================
-- 7. GRANTS
-- ===================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ===================
-- 8. INITIALIZATION LOG
-- ===================
DO $$
BEGIN
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'Themison Database Initialized Successfully';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'Tables created: 22';
    RAISE NOTICE '  - RAG: document_chunks_docling, semantic_cache_responses';
    RAISE NOTICE '  - Business: 20 tables';
    RAISE NOTICE 'Extensions: uuid-ossp, vector';
    RAISE NOTICE 'Indexes: HNSW (vector), GIN (BM25)';
    RAISE NOTICE '==========================================';
END $$;
