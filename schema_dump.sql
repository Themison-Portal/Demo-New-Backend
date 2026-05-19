--
-- PostgreSQL database dump
--

\restrict Xb9G94SEVP6QuA1FRru6vpLykQDS39xNSophdXyj1RUF94mnS3UX1cIa5aSAQ7R

-- Dumped from database version 16.12 (Debian 16.12-1.pgdg12+1)
-- Dumped by pg_dump version 16.12 (Debian 16.12-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: document_type_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.document_type_enum AS ENUM (
    'protocol',
    'brochure',
    'consent_form',
    'report',
    'manual',
    'plan',
    'amendment',
    'icf',
    'case_report_form',
    'standard_operating_procedure',
    'other'
);


ALTER TYPE public.document_type_enum OWNER TO postgres;

--
-- Name: organization_member_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.organization_member_type AS ENUM (
    'admin',
    'staff'
);


ALTER TYPE public.organization_member_type OWNER TO postgres;

--
-- Name: patient_document_type_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.patient_document_type_enum AS ENUM (
    'medical_record',
    'lab_result',
    'imaging',
    'consent_form',
    'assessment',
    'questionnaire',
    'adverse_event_report',
    'medication_record',
    'visit_note',
    'discharge_summary',
    'other'
);


ALTER TYPE public.patient_document_type_enum OWNER TO postgres;

--
-- Name: permission_level; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.permission_level AS ENUM (
    'read',
    'edit',
    'admin'
);


ALTER TYPE public.permission_level OWNER TO postgres;

--
-- Name: userrole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'USER'
);


ALTER TYPE public.userrole OWNER TO postgres;

--
-- Name: visit_document_type_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.visit_document_type_enum AS ENUM (
    'visit_note',
    'lab_results',
    'blood_test',
    'vital_signs',
    'invoice',
    'billing_statement',
    'medication_log',
    'adverse_event_form',
    'assessment_form',
    'imaging_report',
    'procedure_note',
    'data_export',
    'consent_form',
    'insurance_document',
    'other'
);


ALTER TYPE public.visit_document_type_enum OWNER TO postgres;

--
-- Name: visit_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.visit_status_enum AS ENUM (
    'scheduled',
    'in_progress',
    'completed',
    'cancelled',
    'no_show',
    'rescheduled'
);


ALTER TYPE public.visit_status_enum OWNER TO postgres;

--
-- Name: visit_type_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.visit_type_enum AS ENUM (
    'screening',
    'baseline',
    'follow_up',
    'treatment',
    'assessment',
    'monitoring',
    'adverse_event',
    'unscheduled',
    'study_closeout',
    'withdrawal'
);


ALTER TYPE public.visit_type_enum OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_types (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    category text,
    description text,
    deleted_at timestamp with time zone
);


ALTER TABLE public.activity_types OWNER TO postgres;

--
-- Name: chat_document_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_document_links (
    chat_session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    created_at timestamp without time zone,
    usage_count integer,
    first_used_at timestamp without time zone,
    last_used_at timestamp without time zone
);


ALTER TABLE public.chat_document_links OWNER TO postgres;

--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    session_id uuid,
    content text,
    role character varying(50),
    document_chunk_ids character varying[],
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chat_messages_role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying, 'system'::character varying])::text[])))
);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_sessions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    title character varying(255),
    trial_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.chat_sessions OWNER TO postgres;

--
-- Name: document_chunks_docling; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document_chunks_docling (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    document_id uuid NOT NULL,
    content text NOT NULL,
    page_number integer NOT NULL,
    chunk_metadata jsonb,
    embedding public.vector(1536),
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig, content)) STORED,
    contextual_summary text,
    created_at timestamp with time zone DEFAULT now(),
    embedding_large public.vector(2000)
);


ALTER TABLE public.document_chunks_docling OWNER TO postgres;

--
-- Name: invitations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invitations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email text NOT NULL,
    name text NOT NULL,
    organization_id uuid NOT NULL,
    initial_role public.organization_member_type NOT NULL,
    status text DEFAULT 'pending'::text,
    invited_by uuid,
    invited_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone DEFAULT (now() + '7 days'::interval),
    accepted_at timestamp with time zone,
    CONSTRAINT invitations_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'accepted'::text, 'expired'::text, 'cancelled'::text])))
);


ALTER TABLE public.invitations OWNER TO postgres;

--
-- Name: members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.members (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    organization_id uuid NOT NULL,
    profile_id uuid NOT NULL,
    default_role public.organization_member_type NOT NULL,
    invited_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    onboarding_completed boolean DEFAULT false NOT NULL
);


ALTER TABLE public.members OWNER TO postgres;

--
-- Name: organizations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organizations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    created_by uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    onboarding_completed boolean DEFAULT false,
    support_enabled boolean DEFAULT false
);


ALTER TABLE public.organizations OWNER TO postgres;

--
-- Name: patient_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.patient_documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    document_name text NOT NULL,
    document_type public.patient_document_type_enum NOT NULL,
    document_url character varying NOT NULL,
    patient_id uuid,
    uploaded_by uuid,
    status text,
    file_size bigint,
    mime_type character varying,
    version integer DEFAULT 1,
    is_latest boolean DEFAULT true,
    description text,
    tags text[],
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT patient_documents_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'approved'::text, 'signed'::text, 'submitted'::text, 'active'::text, 'rejected'::text, 'archived'::text])))
);


ALTER TABLE public.patient_documents OWNER TO postgres;

--
-- Name: patient_visits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.patient_visits (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    patient_id uuid NOT NULL,
    trial_id uuid NOT NULL,
    doctor_id uuid NOT NULL,
    visit_date date NOT NULL,
    visit_time time without time zone,
    visit_type public.visit_type_enum DEFAULT 'follow_up'::public.visit_type_enum NOT NULL,
    status public.visit_status_enum DEFAULT 'scheduled'::public.visit_status_enum NOT NULL,
    duration_minutes integer,
    visit_number integer,
    notes text,
    next_visit_date date,
    location text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by uuid,
    cost_data jsonb DEFAULT '{}'::jsonb,
    actual_date date
);


ALTER TABLE public.patient_visits OWNER TO postgres;

--
-- Name: patients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.patients (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    patient_code text NOT NULL,
    organization_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    date_of_birth date,
    gender text,
    first_name text,
    last_name text,
    phone_number text,
    email text,
    street_address text,
    city text,
    state_province text,
    postal_code text,
    country text DEFAULT 'United States'::text,
    emergency_contact_name text,
    emergency_contact_phone text,
    emergency_contact_relationship text,
    height_cm numeric(5,2),
    weight_kg numeric(5,2),
    blood_type text,
    medical_history text,
    current_medications text,
    known_allergies text,
    primary_physician_name text,
    primary_physician_phone text,
    insurance_provider text,
    insurance_policy_number text,
    consent_signed boolean DEFAULT false,
    consent_date date,
    screening_notes text,
    is_active boolean DEFAULT true,
    CONSTRAINT patients_blood_type_check CHECK ((blood_type = ANY (ARRAY['A+'::text, 'A-'::text, 'B+'::text, 'B-'::text, 'AB+'::text, 'AB-'::text, 'O+'::text, 'O-'::text, 'unknown'::text]))),
    CONSTRAINT patients_gender_check CHECK ((gender = ANY (ARRAY['male'::text, 'female'::text, 'other'::text, 'prefer_not_to_say'::text])))
);


ALTER TABLE public.patients OWNER TO postgres;

--
-- Name: profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.profiles (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    first_name text,
    last_name text,
    email text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.profiles OWNER TO postgres;

--
-- Name: qa_repository; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.qa_repository (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    trial_id uuid NOT NULL,
    question text NOT NULL,
    answer text NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    tags text[],
    is_verified boolean DEFAULT false,
    source text,
    sources jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.qa_repository OWNER TO postgres;

--
-- Name: response_folders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.response_folders (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    org_id text NOT NULL,
    trial_id uuid,
    name text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    deleted_at timestamp without time zone
);


ALTER TABLE public.response_folders OWNER TO postgres;

--
-- Name: responses_archived; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.responses_archived (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    folder_id uuid NOT NULL,
    user_id uuid NOT NULL,
    org_id text NOT NULL,
    trial_id uuid,
    document_id uuid,
    title text NOT NULL,
    question text,
    answer text,
    raw_data text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    deleted_at timestamp without time zone
);


ALTER TABLE public.responses_archived OWNER TO postgres;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    description text,
    permission_level public.permission_level DEFAULT 'read'::public.permission_level NOT NULL,
    organization_id uuid NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: semantic_cache_responses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semantic_cache_responses (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    query_text text NOT NULL,
    query_embedding public.vector(1536) NOT NULL,
    document_id uuid NOT NULL,
    response_data jsonb NOT NULL,
    context_hash character varying(64),
    hit_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    last_accessed_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.semantic_cache_responses OWNER TO postgres;

--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    trial_id uuid NOT NULL,
    title text NOT NULL,
    description text,
    status text DEFAULT 'todo'::text NOT NULL,
    priority text,
    assigned_to uuid,
    due_date timestamp without time zone,
    patient_id uuid,
    visit_id uuid,
    activity_type_id uuid,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    deleted_at timestamp without time zone,
    category text,
    created_by uuid
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- Name: themison_admins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.themison_admins (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email text NOT NULL,
    name text,
    active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    created_by uuid
);


ALTER TABLE public.themison_admins OWNER TO postgres;

--
-- Name: trial_activity_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trial_activity_types (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    trial_id uuid,
    activity_id text NOT NULL,
    name text NOT NULL,
    category text,
    description text,
    is_custom boolean DEFAULT true,
    deleted_at timestamp with time zone
);


ALTER TABLE public.trial_activity_types OWNER TO postgres;

--
-- Name: trial_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trial_documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    document_name text NOT NULL,
    document_type public.document_type_enum NOT NULL,
    document_url character varying NOT NULL,
    trial_id uuid,
    uploaded_by uuid,
    status text,
    file_size bigint,
    mime_type character varying(255),
    version integer DEFAULT 1,
    amendment_number integer,
    is_latest boolean DEFAULT true,
    description text,
    tags text[],
    warning boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT trial_documents_status_check CHECK ((status = ANY (ARRAY['active'::text, 'archived'::text])))
);


ALTER TABLE public.trial_documents OWNER TO postgres;

--
-- Name: trial_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trial_members (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    trial_id uuid NOT NULL,
    member_id uuid NOT NULL,
    role_id uuid NOT NULL,
    start_date date DEFAULT CURRENT_DATE,
    end_date date,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    settings jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.trial_members OWNER TO postgres;

--
-- Name: trial_members_pending; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trial_members_pending (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    trial_id uuid NOT NULL,
    invitation_id uuid NOT NULL,
    role_id uuid NOT NULL,
    invited_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    notes text
);


ALTER TABLE public.trial_members_pending OWNER TO postgres;

--
-- Name: trial_patients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trial_patients (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    trial_id uuid NOT NULL,
    patient_id uuid NOT NULL,
    enrollment_date date DEFAULT CURRENT_DATE,
    status text DEFAULT 'enrolled'::text,
    randomization_code text,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    assigned_by uuid,
    cost_data jsonb DEFAULT '{}'::jsonb,
    patient_data jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT trial_patients_status_check CHECK ((status = ANY (ARRAY['enrolled'::text, 'completed'::text, 'withdrawn'::text, 'screening'::text])))
);


ALTER TABLE public.trial_patients OWNER TO postgres;

--
-- Name: trials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trials (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    description text,
    phase text NOT NULL,
    location text NOT NULL,
    sponsor text NOT NULL,
    status text DEFAULT 'planning'::text,
    image_url text,
    study_start text,
    estimated_close_out text,
    organization_id uuid NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    budget_data jsonb DEFAULT '{}'::jsonb,
    visit_schedule_template jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT trials_status_check CHECK ((status = ANY (ARRAY['planning'::text, 'active'::text, 'completed'::text, 'paused'::text, 'cancelled'::text])))
);


ALTER TABLE public.trials OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255),
    password text,
    role public.userrole,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: visit_activities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visit_activities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    visit_id uuid NOT NULL,
    activity_name text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.visit_activities OWNER TO postgres;

--
-- Name: visit_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visit_documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    visit_id uuid NOT NULL,
    document_name text NOT NULL,
    document_type public.visit_document_type_enum NOT NULL,
    file_type text,
    document_url character varying(500) NOT NULL,
    file_size bigint,
    mime_type character varying(100),
    version integer DEFAULT 1,
    is_latest boolean DEFAULT true,
    uploaded_by uuid,
    upload_date timestamp with time zone DEFAULT now(),
    description text,
    tags text[],
    amount numeric(10,2),
    currency character varying(3) DEFAULT 'USD'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.visit_documents OWNER TO postgres;

--
-- Name: activity_types activity_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_types
    ADD CONSTRAINT activity_types_pkey PRIMARY KEY (id);


--
-- Name: chat_document_links chat_document_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_document_links
    ADD CONSTRAINT chat_document_links_pkey PRIMARY KEY (chat_session_id, document_id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: document_chunks_docling document_chunks_docling_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks_docling
    ADD CONSTRAINT document_chunks_docling_pkey PRIMARY KEY (id);


--
-- Name: invitations invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_pkey PRIMARY KEY (id);


--
-- Name: members members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: patient_documents patient_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_pkey PRIMARY KEY (id);


--
-- Name: patient_visits patient_visits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_visits
    ADD CONSTRAINT patient_visits_pkey PRIMARY KEY (id);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (id);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);


--
-- Name: qa_repository qa_repository_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.qa_repository
    ADD CONSTRAINT qa_repository_pkey PRIMARY KEY (id);


--
-- Name: response_folders response_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_folders
    ADD CONSTRAINT response_folders_pkey PRIMARY KEY (id);


--
-- Name: responses_archived responses_archived_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.responses_archived
    ADD CONSTRAINT responses_archived_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: semantic_cache_responses semantic_cache_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_cache_responses
    ADD CONSTRAINT semantic_cache_responses_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: themison_admins themison_admins_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.themison_admins
    ADD CONSTRAINT themison_admins_email_key UNIQUE (email);


--
-- Name: themison_admins themison_admins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.themison_admins
    ADD CONSTRAINT themison_admins_pkey PRIMARY KEY (id);


--
-- Name: trial_activity_types trial_activity_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_activity_types
    ADD CONSTRAINT trial_activity_types_pkey PRIMARY KEY (id);


--
-- Name: trial_documents trial_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_documents
    ADD CONSTRAINT trial_documents_pkey PRIMARY KEY (id);


--
-- Name: trial_members_pending trial_members_pending_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members_pending
    ADD CONSTRAINT trial_members_pending_pkey PRIMARY KEY (id);


--
-- Name: trial_members trial_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members
    ADD CONSTRAINT trial_members_pkey PRIMARY KEY (id);


--
-- Name: trial_patients trial_patients_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_patients
    ADD CONSTRAINT trial_patients_pkey PRIMARY KEY (id);


--
-- Name: trials trials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: visit_activities visit_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visit_activities
    ADD CONSTRAINT visit_activities_pkey PRIMARY KEY (id);


--
-- Name: visit_documents visit_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visit_documents
    ADD CONSTRAINT visit_documents_pkey PRIMARY KEY (id);


--
-- Name: idx_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_session_id ON public.chat_messages USING btree (session_id);


--
-- Name: idx_chat_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_sessions_user_id ON public.chat_sessions USING btree (user_id);


--
-- Name: idx_chunks_content_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_content_gin ON public.document_chunks_docling USING gin (content_tsv);


--
-- Name: idx_chunks_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_document_id ON public.document_chunks_docling USING btree (document_id);


--
-- Name: idx_chunks_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chunks_embedding_hnsw ON public.document_chunks_docling USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_members_organization; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_members_organization ON public.members USING btree (organization_id);


--
-- Name: idx_patient_visits_patient; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patient_visits_patient ON public.patient_visits USING btree (patient_id);


--
-- Name: idx_patient_visits_trial; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patient_visits_trial ON public.patient_visits USING btree (trial_id);


--
-- Name: idx_patients_organization; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_patients_organization ON public.patients USING btree (organization_id);


--
-- Name: idx_semantic_cache_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_cache_document_id ON public.semantic_cache_responses USING btree (document_id);


--
-- Name: idx_semantic_cache_embedding_hnsw; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_semantic_cache_embedding_hnsw ON public.semantic_cache_responses USING hnsw (query_embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_trial_documents_trial; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trial_documents_trial ON public.trial_documents USING btree (trial_id);


--
-- Name: idx_trial_patients_patient; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trial_patients_patient ON public.trial_patients USING btree (patient_id);


--
-- Name: idx_trial_patients_trial; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trial_patients_trial ON public.trial_patients USING btree (trial_id);


--
-- Name: idx_trials_organization; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trials_organization ON public.trials USING btree (organization_id);


--
-- Name: chat_document_links chat_document_links_chat_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_document_links
    ADD CONSTRAINT chat_document_links_chat_session_id_fkey FOREIGN KEY (chat_session_id) REFERENCES public.chat_sessions(id) ON DELETE CASCADE;


--
-- Name: chat_document_links chat_document_links_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_document_links
    ADD CONSTRAINT chat_document_links_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.trial_documents(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(id) ON DELETE CASCADE;


--
-- Name: chat_sessions chat_sessions_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE SET NULL;


--
-- Name: document_chunks_docling document_chunks_docling_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks_docling
    ADD CONSTRAINT document_chunks_docling_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.trial_documents(id) ON DELETE CASCADE;


--
-- Name: invitations invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: members members_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: members members_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.profiles(id) ON DELETE CASCADE;


--
-- Name: patient_documents patient_documents_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_documents
    ADD CONSTRAINT patient_documents_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE CASCADE;


--
-- Name: patient_visits patient_visits_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_visits
    ADD CONSTRAINT patient_visits_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.members(id) ON DELETE CASCADE;


--
-- Name: patient_visits patient_visits_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_visits
    ADD CONSTRAINT patient_visits_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE CASCADE;


--
-- Name: patient_visits patient_visits_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patient_visits
    ADD CONSTRAINT patient_visits_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE CASCADE;


--
-- Name: patients patients_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: qa_repository qa_repository_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.qa_repository
    ADD CONSTRAINT qa_repository_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE CASCADE;


--
-- Name: response_folders response_folders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.response_folders
    ADD CONSTRAINT response_folders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.members(id);


--
-- Name: responses_archived responses_archived_folder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.responses_archived
    ADD CONSTRAINT responses_archived_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES public.response_folders(id);


--
-- Name: responses_archived responses_archived_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.responses_archived
    ADD CONSTRAINT responses_archived_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.members(id);


--
-- Name: roles roles_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: semantic_cache_responses semantic_cache_responses_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semantic_cache_responses
    ADD CONSTRAINT semantic_cache_responses_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.trial_documents(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_activity_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_activity_type_id_fkey FOREIGN KEY (activity_type_id) REFERENCES public.activity_types(id);


--
-- Name: tasks tasks_assigned_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.members(id);


--
-- Name: tasks tasks_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.members(id);


--
-- Name: tasks tasks_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id);


--
-- Name: tasks tasks_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id);


--
-- Name: tasks tasks_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.patient_visits(id);


--
-- Name: trial_activity_types trial_activity_types_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_activity_types
    ADD CONSTRAINT trial_activity_types_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id);


--
-- Name: trial_documents trial_documents_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_documents
    ADD CONSTRAINT trial_documents_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE CASCADE;


--
-- Name: trial_members trial_members_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members
    ADD CONSTRAINT trial_members_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(id) ON DELETE CASCADE;


--
-- Name: trial_members_pending trial_members_pending_invitation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members_pending
    ADD CONSTRAINT trial_members_pending_invitation_id_fkey FOREIGN KEY (invitation_id) REFERENCES public.invitations(id) ON DELETE CASCADE;


--
-- Name: trial_members_pending trial_members_pending_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members_pending
    ADD CONSTRAINT trial_members_pending_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: trial_members_pending trial_members_pending_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members_pending
    ADD CONSTRAINT trial_members_pending_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE CASCADE;


--
-- Name: trial_members trial_members_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members
    ADD CONSTRAINT trial_members_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: trial_members trial_members_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_members
    ADD CONSTRAINT trial_members_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE CASCADE;


--
-- Name: trial_patients trial_patients_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_patients
    ADD CONSTRAINT trial_patients_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id) ON DELETE CASCADE;


--
-- Name: trial_patients trial_patients_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trial_patients
    ADD CONSTRAINT trial_patients_trial_id_fkey FOREIGN KEY (trial_id) REFERENCES public.trials(id) ON DELETE CASCADE;


--
-- Name: trials trials_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: visit_activities visit_activities_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visit_activities
    ADD CONSTRAINT visit_activities_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.patient_visits(id) ON DELETE CASCADE;


--
-- Name: visit_documents visit_documents_visit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visit_documents
    ADD CONSTRAINT visit_documents_visit_id_fkey FOREIGN KEY (visit_id) REFERENCES public.patient_visits(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Xb9G94SEVP6QuA1FRru6vpLykQDS39xNSophdXyj1RUF94mnS3UX1cIa5aSAQ7R

