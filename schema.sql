

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


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "public";






CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "extensions";






CREATE TYPE "public"."document_type_enum" AS ENUM (
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


ALTER TYPE "public"."document_type_enum" OWNER TO "postgres";


CREATE TYPE "public"."organization_member_type" AS ENUM (
    'admin',
    'staff'
);


ALTER TYPE "public"."organization_member_type" OWNER TO "postgres";


COMMENT ON TYPE "public"."organization_member_type" IS 'A member within the organization cna be "admin" or "staff"';



CREATE TYPE "public"."patient_document_type_enum" AS ENUM (
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


ALTER TYPE "public"."patient_document_type_enum" OWNER TO "postgres";


CREATE TYPE "public"."permission_level" AS ENUM (
    'read',
    'edit',
    'admin'
);


ALTER TYPE "public"."permission_level" OWNER TO "postgres";


CREATE TYPE "public"."userrole" AS ENUM (
    'ADMIN',
    'USER'
);


ALTER TYPE "public"."userrole" OWNER TO "postgres";


CREATE TYPE "public"."visit_document_type_enum" AS ENUM (
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


ALTER TYPE "public"."visit_document_type_enum" OWNER TO "postgres";


CREATE TYPE "public"."visit_status_enum" AS ENUM (
    'scheduled',
    'in_progress',
    'completed',
    'cancelled',
    'no_show',
    'rescheduled'
);


ALTER TYPE "public"."visit_status_enum" OWNER TO "postgres";


CREATE TYPE "public"."visit_type_enum" AS ENUM (
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


ALTER TYPE "public"."visit_type_enum" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_trial_with_members"("trial_data" "jsonb", "team_assignments" "jsonb"[]) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  new_trial_id UUID;
  user_org_id UUID;
BEGIN
  SELECT organization_id INTO user_org_id 
  FROM members WHERE profile_id = auth.uid() LIMIT 1;
  
  IF user_org_id IS NULL THEN
    RAISE EXCEPTION 'User is not a member of any organization';
  END IF;
  
  -- Crear trial
  INSERT INTO trials (
    name, description, phase, sponsor, location, study_start,
    estimated_close_out, organization_id, created_by, status
  )
  VALUES (
    trial_data->>'name', trial_data->>'description', trial_data->>'phase',
    trial_data->>'sponsor', trial_data->>'location',
    NULLIF(trial_data->>'study_start', '')::DATE,
    NULLIF(trial_data->>'estimated_close_out', '')::DATE,
    user_org_id, auth.uid(), 'planning'
  )
  RETURNING id INTO new_trial_id;
  
  -- INSERTAR CON DISTINCT PARA EVITAR DUPLICADOS
  INSERT INTO trial_members (trial_id, member_id, role_id, is_active, start_date)
  SELECT DISTINCT
    new_trial_id,
    COALESCE((assignment->>'member_id')::UUID, (assignment->>'memberId')::UUID),
    COALESCE((assignment->>'role_id')::UUID, (assignment->>'roleId')::UUID),
    COALESCE((assignment->>'is_active')::BOOLEAN, true),
    COALESCE((assignment->>'start_date')::DATE, CURRENT_DATE)
  FROM unnest(team_assignments) AS assignment
  WHERE COALESCE((assignment->>'member_id')::TEXT, (assignment->>'memberId')::TEXT) IS NOT NULL;
  
  RETURN new_trial_id;
END;
$$;


ALTER FUNCTION "public"."create_trial_with_members"("trial_data" "jsonb", "team_assignments" "jsonb"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_trial_with_members_debug"("trial_data" "jsonb", "team_assignments" "jsonb"[]) RETURNS TABLE("trial_id" "uuid", "debug_logs" "text"[])
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  new_trial_id UUID;
  assignment JSONB;
  user_org_id UUID;
  logs TEXT[] := '{}';
  assignment_count INT;
  inserted_count INT := 0;
  current_member_id UUID;
  current_role_id UUID;
  member_exists BOOLEAN;
  role_exists BOOLEAN;
BEGIN
  -- Log inicial
  logs := array_append(logs, '=== INICIO DEBUG CREATE_TRIAL_WITH_MEMBERS ===');
  logs := array_append(logs, 'Usuario autenticado: ' || COALESCE(auth.uid()::TEXT, 'NULL'));
  
  -- Obtener organization_id del usuario actual
  SELECT organization_id INTO user_org_id 
  FROM members 
  WHERE profile_id = auth.uid() 
  LIMIT 1;
  
  logs := array_append(logs, 'Organización del usuario: ' || COALESCE(user_org_id::TEXT, 'NULL'));
  
  IF user_org_id IS NULL THEN
    logs := array_append(logs, 'ERROR: Usuario no es miembro de ninguna organización');
    RETURN QUERY SELECT NULL::UUID, logs;
    RETURN;
  END IF;
  
  -- Log datos del trial
  logs := array_append(logs, '=== DATOS DEL TRIAL ===');
  logs := array_append(logs, 'Nombre: ' || COALESCE(trial_data->>'name', 'NULL'));
  logs := array_append(logs, 'Descripción: ' || COALESCE(trial_data->>'description', 'NULL'));
  
  -- Crear trial
  BEGIN
    INSERT INTO trials (
      name, 
      description, 
      phase, 
      sponsor, 
      location, 
      study_start,
      estimated_close_out,
      organization_id, 
      created_by,
      status
    )
    VALUES (
      trial_data->>'name',
      trial_data->>'description', 
      trial_data->>'phase',
      trial_data->>'sponsor',
      trial_data->>'location',
      NULLIF(trial_data->>'study_start', '')::DATE,
      NULLIF(trial_data->>'estimated_close_out', '')::DATE,
      user_org_id,
      auth.uid(),
      'planning'
    )
    RETURNING id INTO new_trial_id;
    
    logs := array_append(logs, '✅ Trial creado exitosamente. ID: ' || new_trial_id::TEXT);
  EXCEPTION
    WHEN OTHERS THEN
      logs := array_append(logs, '❌ ERROR creando trial: ' || SQLERRM);
      RETURN QUERY SELECT NULL::UUID, logs;
      RETURN;
  END;
  
  -- Analizar team_assignments
  assignment_count := array_length(team_assignments, 1);
  logs := array_append(logs, '=== ANÁLISIS TEAM ASSIGNMENTS ===');
  logs := array_append(logs, 'Array length: ' || COALESCE(assignment_count::TEXT, 'NULL'));
  
  IF assignment_count IS NULL OR assignment_count = 0 THEN
    logs := array_append(logs, '⚠️ No hay assignments para procesar');
    RETURN QUERY SELECT new_trial_id, logs;
    RETURN;
  END IF;
  
  -- Procesar cada assignment individualmente
  FOR i IN 1..assignment_count LOOP
    assignment := team_assignments[i];
    logs := array_append(logs, '--- Assignment ' || i || ' ---');
    logs := array_append(logs, 'Raw JSON: ' || assignment::TEXT);
    
    -- Extraer datos
    BEGIN
      current_member_id := (assignment->>'member_id')::UUID;
      current_role_id := (assignment->>'role_id')::UUID;
      
      logs := array_append(logs, 'Member ID: ' || COALESCE(current_member_id::TEXT, 'NULL'));
      logs := array_append(logs, 'Role ID: ' || COALESCE(current_role_id::TEXT, 'NULL'));
    EXCEPTION
      WHEN OTHERS THEN
        logs := array_append(logs, '❌ ERROR parseando IDs: ' || SQLERRM);
        CONTINUE;
    END;
    
    -- Verificar que el member existe y pertenece a la organización
    SELECT EXISTS(
      SELECT 1 FROM members 
      WHERE id = current_member_id 
      AND organization_id = user_org_id
    ) INTO member_exists;
    
    logs := array_append(logs, 'Member existe en org: ' || member_exists::TEXT);
    
    -- Verificar que el role existe y pertenece a la organización
    SELECT EXISTS(
      SELECT 1 FROM roles 
      WHERE id = current_role_id 
      AND organization_id = user_org_id
    ) INTO role_exists;
    
    logs := array_append(logs, 'Role existe en org: ' || role_exists::TEXT);
    
    -- Intentar insertar
    IF member_exists AND role_exists THEN
      BEGIN
        INSERT INTO trial_members (trial_id, member_id, role_id, is_active, start_date)
        VALUES (
          new_trial_id,
          current_member_id,
          current_role_id,
          COALESCE((assignment->>'is_active')::BOOLEAN, true),
          COALESCE((assignment->>'start_date')::DATE, CURRENT_DATE)
        );
        
        inserted_count := inserted_count + 1;
        logs := array_append(logs, '✅ Assignment ' || i || ' insertado exitosamente');
        
      EXCEPTION
        WHEN OTHERS THEN
          logs := array_append(logs, '❌ ERROR insertando assignment ' || i || ': ' || SQLERRM);
      END;
    ELSE
      logs := array_append(logs, '❌ Assignment ' || i || ' saltado - member o role no válido');
    END IF;
    
  END LOOP;
  
  logs := array_append(logs, '=== RESUMEN FINAL ===');
  logs := array_append(logs, 'Total assignments procesados: ' || assignment_count::TEXT);
  logs := array_append(logs, 'Total insertados exitosamente: ' || inserted_count::TEXT);
  logs := array_append(logs, '=== FIN DEBUG ===');
  
  RETURN QUERY SELECT new_trial_id, logs;
END;
$$;


ALTER FUNCTION "public"."create_trial_with_members_debug"("trial_data" "jsonb", "team_assignments" "jsonb"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_trial_with_members_extended"("trial_data" "jsonb", "confirmed_assignments" "jsonb"[] DEFAULT '{}'::"jsonb"[], "pending_assignments" "jsonb"[] DEFAULT '{}'::"jsonb"[]) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  new_trial_id UUID;
  user_org_id UUID;
  assignment JSONB;
BEGIN
  -- Obtener organization_id del usuario actual
  SELECT organization_id INTO user_org_id 
  FROM members 
  WHERE profile_id = auth.uid() 
  LIMIT 1;
  
  IF user_org_id IS NULL THEN
    RAISE EXCEPTION 'User is not a member of any organization';
  END IF;
  
  -- 1. Crear trial (igual que la función original)
  INSERT INTO trials (
    name, 
    description, 
    phase, 
    sponsor, 
    location, 
    study_start,
    estimated_close_out,
    organization_id, 
    created_by,
    status
  )
  VALUES (
    trial_data->>'name',
    trial_data->>'description', 
    trial_data->>'phase',
    trial_data->>'sponsor',
    trial_data->>'location',
    NULLIF(trial_data->>'study_start', '')::DATE,
    NULLIF(trial_data->>'estimated_close_out', '')::DATE,
    user_org_id,
    auth.uid(),
    'planning'
  )
  RETURNING id INTO new_trial_id;
  
  -- 2. Insertar members CONFIRMADOS (activos inmediatamente)
  IF array_length(confirmed_assignments, 1) > 0 THEN
    INSERT INTO trial_members (trial_id, member_id, role_id, is_active, start_date)
    SELECT DISTINCT
      new_trial_id,
      COALESCE((assignment->>'member_id')::UUID, (assignment->>'memberId')::UUID),
      COALESCE((assignment->>'role_id')::UUID, (assignment->>'roleId')::UUID),
      COALESCE((assignment->>'is_active')::BOOLEAN, true),
      COALESCE((assignment->>'start_date')::DATE, CURRENT_DATE)
    FROM unnest(confirmed_assignments) AS assignment
    WHERE COALESCE((assignment->>'member_id')::TEXT, (assignment->>'memberId')::TEXT) IS NOT NULL;
  END IF;
  
  -- 3. Insertar members PENDIENTES (se activarán cuando se registren)
  IF array_length(pending_assignments, 1) > 0 THEN
    INSERT INTO trial_members_pending (trial_id, invitation_id, role_id, invited_by, notes)
    SELECT DISTINCT
      new_trial_id,
      COALESCE((assignment->>'invitation_id')::UUID, (assignment->>'invitationId')::UUID),
      COALESCE((assignment->>'role_id')::UUID, (assignment->>'roleId')::UUID),
      COALESCE((assignment->>'invited_by')::UUID, (assignment->>'invitedBy')::UUID, auth.uid()),
      COALESCE(assignment->>'notes', 'Auto-assigned during trial creation')
    FROM unnest(pending_assignments) AS assignment
    WHERE COALESCE((assignment->>'invitation_id')::TEXT, (assignment->>'invitationId')::TEXT) IS NOT NULL;
  END IF;
  
  RETURN new_trial_id;
END;
$$;


ALTER FUNCTION "public"."create_trial_with_members_extended"("trial_data" "jsonb", "confirmed_assignments" "jsonb"[], "pending_assignments" "jsonb"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_trial_with_mixed_assignments"("trial_data" "jsonb", "team_assignments" "jsonb"[] DEFAULT '{}'::"jsonb"[]) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  new_trial_id UUID;
  user_org_id UUID;
  assignment_item JSONB;
BEGIN
  -- Obtener organization_id del usuario actual
  SELECT organization_id INTO user_org_id 
  FROM members 
  WHERE profile_id = auth.uid() 
  LIMIT 1;
  
  IF user_org_id IS NULL THEN
    RAISE EXCEPTION 'User is not a member of any organization';
  END IF;
  
  -- 1. Crear trial (como antes - fechas null son válidas)
  INSERT INTO trials (
    name, 
    description, 
    phase, 
    sponsor, 
    location, 
    study_start,
    estimated_close_out,
    organization_id, 
    created_by
  ) VALUES (
    trial_data->>'name',
    trial_data->>'description', 
    trial_data->>'phase',
    trial_data->>'sponsor',
    trial_data->>'location',
    (trial_data->>'study_start')::DATE,
    (trial_data->>'estimated_close_out')::DATE,
    user_org_id,
    auth.uid()
  ) RETURNING id INTO new_trial_id;
  
  -- 2. Procesar team assignments (detectar automáticamente confirmed vs pending)
  FOR assignment_item IN SELECT * FROM unnest(team_assignments)
  LOOP
    -- Si tiene member_id, es confirmed → trial_members
    IF assignment_item ? 'member_id' AND (assignment_item->>'member_id') IS NOT NULL AND (assignment_item->>'member_id') != '' THEN
      INSERT INTO trial_members (trial_id, member_id, role_id, is_active, start_date)
      VALUES (
        new_trial_id,
        (assignment_item->>'member_id')::UUID,
        (assignment_item->>'role_id')::UUID,
        COALESCE((assignment_item->>'is_active')::BOOLEAN, true),
        COALESCE((assignment_item->>'start_date')::DATE, CURRENT_DATE)
      );
    -- Si tiene invitation_id, es pending → trial_members_pending  
    ELSIF assignment_item ? 'invitation_id' AND (assignment_item->>'invitation_id') IS NOT NULL AND (assignment_item->>'invitation_id') != '' THEN
      INSERT INTO trial_members_pending (trial_id, invitation_id, role_id, invited_by)
      VALUES (
        new_trial_id,
        (assignment_item->>'invitation_id')::UUID,
        (assignment_item->>'role_id')::UUID,
        (SELECT id FROM members WHERE profile_id = auth.uid() LIMIT 1)
      );
    END IF;
  END LOOP;
  
  RETURN new_trial_id;
END;
$$;


ALTER FUNCTION "public"."create_trial_with_mixed_assignments"("trial_data" "jsonb", "team_assignments" "jsonb"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."debug_trial_creation"("org_id" "uuid", "user_profile_id" "uuid", "trial_data" "jsonb", "team_assignments" "jsonb"[]) RETURNS TABLE("trial_id" "uuid", "debug_logs" "text"[])
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  new_trial_id UUID;
  assignment JSONB;
  logs TEXT[] := '{}';
  assignment_count INT;
  inserted_count INT := 0;
  current_member_id UUID;
  current_role_id UUID;
  member_exists BOOLEAN;
  role_exists BOOLEAN;
BEGIN
  -- Log inicial
  logs := array_append(logs, '=== DEBUG TRIAL CREATION ===');
  logs := array_append(logs, 'Org ID: ' || org_id::TEXT);
  logs := array_append(logs, 'User Profile ID: ' || user_profile_id::TEXT);
  
  -- Analizar team_assignments
  assignment_count := array_length(team_assignments, 1);
  logs := array_append(logs, 'Team assignments count: ' || COALESCE(assignment_count::TEXT, 'NULL'));
  
  IF assignment_count IS NULL OR assignment_count = 0 THEN
    logs := array_append(logs, '⚠️ No hay assignments para procesar');
    RETURN QUERY SELECT NULL::UUID, logs;
    RETURN;
  END IF;
  
  -- Procesar cada assignment individualmente
  FOR i IN 1..assignment_count LOOP
    assignment := team_assignments[i];
    logs := array_append(logs, '--- Assignment ' || i || ' ---');
    logs := array_append(logs, 'Raw JSON: ' || assignment::TEXT);
    
    -- Extraer datos
    BEGIN
      current_member_id := (assignment->>'member_id')::UUID;
      current_role_id := (assignment->>'role_id')::UUID;
      
      logs := array_append(logs, 'Member ID: ' || COALESCE(current_member_id::TEXT, 'NULL'));
      logs := array_append(logs, 'Role ID: ' || COALESCE(current_role_id::TEXT, 'NULL'));
    EXCEPTION
      WHEN OTHERS THEN
        logs := array_append(logs, '❌ ERROR parseando IDs: ' || SQLERRM);
        CONTINUE;
    END;
    
    -- Verificar que el member existe y pertenece a la organización
    SELECT EXISTS(
      SELECT 1 FROM members 
      WHERE id = current_member_id 
      AND organization_id = org_id
    ) INTO member_exists;
    
    logs := array_append(logs, 'Member existe en org: ' || member_exists::TEXT);
    
    -- Verificar que el role existe y pertenece a la organización
    SELECT EXISTS(
      SELECT 1 FROM roles 
      WHERE id = current_role_id 
      AND organization_id = org_id
    ) INTO role_exists;
    
    logs := array_append(logs, 'Role existe en org: ' || role_exists::TEXT);
    
    -- Ver detalles del member
    IF member_exists THEN
      DECLARE
        member_name TEXT;
        member_email TEXT;
      BEGIN
        SELECT m.name, p.email INTO member_name, member_email
        FROM members m 
        JOIN profiles p ON m.profile_id = p.id 
        WHERE m.id = current_member_id;
        
        logs := array_append(logs, 'Member details: ' || member_name || ' (' || member_email || ')');
      END;
    END IF;
    
    -- Ver detalles del role
    IF role_exists THEN
      DECLARE
        role_name TEXT;
        role_permission TEXT;
      BEGIN
        SELECT name, permission_level INTO role_name, role_permission
        FROM roles 
        WHERE id = current_role_id;
        
        logs := array_append(logs, 'Role details: ' || role_name || ' (' || role_permission || ')');
      END;
    END IF;
    
    -- Simular inserción (sin hacerla realmente)
    IF member_exists AND role_exists THEN
      inserted_count := inserted_count + 1;
      logs := array_append(logs, '✅ Assignment ' || i || ' SERÍA insertado exitosamente');
    ELSE
      logs := array_append(logs, '❌ Assignment ' || i || ' FALLARÍA - member_exists=' || member_exists::TEXT || ', role_exists=' || role_exists::TEXT);
    END IF;
    
  END LOOP;
  
  logs := array_append(logs, '=== RESUMEN FINAL ===');
  logs := array_append(logs, 'Total assignments procesados: ' || assignment_count::TEXT);
  logs := array_append(logs, 'Total que se insertarían: ' || inserted_count::TEXT);
  logs := array_append(logs, '=== FIN DEBUG ===');
  
  RETURN QUERY SELECT NULL::UUID, logs;
END;
$$;


ALTER FUNCTION "public"."debug_trial_creation"("org_id" "uuid", "user_profile_id" "uuid", "trial_data" "jsonb", "team_assignments" "jsonb"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_organization_roles"("org_id" "uuid", "search_term" "text" DEFAULT ''::"text") RETURNS TABLE("id" "uuid", "name" "text", "description" "text", "permission_level" "public"."permission_level")
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        r.name,
        r.description,
        r.permission_level
    FROM roles r
    WHERE r.organization_id = org_id
    AND (search_term = '' OR r.name ILIKE '%' || search_term || '%')
    ORDER BY r.name;
END;
$$;


ALTER FUNCTION "public"."get_organization_roles"("org_id" "uuid", "search_term" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_trial_team"("trial_id_param" "uuid") RETURNS TABLE("member_id" "uuid", "member_name" "text", "member_email" "text", "role_name" "text", "permission_level" "public"."permission_level", "is_active" boolean, "start_date" "date")
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id as member_id,
        m.name as member_name,
        m.email as member_email,
        r.name as role_name,
        r.permission_level,
        tm.is_active,
        tm.start_date
    FROM trial_members tm
    JOIN members m ON tm.member_id = m.id
    JOIN roles r ON tm.role_id = r.id
    WHERE tm.trial_id = trial_id_param
    ORDER BY r.permission_level DESC, m.name;
END;
$$;


ALTER FUNCTION "public"."get_trial_team"("trial_id_param" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_user_organization_id"() RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    RETURN (
        SELECT m.organization_id
        FROM members m
        WHERE m.profile_id = auth.uid()
        LIMIT 1
    );
END;
$$;


ALTER FUNCTION "public"."get_user_organization_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_user_organization_id_for_trial_members"() RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    AS $$
BEGIN
    RETURN (
        SELECT m.organization_id
        FROM members m
        WHERE m.profile_id = auth.uid()
        LIMIT 1
    );
END;
$$;


ALTER FUNCTION "public"."get_user_organization_id_for_trial_members"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_email_confirmation"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
    -- Only proceed if email is confirmed (email_confirmed_at is set)
    IF NEW.email_confirmed_at IS NOT NULL AND (OLD.email_confirmed_at IS NULL OR OLD.email_confirmed_at != NEW.email_confirmed_at) THEN
        RAISE LOG 'User email confirmed for: %', NEW.email;
        
        -- Check if this user was invited (has invited_at field)
        IF NEW.invited_at IS NOT NULL THEN
            RAISE LOG 'User % was invited, skipping profile creation until signup completion', NEW.email;
            -- Don't create profile yet - wait for actual signup completion
            RETURN NEW;
        END IF;
        
        -- For non-invited users (normal signup), create profile immediately
        INSERT INTO public.profiles (
            id, email, first_name, last_name
        ) VALUES (
            NEW.id,
            NEW.email,
            NEW.raw_user_meta_data ->> 'first_name',
            NEW.raw_user_meta_data ->> 'last_name'
        ) ON CONFLICT (id) DO NOTHING;
        
        RAISE LOG 'Profile created for non-invited user: %', NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_email_confirmation"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_invited_user_signup"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
    -- Check if this is an invited user who just completed signup
    -- (password was updated and they have invited_at set)
    IF NEW.invited_at IS NOT NULL 
       AND NEW.encrypted_password IS NOT NULL 
       AND (OLD.encrypted_password IS NULL OR OLD.encrypted_password != NEW.encrypted_password)
       AND NEW.email_confirmed_at IS NOT NULL THEN
        
        RAISE LOG 'Invited user % completed signup, creating profile', NEW.email;
        
        -- Create profile - this will trigger the member creation
        INSERT INTO public.profiles (
            id, email, first_name, last_name
        ) VALUES (
            NEW.id,
            NEW.email,
            NEW.raw_user_meta_data ->> 'first_name',
            NEW.raw_user_meta_data ->> 'last_name'
        ) ON CONFLICT (id) DO NOTHING;
        
        RAISE LOG 'Profile created for invited user after signup completion: %', NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_invited_user_signup"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_new_profile"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    invitation_record record;
BEGIN
    RAISE LOG 'New profile created for email: %', NEW.email;
    
    -- Try to find a matching invitation
    SELECT * INTO invitation_record
    FROM public.invitations
    WHERE email = NEW.email 
    AND status = 'pending'
    AND (expires_at IS NULL OR expires_at > now())
    ORDER BY invited_at DESC
    LIMIT 1;
    
    IF FOUND THEN
        RAISE LOG 'Found matching invitation with ID: %', invitation_record.id;
        
        -- CAMBIO CRÍTICO: Update invitation status FIRST
        UPDATE public.invitations 
        SET status = 'accepted', accepted_at = now()
        WHERE id = invitation_record.id;
        
        RAISE LOG 'Updated invitation status to accepted for ID: %', invitation_record.id;
        
        -- DESPUÉS: Create member record (ahora handle_pending_trial_assignments encontrará invitation 'accepted')
        INSERT INTO public.members (
            name, email, organization_id, profile_id, 
            default_role, invited_by, created_at, onboarding_completed
        ) VALUES (
            invitation_record.name,
            invitation_record.email,
            invitation_record.organization_id,
            NEW.id,
            invitation_record.initial_role,
            invitation_record.invited_by,
            now(),
            false
        );
        
        RAISE LOG 'Created member record for profile: %', NEW.id;
    ELSE
        RAISE LOG 'No valid invitation found for email: %', NEW.email;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_new_profile"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_pending_trial_assignments"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    pending_assignment record;
BEGIN
    -- Only proceed if this is a new member creation (from invitation acceptance)
    IF TG_OP = 'INSERT' THEN
        RAISE LOG 'New member created, checking for pending trial assignments: %', NEW.email;
        
        -- Find all pending trial assignments for this email
        FOR pending_assignment IN
            SELECT tmp.*, i.email, i.organization_id
            FROM trial_members_pending tmp
            JOIN invitations i ON i.id = tmp.invitation_id
            WHERE i.email = NEW.email 
            AND i.organization_id = NEW.organization_id
            AND i.status = 'accepted'
        LOOP
            RAISE LOG 'Moving pending assignment to active for member: % in trial: %', NEW.id, pending_assignment.trial_id;
            
            -- Create active trial member record
            INSERT INTO trial_members (
                trial_id, member_id, role_id, 
                start_date, is_active, created_at
            ) VALUES (
                pending_assignment.trial_id,
                NEW.id,
                pending_assignment.role_id,
                CURRENT_DATE,
                true,
                now()
            ) ON CONFLICT DO NOTHING;
            
            -- Remove the pending assignment
            DELETE FROM trial_members_pending 
            WHERE id = pending_assignment.id;
            
            RAISE LOG 'Successfully activated trial assignment for member: %', NEW.id;
        END LOOP;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_pending_trial_assignments"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "text"[]) RETURNS TABLE("chunk_id" "uuid", "content" "text", "score" double precision)
    LANGUAGE "sql" STABLE
    AS $$
SELECT
  dc.id,
  dc.content,
  1 - (dc.embedding <=> query_embedding) AS score
FROM document_chunks dc
WHERE
  dc.document_id = ANY(document_ids::uuid[])
ORDER BY dc.embedding <=> query_embedding
LIMIT match_count;
$$;


ALTER FUNCTION "public"."hybrid_search"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "text"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search_UUID"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer DEFAULT 10, "document_ids" "uuid"[] DEFAULT NULL::"uuid"[]) RETURNS TABLE("id" "uuid", "document_id" "uuid", "content" "text", "chunk_metadata" "jsonb", "similarity" double precision, "rank" double precision, "combined_score" double precision)
    LANGUAGE "plpgsql"
    AS $$BEGIN
    RETURN QUERY
    WITH semantic_search AS (
        SELECT
            dc.id,
            dc.document_id,
            dc.content,
            dc.chunk_metadata,
            1 - (dc.embedding <=> query_embedding) as similarity,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank_number
        FROM document_chunks dc
        WHERE
            -- Filter out TOC chunks
            (dc.chunk_metadata->>'is_toc')::boolean IS DISTINCT FROM true
            AND (document_ids IS NULL OR dc.document_id = ANY(document_ids))
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 5
    ),
    fts_search AS (
        SELECT
            dc.id,
            dc.document_id,
            dc.content,
            dc.chunk_metadata,
            ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', query_text)) as rank,
            ROW_NUMBER() OVER (ORDER BY ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', query_text)) DESC) as rank_number
        FROM document_chunks dc
        WHERE
            -- Filter out TOC chunks
            (dc.chunk_metadata->>'is_toc')::boolean IS DISTINCT FROM true
            AND (document_ids IS NULL OR dc.document_id = ANY(document_ids))
            AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', query_text)
        ORDER BY rank DESC
        LIMIT match_count * 5
    ),
    combined AS (
        SELECT
            COALESCE(s.id, f.id) as id,
            COALESCE(s.document_id, f.document_id) as document_id,
            COALESCE(s.content, f.content) as content,
            COALESCE(s.chunk_metadata, f.chunk_metadata) as chunk_metadata,
            COALESCE(s.similarity, 0) as similarity,
            COALESCE(f.rank, 0) as rank,
            -- RRF (Reciprocal Rank Fusion) formula: 1 / (k + rank)
            (COALESCE(1.0 / (60 + s.rank_number), 0.0) +
             COALESCE(1.0 / (60 + f.rank_number), 0.0)) as combined_score
        FROM semantic_search s
        FULL OUTER JOIN fts_search f ON s.id = f.id
    )
    SELECT
        combined.id,
        combined.document_id,
        combined.content,
        combined.chunk_metadata,
        combined.similarity,
        combined.rank,
        combined.combined_score
    FROM combined
    ORDER BY combined.combined_score DESC
    LIMIT match_count;
END;$$;


ALTER FUNCTION "public"."hybrid_search_UUID"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "uuid"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search_by_document"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer DEFAULT 10) RETURNS TABLE("document_id" "uuid", "document_name" "text", "document_type" "public"."document_type_enum", "combined_score" real, "similarity_score" real, "text_score" real, "chunk_count" integer, "chunks_content" "text")
    LANGUAGE "sql"
    AS $$
WITH full_text AS (
    SELECT
        dc.document_id,
        d.document_name,
        d.document_type,
        CAST(ts_rank_cd(to_tsvector('english', dc.content), websearch_to_tsquery(query_text)) AS REAL) as text_score,
        row_number() OVER (ORDER BY ts_rank_cd(to_tsvector('english', dc.content), websearch_to_tsquery(query_text)) DESC) as rank_ix
    FROM document_chunks dc
    JOIN trial_documents d ON dc.document_id = d.id
    WHERE to_tsvector('english', dc.content) @@ websearch_to_tsquery(query_text)
    ORDER BY rank_ix
    LIMIT match_count * 2
),
semantic AS (
    SELECT
        dc.document_id,
        d.document_name,
        d.document_type,
        CAST((1.0 - (dc.embedding <=> query_embedding)) AS REAL) as similarity_score,
        row_number() OVER (ORDER BY dc.embedding <=> query_embedding) as rank_ix
    FROM document_chunks dc
    JOIN trial_documents d ON dc.document_id = d.id
    WHERE dc.embedding IS NOT NULL
    ORDER BY rank_ix
    LIMIT match_count * 2
),
document_scores AS (
    SELECT
        COALESCE(ft.document_id, sem.document_id) as document_id,
        COALESCE(ft.document_name, sem.document_name) as document_name,
        COALESCE(ft.document_type, sem.document_type) as document_type,
        CAST((COALESCE(1.0 / (50 + ft.rank_ix), 0.0) + COALESCE(1.0 / (50 + sem.rank_ix), 0.0)) AS REAL) as combined_score,
        COALESCE(sem.similarity_score, 0.0) as similarity_score,
        COALESCE(ft.text_score, 0.0) as text_score
    FROM full_text ft
    FULL OUTER JOIN semantic sem ON ft.document_id = sem.document_id
    ORDER BY combined_score DESC
    LIMIT match_count
),
document_chunks_agg AS (
    SELECT
        ds.document_id,
        ds.document_name,
        ds.document_type,
        ds.combined_score,
        ds.similarity_score,
        ds.text_score,
        COUNT(dc.id) as chunk_count,
        STRING_AGG(
            '--- Chunk ' || dc.chunk_index || ' ---\n' || dc.content, 
            '\n\n'
        ) as chunks_content
    FROM document_scores ds
    JOIN document_chunks dc ON ds.document_id = dc.document_id
    GROUP BY ds.document_id, ds.document_name, ds.document_type, ds.combined_score, ds.similarity_score, ds.text_score
)
SELECT
    document_id,
    document_name,
    document_type,
    combined_score,
    similarity_score,
    text_score,
    chunk_count,
    chunks_content
FROM document_chunks_agg
ORDER BY combined_score DESC;
$$;


ALTER FUNCTION "public"."hybrid_search_by_document"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search_v1_backup"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer DEFAULT 10, "document_ids" "text"[] DEFAULT NULL::"text"[]) RETURNS TABLE("id" "uuid", "content" "text", "chunk_index" integer, "document_id" "uuid", "document_name" "text", "document_type" "public"."document_type_enum", "chunk_metadata" "jsonb", "combined_score" real, "similarity_score" real, "text_score" real)
    LANGUAGE "sql"
    AS $$WITH full_text AS (

SELECT

dc.id,

dc.content,

dc.chunk_index,

dc.document_id,

dc.chunk_metadata,

CAST(ts_rank_cd(to_tsvector('english', dc.content), websearch_to_tsquery(query_text)) AS REAL) as text_score,

row_number() OVER (ORDER BY ts_rank_cd(to_tsvector('english', dc.content), websearch_to_tsquery(query_text)) DESC) as rank_ix

FROM document_chunks dc

WHERE to_tsvector('english', dc.content) @@ websearch_to_tsquery(query_text)

AND (document_ids IS NULL OR dc.document_id::TEXT = ANY(document_ids))

ORDER BY rank_ix

LIMIT match_count * 2

),

semantic AS (

SELECT

dc.id,

dc.content,

dc.chunk_index,

dc.document_id,

dc.chunk_metadata,

CAST((1.0 - (dc.embedding <=> query_embedding)) AS REAL) as similarity_score,

row_number() OVER (ORDER BY dc.embedding <=> query_embedding) as rank_ix

FROM document_chunks dc

WHERE dc.embedding IS NOT NULL

AND (document_ids IS NULL OR dc.document_id::TEXT = ANY(document_ids))

ORDER BY rank_ix

LIMIT match_count * 2

),

combined_results AS (

SELECT

COALESCE(ft.id, sem.id) as id,

COALESCE(ft.content, sem.content) as content,

COALESCE(ft.chunk_index, sem.chunk_index) as chunk_index,

COALESCE(ft.document_id, sem.document_id) as document_id,

COALESCE(ft.chunk_metadata, sem.chunk_metadata) as chunk_metadata,

CAST((COALESCE(1.0 / (50 + ft.rank_ix), 0.0) + COALESCE(1.0 / (50 + sem.rank_ix), 0.0)) AS REAL) as combined_score,

COALESCE(sem.similarity_score, 0.0) as similarity_score,

COALESCE(ft.text_score, 0.0) as text_score

FROM full_text ft

FULL OUTER JOIN semantic sem ON ft.id = sem.id

ORDER BY combined_score DESC

LIMIT match_count

)

SELECT

cr.id,

cr.content,

cr.chunk_index,

cr.document_id,

COALESCE(d.document_name, 'Unknown Document') as document_name,

COALESCE(d.document_type, 'other'::document_type_enum) as document_type,

cr.chunk_metadata,

cr.combined_score,

cr.similarity_score,

cr.text_score

FROM combined_results cr

LEFT JOIN trial_documents d ON cr.document_id = d.id

ORDER BY cr.combined_score DESC;$$;


ALTER FUNCTION "public"."hybrid_search_v1_backup"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "text"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search_v2"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "uuid"[]) RETURNS TABLE("id" "uuid", "content" "text", "metadata" "jsonb", "semantic_score" double precision, "keyword_score" double precision)
    LANGUAGE "sql" STABLE
    AS $$
SELECT
    dc.id,
    dc.content,
    jsonb_build_object(
        'document_id', dc.document_id,                                           
        'chunk_index', dc.chunk_index  
    ) AS metadata,

    -- Semantic similarity
    1 - (dc.embedding <=> query_embedding) AS semantic_score,

    -- Keyword relevance (on-the-fly)
    ts_rank_cd(
        to_tsvector('english', dc.content),
        plainto_tsquery('english', query_text)
    ) AS keyword_score

FROM document_chunks dc
WHERE
    (document_ids IS NULL OR dc.document_id = ANY(document_ids))
    AND to_tsvector('english', dc.content)
        @@ plainto_tsquery('english', query_text)

ORDER BY
    semantic_score DESC
LIMIT match_count;
$$;


ALTER FUNCTION "public"."hybrid_search_v2"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "uuid"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."hybrid_search_v2_test"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer DEFAULT 10, "document_ids" "text"[] DEFAULT NULL::"text"[], "retrieval_multiplier" integer DEFAULT 5) RETURNS TABLE("id" "uuid", "content" "text", "chunk_index" integer, "document_id" "uuid", "document_name" "text", "document_type" "public"."document_type_enum", "chunk_metadata" "jsonb", "combined_score" real, "similarity_score" real, "text_score" real, "keyword_rank" integer, "semantic_rank" integer)
    LANGUAGE "sql"
    AS $$
  WITH full_text AS (
      SELECT
          dc.id,
          dc.content,
          dc.chunk_index,
          dc.document_id,
          dc.chunk_metadata,
          CAST(ts_rank_cd(
              to_tsvector('english', dc.content),
              websearch_to_tsquery(query_text)
          ) AS REAL) as text_score,
          row_number() OVER (
              ORDER BY ts_rank_cd(
                  to_tsvector('english', dc.content),
                  websearch_to_tsquery(query_text)
              ) DESC
          ) as rank_ix
      FROM document_chunks dc
      WHERE to_tsvector('english', dc.content) @@ websearch_to_tsquery(query_text)
      AND (document_ids IS NULL OR dc.document_id::TEXT = ANY(document_ids))
      ORDER BY rank_ix
      LIMIT match_count * retrieval_multiplier
  ),
  semantic AS (
      SELECT
          dc.id,
          dc.content,
          dc.chunk_index,
          dc.document_id,
          dc.chunk_metadata,
          CAST((1.0 - (dc.embedding <=> query_embedding)) AS REAL) as similarity_score,
          row_number() OVER (ORDER BY dc.embedding <=> query_embedding) as rank_ix
      FROM document_chunks dc
      WHERE dc.embedding IS NOT NULL
      AND (document_ids IS NULL OR dc.document_id::TEXT = ANY(document_ids))
      ORDER BY rank_ix
      LIMIT match_count * retrieval_multiplier
  ),
  combined_results AS (
      SELECT
          COALESCE(ft.id, sem.id) as id,
          COALESCE(ft.content, sem.content) as content,
          COALESCE(ft.chunk_index, sem.chunk_index) as chunk_index,
          COALESCE(ft.document_id, sem.document_id) as document_id,
          COALESCE(ft.chunk_metadata, sem.chunk_metadata) as chunk_metadata,
          CAST(
              (COALESCE(1.0 / (30 + ft.rank_ix), 0.0) * 0.6) +
              (COALESCE(1.0 / (30 + sem.rank_ix), 0.0) * 0.4)
          AS REAL) as combined_score,
          COALESCE(sem.similarity_score, 0.0) as similarity_score,
          COALESCE(ft.text_score, 0.0) as text_score,
          CAST(ft.rank_ix AS integer) as keyword_rank,
          CAST(sem.rank_ix AS integer) as semantic_rank
      FROM full_text ft
      FULL OUTER JOIN semantic sem ON ft.id = sem.id
      ORDER BY combined_score DESC
      LIMIT match_count * 2
  )
  SELECT
      cr.id,
      cr.content,
      cr.chunk_index,
      cr.document_id,
      COALESCE(d.document_name, 'Unknown Document') as document_name,
      COALESCE(d.document_type, 'other'::document_type_enum) as document_type,
      cr.chunk_metadata,
      cr.combined_score,
      cr.similarity_score,
      cr.text_score,
      cr.keyword_rank,
      cr.semantic_rank
  FROM combined_results cr
  LEFT JOIN trial_documents d ON cr.document_id = d.id
  ORDER BY cr.combined_score DESC;
  $$;


ALTER FUNCTION "public"."hybrid_search_v2_test"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer, "document_ids" "text"[], "retrieval_multiplier" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."is_themison_admin"() RETURNS boolean
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM themison_admins 
        WHERE email = auth.jwt() ->> 'email'
        AND active = true
    );
END;
$$;


ALTER FUNCTION "public"."is_themison_admin"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."kw_match_documents"("query_text" "text", "match_count" integer) RETURNS TABLE("id" bigint, "content" "text", "metadata" "jsonb", "similarity" real)
    LANGUAGE "plpgsql"
    AS $_$

begin
return query execute
format('select id, content, metadata, ts_rank(to_tsvector(content), plainto_tsquery($1)) as similarity
from documents
where to_tsvector(content) @@ plainto_tsquery($1)
order by similarity desc
limit $2')
using query_text, match_count;
end;
$_$;


ALTER FUNCTION "public"."kw_match_documents"("query_text" "text", "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mock_calculate_burn_rate"("trial_id" "uuid") RETURNS numeric
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    monthly_burn DECIMAL;
BEGIN
    SELECT (budget_data->>'burn_rate')::DECIMAL
    INTO monthly_burn
    FROM trials WHERE id = trial_id;

    RETURN COALESCE(monthly_burn, 0);
END;
$$;


ALTER FUNCTION "public"."mock_calculate_burn_rate"("trial_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mock_get_available_budget"("trial_id" "uuid") RETURNS numeric
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    total_budget DECIMAL;
    spent_to_date DECIMAL;
BEGIN
    SELECT
        (budget_data->>'total_budget')::DECIMAL,
        (budget_data->>'spent_to_date')::DECIMAL
    INTO total_budget, spent_to_date
    FROM trials WHERE id = trial_id;

    RETURN COALESCE(total_budget, 0) - COALESCE(spent_to_date, 0);
END;
$$;


ALTER FUNCTION "public"."mock_get_available_budget"("trial_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mock_get_patient_total_cost"("patient_id" "uuid", "trial_id" "uuid") RETURNS numeric
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    patient_costs DECIMAL;
    visit_costs DECIMAL;
BEGIN
    -- Costo base del paciente
    SELECT (cost_data->>'costs_to_date')::DECIMAL
    INTO patient_costs
    FROM trial_patients WHERE patient_id = patient_id AND trial_id = trial_id;

    -- Suma de costos de visitas
    SELECT COALESCE(SUM((cost_data->>'visit_cost')::DECIMAL), 0)
    INTO visit_costs
    FROM patient_visits WHERE patient_id = patient_id AND trial_id = trial_id;

    RETURN COALESCE(patient_costs, 0) + COALESCE(visit_costs, 0);
END;
$$;


ALTER FUNCTION "public"."mock_get_patient_total_cost"("patient_id" "uuid", "trial_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mock_populate_patient_costs"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    trial_phase TEXT;
    trial_name TEXT;
BEGIN
    -- Obtener datos del trial
    SELECT phase, name INTO trial_phase, trial_name FROM trials WHERE id = NEW.trial_id;

    -- Auto-generar cost data mock basado en phase
    NEW.cost_data = jsonb_build_object(
        'budget_allocated',
            CASE trial_phase
                WHEN 'Phase I' THEN 3000
                WHEN 'Phase II' THEN 5000
                WHEN 'Phase III' THEN 8000
                WHEN 'Phase IV' THEN 6000
                WHEN 'Observational' THEN 2000
                WHEN 'Registry' THEN 1500
                ELSE 2500
            END,
        'costs_to_date', FLOOR(RANDOM() * 500 + 100)::INTEGER, -- Mock 100-600
        'reimbursement_rate',
            CASE trial_phase
                WHEN 'Phase I' THEN 200
                WHEN 'Phase II' THEN 150
                WHEN 'Phase III' THEN 125
                ELSE 150
            END,
        'transport_allowance',
            CASE trial_phase
                WHEN 'Phase I' THEN 50
                WHEN 'Phase II' THEN 40
                WHEN 'Phase III' THEN 35
                ELSE 40
            END,
        'target_visits',
            CASE trial_phase
                WHEN 'Phase I' THEN 6
                WHEN 'Phase II' THEN 10
                WHEN 'Phase III' THEN 15
                WHEN 'Phase IV' THEN 12
                WHEN 'Observational' THEN 4
                ELSE 8
            END,
        'baseline_date', NEW.enrollment_date,
        'expected_completion', (NEW.enrollment_date + INTERVAL '12 months')::DATE,
        'compliance_target', 90, -- 90% target
        'trial_name', trial_name
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."mock_populate_patient_costs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mock_populate_trial_budget"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Auto-generar budget data mock basado en phase
    NEW.budget_data = jsonb_build_object(
        'total_budget',
            CASE NEW.phase
                WHEN 'Phase I' THEN 250000
                WHEN 'Phase II' THEN 500000
                WHEN 'Phase III' THEN 1000000
                WHEN 'Phase IV' THEN 750000
                WHEN 'Observational' THEN 150000
                WHEN 'Registry' THEN 100000
                ELSE 200000
            END,
        'sponsor_funding',
            CASE NEW.phase
                WHEN 'Phase I' THEN 200000
                WHEN 'Phase II' THEN 450000
                WHEN 'Phase III' THEN 900000
                WHEN 'Phase IV' THEN 700000
                ELSE 180000
            END,
        'spent_to_date', FLOOR(RANDOM() * 50000 + 5000)::INTEGER, -- Mock spent 5K-55K
        'categories', jsonb_build_object(
            'patient_costs',
                CASE NEW.phase
                    WHEN 'Phase I' THEN 100000
                    WHEN 'Phase II' THEN 200000
                    WHEN 'Phase III' THEN 400000
                    WHEN 'Phase IV' THEN 300000
                    ELSE 60000
                END,
            'staff_costs',
                CASE NEW.phase
                    WHEN 'Phase I' THEN 80000
                    WHEN 'Phase II' THEN 150000
                    WHEN 'Phase III' THEN 300000
                    ELSE 70000
                END,
            'procedures', 50000,
            'transport', 15000,
            'equipment', 25000,
            'regulatory', 10000
        ),
        'burn_rate',
            CASE NEW.phase
                WHEN 'Phase I' THEN 8000
                WHEN 'Phase II' THEN 15000
                WHEN 'Phase III' THEN 25000
                WHEN 'Phase IV' THEN 20000
                ELSE 5000
            END,
        'budget_start_date', NEW.created_at::DATE,
        'projected_end_date', (NEW.created_at::DATE + INTERVAL '18 months')::DATE
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."mock_populate_trial_budget"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."mock_populate_visit_costs"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      trial_phase TEXT;
      base_cost INTEGER;
      patient_transport_allowance INTEGER;
      taxi_cost INTEGER;
      public_transport_cost INTEGER;
      parking_cost INTEGER;
      meal_cost INTEGER;
  BEGIN
      -- Obtener datos del trial y paciente
      SELECT t.phase, (tp.cost_data->>'transport_allowance')::INTEGER
      INTO trial_phase, patient_transport_allowance
      FROM trials t
      JOIN trial_patients tp ON t.id = tp.trial_id
      WHERE tp.patient_id = NEW.patient_id AND tp.trial_id = NEW.trial_id;

      -- Base cost por tipo de visita
      base_cost := CASE NEW.visit_type
          WHEN 'screening' THEN 250
          WHEN 'baseline' THEN 300
          WHEN 'follow_up' THEN 180
          WHEN 'treatment' THEN 350
          WHEN 'assessment' THEN 200
          WHEN 'monitoring' THEN 160
          WHEN 'adverse_event' THEN 400
          WHEN 'unscheduled' THEN 350
          WHEN 'study_closeout' THEN 220
          WHEN 'withdrawal' THEN 100
          ELSE 150
      END;

      -- Multiplicador por phase
      base_cost := FLOOR(base_cost * CASE trial_phase
          WHEN 'Phase I' THEN 1.3
          WHEN 'Phase II' THEN 1.1
          WHEN 'Phase III' THEN 0.9
          WHEN 'Phase IV' THEN 1.0
          WHEN 'Observational' THEN 0.7
          WHEN 'Registry' THEN 0.6
          ELSE 1.0
      END);

      -- Generar costos de transporte detallados
      taxi_cost := FLOOR(RANDOM() * 20 + 5)::INTEGER; -- 5-25
      public_transport_cost := FLOOR(RANDOM() * 8 + 2)::INTEGER; -- 2-10
      parking_cost := FLOOR(RANDOM() * 10 + 2)::INTEGER; -- 2-12
      meal_cost := CASE NEW.visit_type
          WHEN 'screening' THEN FLOOR(RANDOM() * 15 + 10)::INTEGER -- 10-25
          WHEN 'baseline' THEN FLOOR(RANDOM() * 20 + 15)::INTEGER -- 15-35
          WHEN 'treatment' THEN FLOOR(RANDOM() * 25 + 20)::INTEGER -- 20-45
          ELSE FLOOR(RANDOM() * 12 + 8)::INTEGER -- 8-20
      END;

      NEW.cost_data = jsonb_build_object(
          'visit_cost', base_cost,
          'reimbursement_amount', COALESCE(patient_transport_allowance, 35),
          'transport_cost', taxi_cost + public_transport_cost + parking_cost,
          'transportation_details', jsonb_build_object(
              'taxi_rides', taxi_cost,
              'public_transport', public_transport_cost,
              'parking', parking_cost,
              'mileage_reimbursement', FLOOR(RANDOM() * 15 + 5)::INTEGER, -- 5-20
              'total_transport', taxi_cost + public_transport_cost + parking_cost
          ),
          'meal_allowance', meal_cost,
          'accommodation', CASE
              WHEN RANDOM() < 0.1 THEN FLOOR(RANDOM() * 80 + 50)::INTEGER -- 10% chance de accommodation
              ELSE 0
          END,
          'procedure_costs',
              CASE NEW.visit_type
                  WHEN 'screening' THEN FLOOR(RANDOM() * 300 + 100)::INTEGER
                  WHEN 'baseline' THEN FLOOR(RANDOM() * 400 + 150)::INTEGER
                  WHEN 'follow_up' THEN FLOOR(RANDOM() * 200 + 50)::INTEGER
                  WHEN 'adverse_event' THEN FLOOR(RANDOM() * 500 + 200)::INTEGER
                  ELSE FLOOR(RANDOM() * 150 + 25)::INTEGER
              END,
          'lab_costs',
              CASE NEW.visit_type
                  WHEN 'screening' THEN FLOOR(RANDOM() * 200 + 50)::INTEGER
                  WHEN 'baseline' THEN FLOOR(RANDOM() * 250 + 75)::INTEGER
                  WHEN 'follow_up' THEN FLOOR(RANDOM() * 150 + 25)::INTEGER
                  ELSE FLOOR(RANDOM() * 100 + 15)::INTEGER
              END,
          'staff_time_hours', ROUND((RANDOM() * 2.5 + 0.5)::NUMERIC, 1),
          'visit_type', NEW.visit_type,
          'visit_date', NEW.visit_date,
          'phase', trial_phase,
          'visit_month', TO_CHAR(NEW.visit_date, 'YYYY-MM'),
          'cost_breakdown', jsonb_build_object(
              'transportation', taxi_cost + public_transport_cost + parking_cost,
              'meals', meal_cost,
              'procedures', CASE NEW.visit_type
                  WHEN 'screening' THEN FLOOR(RANDOM() * 300 + 100)::INTEGER
                  WHEN 'baseline' THEN FLOOR(RANDOM() * 400 + 150)::INTEGER
                  ELSE FLOOR(RANDOM() * 150 + 50)::INTEGER
              END,
              'staff', FLOOR(base_cost * 0.3)::INTEGER
          )
      );
      RETURN NEW;
  END;
  $$;


ALTER FUNCTION "public"."mock_populate_visit_costs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."populate_patient_data"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      trial_phase TEXT;
      trial_name TEXT;
      patient_age INTEGER;
      target_visits INTEGER;
      visit_history JSONB := jsonb_build_array();
      i INTEGER;
      visit_date DATE;
      visit_status TEXT;
      visit_types TEXT[] := ARRAY['screening', 'baseline', 'follow_up', 'assessment'];
  BEGIN
      -- Obtener datos del trial
      SELECT phase, name INTO trial_phase, trial_name FROM trials WHERE id = NEW.trial_id;

      -- Calcular edad del paciente
      SELECT EXTRACT(YEAR FROM AGE(date_of_birth)) INTO patient_age
      FROM patients WHERE id = NEW.patient_id;

      -- Determinar número de visitas según fase
      target_visits := CASE trial_phase
          WHEN 'Phase I' THEN 8
          WHEN 'Phase II' THEN 12
          WHEN 'Phase III' THEN 18
          WHEN 'Phase IV' THEN 15
          WHEN 'Observational' THEN 6
          ELSE 10
      END;

      -- Generar historial de visitas mock para los últimos 6 meses
      FOR i IN 1..LEAST(3, target_visits) LOOP
          -- Generar fechas de visitas pasadas (últimos 3-6 meses)
          visit_date := (NEW.enrollment_date - INTERVAL '1 month' * (4 - i))::DATE;

          -- 85% completed, 10% missed, 5% cancelled
          IF RANDOM() < 0.85 THEN
              visit_status := 'completed';
          ELSIF RANDOM() < 0.95 THEN
              visit_status := 'missed';
          ELSE
              visit_status := 'cancelled';
          END IF;

          visit_history := visit_history || jsonb_build_object(
              'type', visit_types[((i-1) % array_length(visit_types, 1)) + 1],
              'date', visit_date::TEXT,
              'scheduled_date', visit_date::TEXT,
              'actual_date', CASE
                  WHEN visit_status = 'completed' THEN visit_date::TEXT
                  WHEN visit_status = 'missed' THEN NULL
                  ELSE NULL
              END,
              'status', visit_status,
              'visit_number', i,
              'month', TO_CHAR(visit_date, 'YYYY-MM'),
              'duration_minutes', CASE visit_status
                  WHEN 'completed' THEN FLOOR(RANDOM() * 90 + 30)::INTEGER
                  ELSE NULL
              END,
              'notes', CASE visit_status
                  WHEN 'completed' THEN 'Visit completed successfully'
                  WHEN 'missed' THEN 'Patient did not show up'
                  WHEN 'cancelled' THEN 'Cancelled due to scheduling conflict'
                  ELSE NULL
              END
          );
      END LOOP;

      -- Construir patient_data completo
      SELECT
          jsonb_build_object(
              'visits', jsonb_build_object(
                  'completed', (SELECT COUNT(*) FROM jsonb_array_elements(visit_history) AS vh WHERE vh->>'status' = 'completed'),
                  'scheduled', 1,
                  'missed', (SELECT COUNT(*) FROM jsonb_array_elements(visit_history) AS vh WHERE vh->>'status' = 'missed'),
                  'cancelled', (SELECT COUNT(*) FROM jsonb_array_elements(visit_history) AS vh WHERE vh->>'status' = 'cancelled'),
                  'remaining', target_visits - (SELECT COUNT(*) FROM jsonb_array_elements(visit_history)),
                  'total_target', target_visits,
                  'last_6_months', jsonb_build_object(
                      'scheduled', jsonb_array_length(visit_history),
                      'completed', (SELECT COUNT(*) FROM jsonb_array_elements(visit_history) AS vh WHERE vh->>'status' = 'completed'),
                      'missed', (SELECT COUNT(*) FROM jsonb_array_elements(visit_history) AS vh WHERE vh->>'status' = 'missed')
                  )
              ),
              'nextVisit', jsonb_build_object(
                  'type', 'Screening',
                  'date', (NEW.enrollment_date + INTERVAL '7 days')::TEXT,
                  'time', '10:00 AM',
                  'location', 'Main Clinical Site',
                  'visit_number', jsonb_array_length(visit_history) + 1,
                  'scheduled_date', (NEW.enrollment_date + INTERVAL '7 days')::TEXT
              ),
              'visitHistory', visit_history,
              'medical', jsonb_build_object(
                  'height', COALESCE(p.height_cm::TEXT || ' cm', 'Not recorded'),
                  'weight', COALESCE(p.weight_kg::TEXT || ' kg', 'Not recorded'),
                  'bmi', CASE
                      WHEN p.height_cm IS NOT NULL AND p.weight_kg IS NOT NULL
                      THEN ROUND((p.weight_kg / POWER(p.height_cm/100.0, 2))::NUMERIC, 1)::TEXT
                      ELSE 'Not calculated'
                  END,
                  'bloodType', COALESCE(p.blood_type, 'Unknown'),
                  'age', patient_age,
                  'gender', COALESCE(p.gender, 'not_specified'),
                  'conditions', CASE
                      WHEN p.medical_history IS NOT NULL AND p.medical_history != ''
                      THEN to_jsonb(string_to_array(p.medical_history, ','))
                      ELSE jsonb_build_array()
                  END,
                  'medications', CASE
                      WHEN p.current_medications IS NOT NULL AND p.current_medications != ''
                      THEN to_jsonb(string_to_array(p.current_medications, ','))
                      ELSE jsonb_build_array()
                  END,
                  'allergies', CASE
                      WHEN p.known_allergies IS NOT NULL AND p.known_allergies != ''
                      THEN to_jsonb(string_to_array(p.known_allergies, ','))
                      ELSE jsonb_build_array()
                  END,
                  'emergencyContact', jsonb_build_object(
                      'name', COALESCE(p.emergency_contact_name, 'Not provided'),
                      'phone', COALESCE(p.emergency_contact_phone, 'Not provided'),
                      'relationship', COALESCE(p.emergency_contact_relationship, 'Not specified')
                  )
              ),
              'compliance', jsonb_build_object(
                  'overallScore', FLOOR(RANDOM() * 30 + 70)::INTEGER,
                  'medicationAdherence', FLOOR(RANDOM() * 20 + 80)::INTEGER,
                  'visitAttendance', FLOOR(RANDOM() * 25 + 75)::INTEGER,
                  'questionnaires', FLOOR(RANDOM() * 35 + 65)::INTEGER,
                  'issues', jsonb_build_array(),
                  'lastUpdated', CURRENT_DATE::TEXT,
                  'visitAttendanceRate', CASE
                      WHEN jsonb_array_length(visit_history) > 0
                      THEN ROUND(((SELECT COUNT(*) FROM jsonb_array_elements(visit_history) AS vh WHERE vh->>'status' = 'completed')::NUMERIC / jsonb_array_length(visit_history)) * 100, 1)
                      ELSE 100
                  END
              ),
              'contact', jsonb_build_object(
                  'email', COALESCE(p.email, 'No email provided'),
                  'phone', COALESCE(p.phone_number, 'No phone provided'),
                  'address', jsonb_build_object(
                      'street', COALESCE(p.street_address, 'Not provided'),
                      'city', COALESCE(p.city, 'Not provided'),
                      'state', COALESCE(p.state_province, 'Not provided'),
                      'country', COALESCE(p.country, 'United States')
                  )
              ),
              'metadata', jsonb_build_object(
                  'lastUpdated', NOW()::TEXT,
                  'dataVersion', '2.0',
                  'autoGenerated', true,
                  'trial_phase', trial_phase,
                  'enrollment_date', NEW.enrollment_date::TEXT
              )
          )
      INTO NEW.patient_data
      FROM patients p
      WHERE p.id = NEW.patient_id;

      RETURN NEW;
  END;
  $$;


ALTER FUNCTION "public"."populate_patient_data"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."send_invitation_email_dynamic"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    request_id INTEGER;
BEGIN
    -- Generar un ID único para esta solicitud
    request_id := (RANDOM() * 1000000)::INTEGER;
    
    -- Llamar a la Edge Function
    PERFORM
        net.http_post(
            url := current_setting('app.settings.supabase_url', true) || '/functions/v1/send-invitation-dynamic',
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'Authorization', 'Bearer ' || current_setting('app.settings.supabase_service_role_key', true)
            ),
            body := jsonb_build_object(
                'user_email', NEW.email,
                'organization_name', NEW.organization_name,
                'invitation_id', NEW.id
            )
        );

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."send_invitation_email_dynamic"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."send_invitation_email_simple"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
    request_id bigint;
    payload jsonb;
    edge_function_url text;
    org_name text;
BEGIN
    -- Get organization name
    SELECT name INTO org_name FROM organizations WHERE id = NEW.organization_id;
    
    -- Edge Function URL
    edge_function_url := 'https://gpfyejxokywdkudkeywv.supabase.co/functions/v1/send-invitation-dynamic';
    
    -- Prepare payload with the correct format that edge function expects
    payload := jsonb_build_object(
        'user_email', NEW.email,
        'organization_name', COALESCE(org_name, 'Organization'),
        'invitation_id', NEW.id
    );
    
    -- Call Edge Function using pg_net
    SELECT net.http_post(
        url := edge_function_url,
        body := payload,
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwZnllanhva3l3ZGt1ZGtleXd2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA3MTU1ODQsImV4cCI6MjA2NjI5MTU4NH0.MvgGO6iVBqvn25oVptUHigaxVBTeezpR69wpEld3kLc'
        )
    ) INTO request_id;
    
    RAISE LOG 'Dynamic Invitation Edge Function called for: %, request_id: %', NEW.email, request_id;
    
    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG 'Error calling dynamic invitation Edge Function: %', SQLERRM;
        RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."send_invitation_email_simple"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."test_hybrid_search"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer DEFAULT 10) RETURNS TABLE("id" "uuid", "content" "text", "chunk_index" integer, "combined_score" real, "similarity_score" real, "text_score" real)
    LANGUAGE "sql"
    AS $$
WITH full_text AS (
    SELECT
        dc.id,
        dc.content,
        dc.chunk_index,
        CAST(ts_rank_cd(to_tsvector('english', dc.content), websearch_to_tsquery(query_text)) AS REAL) as text_score,
        row_number() OVER (ORDER BY ts_rank_cd(to_tsvector('english', dc.content), websearch_to_tsquery(query_text)) DESC) as rank_ix
    FROM document_chunks dc
    WHERE to_tsvector('english', dc.content) @@ websearch_to_tsquery(query_text)
    ORDER BY rank_ix
    LIMIT match_count * 2
),
semantic AS (
    SELECT
        dc.id,
        dc.content,
        dc.chunk_index,
        CAST((1.0 - (dc.embedding <=> query_embedding)) AS REAL) as similarity_score,
        row_number() OVER (ORDER BY dc.embedding <=> query_embedding) as rank_ix
    FROM document_chunks dc
    WHERE dc.embedding IS NOT NULL
    ORDER BY rank_ix
    LIMIT match_count * 2
)
SELECT
    COALESCE(ft.id, sem.id) as id,
    COALESCE(ft.content, sem.content) as content,
    COALESCE(ft.chunk_index, sem.chunk_index) as chunk_index,
    CAST((COALESCE(1.0 / (50 + ft.rank_ix), 0.0) + COALESCE(1.0 / (50 + sem.rank_ix), 0.0)) AS REAL) as combined_score,
    COALESCE(sem.similarity_score, 0.0) as similarity_score,
    COALESCE(ft.text_score, 0.0) as text_score
FROM full_text ft
FULL OUTER JOIN semantic sem ON ft.id = sem.id
ORDER BY combined_score DESC
LIMIT match_count;
$$;


ALTER FUNCTION "public"."test_hybrid_search"("query_text" "text", "query_embedding" "extensions"."vector", "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_qa_repository_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
  BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
  END;
  $$;


ALTER FUNCTION "public"."update_qa_repository_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."user_belongs_to_organization"() RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    AS $$
BEGIN
    RETURN (
        SELECT m.organization_id
        FROM members m
        WHERE m.profile_id = auth.uid()
        LIMIT 1
    );
END;
$$;


ALTER FUNCTION "public"."user_belongs_to_organization"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."user_can_access_trial"("trial_id_param" "uuid") RETURNS boolean
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM trials t
        JOIN members m ON t.organization_id = m.organization_id
        WHERE t.id = trial_id_param 
        AND m.profile_id = auth.uid()
    );
END;
$$;


ALTER FUNCTION "public"."user_can_access_trial"("trial_id_param" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."user_can_create_trials"("user_profile_id" "uuid") RETURNS boolean
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM members 
        WHERE profile_id = user_profile_id 
        AND default_role = 'admin'
    );
END;
$$;


ALTER FUNCTION "public"."user_can_create_trials"("user_profile_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."user_organization_status"("user_profile_id" "uuid") RETURNS TABLE("organization_id" "uuid", "organization_name" "text", "default_role" "text", "member_since" timestamp with time zone)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.id as organization_id,
        o.name as organization_name,
        m.default_role,
        m.created_at as member_since
    FROM members m
    JOIN organizations o ON m.organization_id = o.id
    WHERE m.profile_id = user_profile_id
    LIMIT 1;
END;
$$;


ALTER FUNCTION "public"."user_organization_status"("user_profile_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."user_trial_permission"("user_profile_id" "uuid", "trial_id_param" "uuid") RETURNS "public"."permission_level"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    max_permission permission_level := 'read';
BEGIN
    SELECT CASE 
        WHEN COUNT(*) = 0 THEN 'read'::permission_level
        ELSE MAX(r.permission_level::text)::permission_level
    END
    INTO max_permission
    FROM trial_members tm
    JOIN members m ON tm.member_id = m.id
    JOIN roles r ON tm.role_id = r.id
    WHERE m.profile_id = user_profile_id
    AND tm.trial_id = trial_id_param
    AND tm.is_active = true;
    
    RETURN max_permission;
END;
$$;


ALTER FUNCTION "public"."user_trial_permission"("user_profile_id" "uuid", "trial_id_param" "uuid") OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."chat_document_links" (
    "chat_session_id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "created_at" timestamp without time zone,
    "usage_count" integer,
    "first_used_at" timestamp without time zone,
    "last_used_at" timestamp without time zone
);


ALTER TABLE "public"."chat_document_links" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_messages" (
    "id" "uuid" NOT NULL,
    "session_id" "uuid",
    "content" "text",
    "role" character varying(50),
    "created_at" timestamp without time zone,
    "document_chunk_ids" character varying[]
);


ALTER TABLE "public"."chat_messages" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chat_sessions" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid",
    "title" character varying(255),
    "created_at" timestamp without time zone,
    "updated_at" timestamp without time zone,
    "trial_id" "uuid"
);


ALTER TABLE "public"."chat_sessions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_chunks" (
    "id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "content" "text" NOT NULL,
    "chunk_index" integer NOT NULL,
    "chunk_metadata" "jsonb",
    "embedding" "extensions"."vector"(1536),
    "created_at" timestamp without time zone
);


ALTER TABLE "public"."document_chunks" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_chunks_docling" (
    "id" "uuid" NOT NULL,
    "document_id" "uuid" NOT NULL,
    "content" "text" NOT NULL,
    "page_number" integer NOT NULL,
    "chunk_metadata" "jsonb",
    "embedding" "extensions"."vector"(1536),
    "created_at" timestamp without time zone
);


ALTER TABLE "public"."document_chunks_docling" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."documents" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "original_filename" character varying(255) NOT NULL,
    "storage_url" "text" NOT NULL,
    "file_size" integer,
    "processing_status" character varying(50),
    "metadata" "json",
    "chunks" "json",
    "content" "text",
    "total_pages" integer,
    "total_chunks" integer,
    "created_at" timestamp without time zone,
    "updated_at" timestamp without time zone
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."invitations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "token" "text" NOT NULL,
    "email" "text" NOT NULL,
    "name" "text" NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "initial_role" "public"."organization_member_type" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text",
    "invited_by" "uuid",
    "invited_at" timestamp with time zone DEFAULT "now"(),
    "expires_at" timestamp with time zone DEFAULT ("now"() + '7 days'::interval),
    "accepted_at" timestamp with time zone,
    CONSTRAINT "invitations_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'accepted'::"text", 'expired'::"text", 'cancelled'::"text"])))
);

CREATE UNIQUE INDEX IF NOT EXISTS "idx_invitations_token" ON "public"."invitations" ("token");


ALTER TABLE "public"."invitations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."members" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "email" "text" NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "profile_id" "uuid" NOT NULL,
    "default_role" "public"."organization_member_type" NOT NULL,
    "invited_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "onboarding_completed" boolean DEFAULT false NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL
);


ALTER TABLE "public"."members" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."organizations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "onboarding_completed" boolean DEFAULT false,
    "support_enabled" boolean DEFAULT true,
    "is_active" boolean DEFAULT true
);


ALTER TABLE "public"."organizations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."patient_documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT ("now"() AT TIME ZONE 'utc'::"text"),
    "document_name" "text" NOT NULL,
    "document_type" "public"."patient_document_type_enum" NOT NULL,
    "document_url" character varying NOT NULL,
    "patient_id" "uuid",
    "uploaded_by" "uuid",
    "status" "text",
    "file_size" bigint,
    "mime_type" character varying,
    "version" integer DEFAULT 1,
    "is_latest" boolean DEFAULT true,
    "description" "text",
    "tags" "text"[],
    CONSTRAINT "patient_documents_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'signed'::"text", 'submitted'::"text", 'active'::"text", 'rejected'::"text", 'archived'::"text"])))
);


ALTER TABLE "public"."patient_documents" OWNER TO "postgres";


COMMENT ON TABLE "public"."patient_documents" IS 'Document management for patients with versioning and approval workflow';



CREATE TABLE IF NOT EXISTS "public"."patient_visits" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "patient_id" "uuid" NOT NULL,
    "trial_id" "uuid" NOT NULL,
    "doctor_id" "uuid" NOT NULL,
    "visit_date" "date" NOT NULL,
    "visit_time" time without time zone,
    "visit_type" "public"."visit_type_enum" DEFAULT 'follow_up'::"public"."visit_type_enum" NOT NULL,
    "status" "public"."visit_status_enum" DEFAULT 'scheduled'::"public"."visit_status_enum" NOT NULL,
    "duration_minutes" integer,
    "visit_number" integer,
    "notes" "text",
    "next_visit_date" "date",
    "location" "text",
    "actual_date" "date",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "created_by" "uuid",
    "cost_data" "jsonb" DEFAULT '{}'::"jsonb"
);


ALTER TABLE "public"."patient_visits" OWNER TO "postgres";


COMMENT ON TABLE "public"."patient_visits" IS 'Tracks patient visits for clinical trials with scheduling and status information';



COMMENT ON COLUMN "public"."patient_visits"."visit_number" IS 'Sequential visit number for the patient within this specific trial';



CREATE TABLE IF NOT EXISTS "public"."patients" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "patient_code" "text" NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "date_of_birth" "date",
    "gender" "text",
    "first_name" "text",
    "last_name" "text",
    "phone_number" "text",
    "email" "text",
    "street_address" "text",
    "city" "text",
    "state_province" "text",
    "postal_code" "text",
    "country" "text" DEFAULT 'United States'::"text",
    "emergency_contact_name" "text",
    "emergency_contact_phone" "text",
    "emergency_contact_relationship" "text",
    "height_cm" numeric(5,2),
    "weight_kg" numeric(5,2),
    "blood_type" "text",
    "medical_history" "text",
    "current_medications" "text",
    "known_allergies" "text",
    "primary_physician_name" "text",
    "primary_physician_phone" "text",
    "insurance_provider" "text",
    "insurance_policy_number" "text",
    "consent_signed" boolean DEFAULT false,
    "consent_date" "date",
    "screening_notes" "text",
    "is_active" boolean DEFAULT true,
    CONSTRAINT "patients_blood_type_check" CHECK (("blood_type" = ANY (ARRAY['A+'::"text", 'A-'::"text", 'B+'::"text", 'B-'::"text", 'AB+'::"text", 'AB-'::"text", 'O+'::"text", 'O-'::"text", 'unknown'::"text"]))),
    CONSTRAINT "patients_gender_check" CHECK (("gender" = ANY (ARRAY['male'::"text", 'female'::"text", 'other'::"text", 'prefer_not_to_say'::"text"])))
);


ALTER TABLE "public"."patients" OWNER TO "postgres";


COMMENT ON COLUMN "public"."patients"."date_of_birth" IS 'Patient date of birth for age calculations and eligibility';



COMMENT ON COLUMN "public"."patients"."gender" IS 'Patient gender identity for trial demographics';



COMMENT ON COLUMN "public"."patients"."height_cm" IS 'Patient height in centimeters';



COMMENT ON COLUMN "public"."patients"."weight_kg" IS 'Patient weight in kilograms';



COMMENT ON COLUMN "public"."patients"."medical_history" IS 'Free-text field for comprehensive medical history';



COMMENT ON COLUMN "public"."patients"."current_medications" IS 'List of current medications and dosages';



COMMENT ON COLUMN "public"."patients"."known_allergies" IS 'Known drug and other allergies';



COMMENT ON COLUMN "public"."patients"."consent_signed" IS 'Whether patient has signed informed consent';



COMMENT ON COLUMN "public"."patients"."is_active" IS 'Indicates whether the patient is currently active in the system (true = active, false = inactive)';



CREATE TABLE IF NOT EXISTS "public"."trials" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "phase" "text" NOT NULL,
    "location" "text" NOT NULL,
    "sponsor" "text" NOT NULL,
    "status" "text" DEFAULT 'planning'::"text",
    "image_url" "text",
    "study_start" "text",
    "estimated_close_out" "text",
    "organization_id" "uuid" NOT NULL,
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "budget_data" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "trials_status_check" CHECK (("status" = ANY (ARRAY['planning'::"text", 'active'::"text", 'completed'::"text", 'paused'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "public"."trials" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."patient_visits_detailed" AS
 SELECT "pv"."id",
    "pv"."patient_id",
    "pv"."trial_id",
    "pv"."doctor_id",
    "pv"."visit_date",
    "pv"."visit_time",
    "pv"."visit_type",
    "pv"."status",
    "pv"."duration_minutes",
    "pv"."visit_number",
    "pv"."notes",
    "pv"."next_visit_date",
    "pv"."location",
    "pv"."created_at",
    "pv"."updated_at",
    "pv"."created_by",
    "p"."patient_code",
    "p"."first_name",
    "p"."last_name",
    "t"."name" AS "trial_name",
    "t"."phase" AS "trial_phase",
    "m"."name" AS "doctor_name",
    "m"."email" AS "doctor_email"
   FROM ((("public"."patient_visits" "pv"
     JOIN "public"."patients" "p" ON (("pv"."patient_id" = "p"."id")))
     JOIN "public"."trials" "t" ON (("pv"."trial_id" = "t"."id")))
     JOIN "public"."members" "m" ON (("pv"."doctor_id" = "m"."id")));


ALTER TABLE "public"."patient_visits_detailed" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."profiles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "first_name" "text",
    "last_name" "text",
    "email" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."profiles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."protocol_chunks" (
    "id" "uuid" NOT NULL,
    "embedding" "extensions"."vector"(1536),
    "content" "text" NOT NULL,
    "protocol_id" "uuid" NOT NULL,
    "page_number" integer,
    "paragraph_number" integer,
    "created_at" timestamp without time zone
);


ALTER TABLE "public"."protocol_chunks" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."protocol_chunks_biobert" (
    "id" "uuid" NOT NULL,
    "embedding" "extensions"."vector"(768),
    "content" "text" NOT NULL,
    "protocol_id" "uuid" NOT NULL,
    "page_number" integer,
    "paragraph_number" integer,
    "created_at" timestamp without time zone
);


ALTER TABLE "public"."protocol_chunks_biobert" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."protocols" (
    "id" "uuid" NOT NULL,
    "title" character varying NOT NULL
);


ALTER TABLE "public"."protocols" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."protocols_biobert" (
    "id" "uuid" NOT NULL,
    "title" character varying NOT NULL
);


ALTER TABLE "public"."protocols_biobert" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."qa_repository" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trial_id" "uuid" NOT NULL,
    "question" "text" NOT NULL,
    "answer" "text" NOT NULL,
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "tags" "text"[],
    "is_verified" boolean DEFAULT false,
    "source" "text",
    "sources" "jsonb" DEFAULT '[]'::"jsonb"
);


ALTER TABLE "public"."qa_repository" OWNER TO "postgres";


COMMENT ON COLUMN "public"."qa_repository"."sources" IS 'Array of source citations with section, page, content, and relevance information';



CREATE TABLE IF NOT EXISTS "public"."roles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "permission_level" "public"."permission_level" DEFAULT 'read'::"public"."permission_level" NOT NULL,
    "organization_id" "uuid" NOT NULL,
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."roles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."themison_admins" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "email" "text" NOT NULL,
    "name" "text",
    "active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "created_by" "uuid"
);


ALTER TABLE "public"."themison_admins" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trial_documents" (
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_name" "text" NOT NULL,
    "document_type" "public"."document_type_enum" NOT NULL,
    "document_url" character varying NOT NULL,
    "trial_id" "uuid",
    "updated_at" timestamp with time zone DEFAULT ("now"() AT TIME ZONE 'utc'::"text"),
    "uploaded_by" "uuid",
    "status" "text",
    "file_size" bigint,
    "mime_type" character varying(255),
    "version" integer DEFAULT 1,
    "amendment_number" integer,
    "is_latest" boolean DEFAULT true,
    "description" "text",
    "tags" "text"[],
    "warning" boolean,
    CONSTRAINT "trial_documents_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'archived'::"text"])))
);


ALTER TABLE "public"."trial_documents" OWNER TO "postgres";


COMMENT ON TABLE "public"."trial_documents" IS 'Document hub for every trial with versioning and approval workflow';



CREATE TABLE IF NOT EXISTS "public"."trial_members" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trial_id" "uuid" NOT NULL,
    "member_id" "uuid" NOT NULL,
    "role_id" "uuid" NOT NULL,
    "start_date" "date" DEFAULT CURRENT_DATE,
    "end_date" "date",
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."trial_members" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trial_members_pending" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trial_id" "uuid" NOT NULL,
    "invitation_id" "uuid" NOT NULL,
    "role_id" "uuid" NOT NULL,
    "invited_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "notes" "text"
);


ALTER TABLE "public"."trial_members_pending" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."trial_patients" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "trial_id" "uuid" NOT NULL,
    "patient_id" "uuid" NOT NULL,
    "enrollment_date" "date" DEFAULT CURRENT_DATE,
    "status" "text" DEFAULT 'enrolled'::"text",
    "randomization_code" "text",
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "assigned_by" "uuid",
    "cost_data" "jsonb" DEFAULT '{}'::"jsonb",
    "patient_data" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "trial_patients_status_check" CHECK (("status" = ANY (ARRAY['enrolled'::"text", 'completed'::"text", 'withdrawn'::"text", 'screening'::"text"])))
);


ALTER TABLE "public"."trial_patients" OWNER TO "postgres";


COMMENT ON COLUMN "public"."trial_patients"."assigned_by" IS 'References the member (doctor/staff) who assigned this patient to the trial';



CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" NOT NULL,
    "email" character varying(255),
    "password" "uuid",
    "role" "public"."userrole",
    "created_at" timestamp without time zone,
    "updated_at" timestamp without time zone
);


ALTER TABLE "public"."users" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."visit_documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "visit_id" "uuid" NOT NULL,
    "document_name" "text" NOT NULL,
    "document_type" "public"."visit_document_type_enum" NOT NULL,
    "file_type" "text",
    "document_url" character varying(500) NOT NULL,
    "file_size" bigint,
    "mime_type" character varying(100),
    "version" integer DEFAULT 1,
    "is_latest" boolean DEFAULT true,
    "uploaded_by" "uuid",
    "upload_date" timestamp with time zone DEFAULT "now"(),
    "description" "text",
    "tags" "text"[],
    "amount" numeric(10,2),
    "currency" character varying(3) DEFAULT 'USD'::character varying,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT ("now"() AT TIME ZONE 'utc'::"text")
);


ALTER TABLE "public"."visit_documents" OWNER TO "postgres";


COMMENT ON TABLE "public"."visit_documents" IS 'Documents associated with specific patient visits (notes, lab results, invoices, etc.)';



COMMENT ON COLUMN "public"."visit_documents"."file_type" IS 'File extension or format (PDF, CSV, XLSX, JPG, etc.)';



COMMENT ON COLUMN "public"."visit_documents"."amount" IS 'Monetary amount for financial documents like invoices';



COMMENT ON COLUMN "public"."visit_documents"."currency" IS 'Currency code for financial documents';



ALTER TABLE ONLY "public"."chat_document_links"
    ADD CONSTRAINT "chat_document_links_pkey" PRIMARY KEY ("chat_session_id", "document_id");



ALTER TABLE ONLY "public"."chat_messages"
    ADD CONSTRAINT "chat_messages_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chat_sessions"
    ADD CONSTRAINT "chat_sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_chunks_docling"
    ADD CONSTRAINT "document_chunks_docling_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."invitations"
    ADD CONSTRAINT "invitations_email_organization_id_key" UNIQUE ("email", "organization_id");



ALTER TABLE ONLY "public"."invitations"
    ADD CONSTRAINT "invitations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."members"
    ADD CONSTRAINT "members_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."patient_documents"
    ADD CONSTRAINT "patient_documents_document_name_key" UNIQUE ("document_name");



ALTER TABLE ONLY "public"."patient_documents"
    ADD CONSTRAINT "patient_documents_document_url_key" UNIQUE ("document_url");



ALTER TABLE ONLY "public"."patient_documents"
    ADD CONSTRAINT "patient_documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."patient_visits"
    ADD CONSTRAINT "patient_visits_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."patients"
    ADD CONSTRAINT "patients_patient_code_organization_id_key" UNIQUE ("patient_code", "organization_id");



ALTER TABLE ONLY "public"."patients"
    ADD CONSTRAINT "patients_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."protocol_chunks_biobert"
    ADD CONSTRAINT "protocol_chunks_biobert_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."protocol_chunks"
    ADD CONSTRAINT "protocol_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."protocols_biobert"
    ADD CONSTRAINT "protocols_biobert_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."protocols"
    ADD CONSTRAINT "protocols_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."qa_repository"
    ADD CONSTRAINT "qa_repository_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_name_organization_id_key" UNIQUE ("name", "organization_id");



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."themison_admins"
    ADD CONSTRAINT "themison_admins_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."themison_admins"
    ADD CONSTRAINT "themison_admins_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."trial_documents"
    ADD CONSTRAINT "trial_documents_document_name_key" UNIQUE ("document_name");



ALTER TABLE ONLY "public"."trial_documents"
    ADD CONSTRAINT "trial_documents_document_url_key" UNIQUE ("document_url");



ALTER TABLE ONLY "public"."trial_documents"
    ADD CONSTRAINT "trial_documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."trial_members_pending"
    ADD CONSTRAINT "trial_members_pending_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."trial_members_pending"
    ADD CONSTRAINT "trial_members_pending_trial_id_invitation_id_role_id_key" UNIQUE ("trial_id", "invitation_id", "role_id");



ALTER TABLE ONLY "public"."trial_members"
    ADD CONSTRAINT "trial_members_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."trial_members"
    ADD CONSTRAINT "trial_members_trial_id_member_id_role_id_key" UNIQUE ("trial_id", "member_id", "role_id");



ALTER TABLE ONLY "public"."trial_patients"
    ADD CONSTRAINT "trial_patients_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."trial_patients"
    ADD CONSTRAINT "trial_patients_trial_id_patient_id_key" UNIQUE ("trial_id", "patient_id");



ALTER TABLE ONLY "public"."trials"
    ADD CONSTRAINT "trials_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."visit_documents"
    ADD CONSTRAINT "visit_documents_document_url_key" UNIQUE ("document_url");



ALTER TABLE ONLY "public"."visit_documents"
    ADD CONSTRAINT "visit_documents_pkey" PRIMARY KEY ("id");



CREATE INDEX "document_chunks_docling_document_id_idx" ON "public"."document_chunks_docling" USING "btree" ("document_id");



CREATE INDEX "document_chunks_docling_embedding_idx" ON "public"."document_chunks_docling" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "document_chunks_docling_embedding_idx1" ON "public"."document_chunks_docling" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "document_chunks_docling_int4_idx" ON "public"."document_chunks_docling" USING "btree" (((("chunk_metadata" ->> 'page_start'::"text"))::integer));



CREATE INDEX "document_chunks_docling_to_tsvector_idx" ON "public"."document_chunks_docling" USING "gin" ("to_tsvector"('"english"'::"regconfig", "content"));



CREATE INDEX "idx_chat_sessions_trial_id" ON "public"."chat_sessions" USING "btree" ("trial_id");



CREATE INDEX "idx_chat_sessions_user_trial" ON "public"."chat_sessions" USING "btree" ("user_id", "trial_id");



CREATE INDEX "idx_chunks_document_id" ON "public"."document_chunks" USING "btree" ("document_id");



CREATE INDEX "idx_chunks_embedding_hnsw" ON "public"."document_chunks" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "idx_chunks_page_start" ON "public"."document_chunks" USING "btree" (((("chunk_metadata" ->> 'page_start'::"text"))::integer));



CREATE INDEX "idx_document_chunks_content_fts" ON "public"."document_chunks" USING "gin" ("to_tsvector"('"english"'::"regconfig", "content"));



CREATE INDEX "idx_document_chunks_embedding" ON "public"."document_chunks" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "idx_invitations_email" ON "public"."invitations" USING "btree" ("email");



CREATE INDEX "idx_invitations_organization" ON "public"."invitations" USING "btree" ("organization_id");



CREATE INDEX "idx_invitations_status" ON "public"."invitations" USING "btree" ("status");



CREATE INDEX "idx_members_default_role" ON "public"."members" USING "btree" ("default_role");



CREATE INDEX "idx_members_email" ON "public"."members" USING "btree" ("email");



CREATE INDEX "idx_members_organization" ON "public"."members" USING "btree" ("organization_id");



CREATE INDEX "idx_members_profile" ON "public"."members" USING "btree" ("profile_id");



CREATE INDEX "idx_organizations_created_by" ON "public"."organizations" USING "btree" ("created_by");



CREATE INDEX "idx_patient_documents_created_at" ON "public"."patient_documents" USING "btree" ("created_at");



CREATE INDEX "idx_patient_documents_document_type" ON "public"."patient_documents" USING "btree" ("document_type");



CREATE INDEX "idx_patient_documents_patient_id" ON "public"."patient_documents" USING "btree" ("patient_id");



CREATE INDEX "idx_patient_documents_status" ON "public"."patient_documents" USING "btree" ("status");



CREATE INDEX "idx_patient_documents_uploaded_by" ON "public"."patient_documents" USING "btree" ("uploaded_by");



CREATE INDEX "idx_patient_visits_cost_data" ON "public"."patient_visits" USING "gin" ("cost_data");



CREATE INDEX "idx_patient_visits_date" ON "public"."patient_visits" USING "btree" ("visit_date");



CREATE INDEX "idx_patient_visits_doctor_id" ON "public"."patient_visits" USING "btree" ("doctor_id");



CREATE INDEX "idx_patient_visits_patient_id" ON "public"."patient_visits" USING "btree" ("patient_id");



CREATE INDEX "idx_patient_visits_patient_trial" ON "public"."patient_visits" USING "btree" ("patient_id", "trial_id");



CREATE INDEX "idx_patient_visits_status" ON "public"."patient_visits" USING "btree" ("status");



CREATE INDEX "idx_patient_visits_trial_id" ON "public"."patient_visits" USING "btree" ("trial_id");



CREATE INDEX "idx_patient_visits_type" ON "public"."patient_visits" USING "btree" ("visit_type");



CREATE INDEX "idx_patients_city" ON "public"."patients" USING "btree" ("city");



CREATE INDEX "idx_patients_code" ON "public"."patients" USING "btree" ("patient_code");



CREATE INDEX "idx_patients_consent_signed" ON "public"."patients" USING "btree" ("consent_signed");



CREATE INDEX "idx_patients_date_of_birth" ON "public"."patients" USING "btree" ("date_of_birth");



CREATE INDEX "idx_patients_email" ON "public"."patients" USING "btree" ("email");



CREATE INDEX "idx_patients_gender" ON "public"."patients" USING "btree" ("gender");



CREATE INDEX "idx_patients_is_active" ON "public"."patients" USING "btree" ("is_active");



CREATE INDEX "idx_patients_organization" ON "public"."patients" USING "btree" ("organization_id");



CREATE INDEX "idx_profiles_email" ON "public"."profiles" USING "btree" ("email");



CREATE INDEX "idx_qa_repository_created_at" ON "public"."qa_repository" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_qa_repository_sources" ON "public"."qa_repository" USING "gin" ("sources");



CREATE INDEX "idx_qa_repository_trial_id" ON "public"."qa_repository" USING "btree" ("trial_id");



CREATE INDEX "idx_roles_organization" ON "public"."roles" USING "btree" ("organization_id");



CREATE INDEX "idx_roles_permission" ON "public"."roles" USING "btree" ("permission_level");



CREATE INDEX "idx_themison_admins_active" ON "public"."themison_admins" USING "btree" ("active");



CREATE INDEX "idx_themison_admins_email" ON "public"."themison_admins" USING "btree" ("email");



CREATE INDEX "idx_trial_documents_document_type" ON "public"."trial_documents" USING "btree" ("document_type");



CREATE INDEX "idx_trial_documents_is_latest" ON "public"."trial_documents" USING "btree" ("is_latest");



CREATE INDEX "idx_trial_documents_status" ON "public"."trial_documents" USING "btree" ("status");



CREATE INDEX "idx_trial_documents_trial_id" ON "public"."trial_documents" USING "btree" ("trial_id");



CREATE INDEX "idx_trial_documents_uploaded_by" ON "public"."trial_documents" USING "btree" ("uploaded_by");



CREATE INDEX "idx_trial_members_active" ON "public"."trial_members" USING "btree" ("is_active");



CREATE INDEX "idx_trial_members_member" ON "public"."trial_members" USING "btree" ("member_id");



CREATE INDEX "idx_trial_members_role" ON "public"."trial_members" USING "btree" ("role_id");



CREATE INDEX "idx_trial_members_trial" ON "public"."trial_members" USING "btree" ("trial_id");



CREATE INDEX "idx_trial_patients_assigned_by" ON "public"."trial_patients" USING "btree" ("assigned_by");



CREATE INDEX "idx_trial_patients_cost_data" ON "public"."trial_patients" USING "gin" ("cost_data");



CREATE INDEX "idx_trial_patients_patient" ON "public"."trial_patients" USING "btree" ("patient_id");



CREATE INDEX "idx_trial_patients_status" ON "public"."trial_patients" USING "btree" ("status");



CREATE INDEX "idx_trial_patients_trial" ON "public"."trial_patients" USING "btree" ("trial_id");



CREATE INDEX "idx_trials_budget_data" ON "public"."trials" USING "gin" ("budget_data");



CREATE INDEX "idx_trials_created_by" ON "public"."trials" USING "btree" ("created_by");



CREATE INDEX "idx_trials_organization" ON "public"."trials" USING "btree" ("organization_id");



CREATE INDEX "idx_trials_status" ON "public"."trials" USING "btree" ("status");



CREATE INDEX "idx_visit_documents_file_type" ON "public"."visit_documents" USING "btree" ("file_type");



CREATE INDEX "idx_visit_documents_latest" ON "public"."visit_documents" USING "btree" ("is_latest") WHERE ("is_latest" = true);



CREATE INDEX "idx_visit_documents_type" ON "public"."visit_documents" USING "btree" ("document_type");



CREATE INDEX "idx_visit_documents_visit_id" ON "public"."visit_documents" USING "btree" ("visit_id");



CREATE INDEX "ix_protocol_chunks_biobert_id" ON "public"."protocol_chunks_biobert" USING "btree" ("id");



CREATE INDEX "ix_protocol_chunks_id" ON "public"."protocol_chunks" USING "btree" ("id");



CREATE INDEX "ix_protocols_biobert_id" ON "public"."protocols_biobert" USING "btree" ("id");



CREATE INDEX "ix_protocols_id" ON "public"."protocols" USING "btree" ("id");



CREATE OR REPLACE TRIGGER "handle_new_profile_trigger" AFTER INSERT ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."handle_new_profile"();



CREATE OR REPLACE TRIGGER "handle_pending_trial_assignments_trigger" AFTER INSERT ON "public"."members" FOR EACH ROW EXECUTE FUNCTION "public"."handle_pending_trial_assignments"();



COMMENT ON TRIGGER "handle_pending_trial_assignments_trigger" ON "public"."members" IS 'Mueve automáticamente las asignaciones pendientes de trials a activas cuando se crea un nuevo member (signup completado)';



CREATE OR REPLACE TRIGGER "mock_populate_patient_costs_trigger" BEFORE INSERT ON "public"."trial_patients" FOR EACH ROW EXECUTE FUNCTION "public"."mock_populate_patient_costs"();



CREATE OR REPLACE TRIGGER "mock_trigger_populate_trial_budget" BEFORE INSERT ON "public"."trials" FOR EACH ROW EXECUTE FUNCTION "public"."mock_populate_trial_budget"();



CREATE OR REPLACE TRIGGER "mock_trigger_populate_visit_costs" BEFORE INSERT ON "public"."patient_visits" FOR EACH ROW EXECUTE FUNCTION "public"."mock_populate_visit_costs"();



CREATE OR REPLACE TRIGGER "populate_patient_data_trigger" BEFORE INSERT ON "public"."trial_patients" FOR EACH ROW EXECUTE FUNCTION "public"."populate_patient_data"();



CREATE OR REPLACE TRIGGER "qa_repository_updated_at" BEFORE UPDATE ON "public"."qa_repository" FOR EACH ROW EXECUTE FUNCTION "public"."update_qa_repository_updated_at"();



CREATE OR REPLACE TRIGGER "update_members_updated_at" BEFORE UPDATE ON "public"."members" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_organizations_updated_at" BEFORE UPDATE ON "public"."organizations" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_patient_visits_updated_at" BEFORE UPDATE ON "public"."patient_visits" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_patients_updated_at" BEFORE UPDATE ON "public"."patients" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_profiles_updated_at" BEFORE UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_roles_updated_at" BEFORE UPDATE ON "public"."roles" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_trial_patients_updated_at" BEFORE UPDATE ON "public"."trial_patients" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_trials_updated_at" BEFORE UPDATE ON "public"."trials" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_visit_documents_updated_at" BEFORE UPDATE ON "public"."visit_documents" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."chat_document_links"
    ADD CONSTRAINT "chat_document_links_chat_session_id_fkey" FOREIGN KEY ("chat_session_id") REFERENCES "public"."chat_sessions"("id");



ALTER TABLE ONLY "public"."chat_document_links"
    ADD CONSTRAINT "chat_document_links_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id");



ALTER TABLE ONLY "public"."chat_messages"
    ADD CONSTRAINT "chat_messages_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."chat_sessions"("id");



ALTER TABLE ONLY "public"."chat_sessions"
    ADD CONSTRAINT "chat_sessions_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."trial_documents"("id");



ALTER TABLE ONLY "public"."invitations"
    ADD CONSTRAINT "invitations_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");



ALTER TABLE ONLY "public"."members"
    ADD CONSTRAINT "members_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");



ALTER TABLE ONLY "public"."members"
    ADD CONSTRAINT "members_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "public"."profiles"("id");



ALTER TABLE ONLY "public"."organizations"
    ADD CONSTRAINT "organizations_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."themison_admins"("id");



ALTER TABLE ONLY "public"."patient_documents"
    ADD CONSTRAINT "patient_documents_patient_id_fkey" FOREIGN KEY ("patient_id") REFERENCES "public"."patients"("id");



ALTER TABLE ONLY "public"."patient_documents"
    ADD CONSTRAINT "patient_documents_uploaded_by_fkey" FOREIGN KEY ("uploaded_by") REFERENCES "public"."members"("id");



ALTER TABLE ONLY "public"."patient_visits"
    ADD CONSTRAINT "patient_enrolled_in_trial" FOREIGN KEY ("patient_id", "trial_id") REFERENCES "public"."trial_patients"("patient_id", "trial_id");



ALTER TABLE ONLY "public"."patient_visits"
    ADD CONSTRAINT "patient_visits_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."members"("id");



ALTER TABLE ONLY "public"."patient_visits"
    ADD CONSTRAINT "patient_visits_doctor_id_fkey" FOREIGN KEY ("doctor_id") REFERENCES "public"."members"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."patient_visits"
    ADD CONSTRAINT "patient_visits_patient_id_fkey" FOREIGN KEY ("patient_id") REFERENCES "public"."patients"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."patient_visits"
    ADD CONSTRAINT "patient_visits_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."patients"
    ADD CONSTRAINT "patients_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");



ALTER TABLE ONLY "public"."protocol_chunks_biobert"
    ADD CONSTRAINT "protocol_chunks_biobert_protocol_id_fkey" FOREIGN KEY ("protocol_id") REFERENCES "public"."protocols_biobert"("id");



ALTER TABLE ONLY "public"."protocol_chunks"
    ADD CONSTRAINT "protocol_chunks_protocol_id_fkey" FOREIGN KEY ("protocol_id") REFERENCES "public"."protocols"("id");



ALTER TABLE ONLY "public"."qa_repository"
    ADD CONSTRAINT "qa_repository_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."members"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."qa_repository"
    ADD CONSTRAINT "qa_repository_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."roles"
    ADD CONSTRAINT "roles_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");



ALTER TABLE ONLY "public"."trial_documents"
    ADD CONSTRAINT "trial_documents_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_documents"
    ADD CONSTRAINT "trial_documents_uploaded_by_fkey" FOREIGN KEY ("uploaded_by") REFERENCES "public"."members"("id");



ALTER TABLE ONLY "public"."trial_members"
    ADD CONSTRAINT "trial_members_member_id_fkey" FOREIGN KEY ("member_id") REFERENCES "public"."members"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_members_pending"
    ADD CONSTRAINT "trial_members_pending_invitation_id_fkey" FOREIGN KEY ("invitation_id") REFERENCES "public"."invitations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_members_pending"
    ADD CONSTRAINT "trial_members_pending_invited_by_fkey" FOREIGN KEY ("invited_by") REFERENCES "public"."members"("id");



ALTER TABLE ONLY "public"."trial_members_pending"
    ADD CONSTRAINT "trial_members_pending_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_members_pending"
    ADD CONSTRAINT "trial_members_pending_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_members"
    ADD CONSTRAINT "trial_members_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "public"."roles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_members"
    ADD CONSTRAINT "trial_members_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."trial_patients"
    ADD CONSTRAINT "trial_patients_assigned_by_fkey" FOREIGN KEY ("assigned_by") REFERENCES "public"."members"("id");



ALTER TABLE ONLY "public"."trial_patients"
    ADD CONSTRAINT "trial_patients_patient_id_fkey" FOREIGN KEY ("patient_id") REFERENCES "public"."patients"("id");



ALTER TABLE ONLY "public"."trial_patients"
    ADD CONSTRAINT "trial_patients_trial_id_fkey" FOREIGN KEY ("trial_id") REFERENCES "public"."trials"("id");



ALTER TABLE ONLY "public"."trials"
    ADD CONSTRAINT "trials_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "public"."organizations"("id");



ALTER TABLE ONLY "public"."visit_documents"
    ADD CONSTRAINT "visit_documents_uploaded_by_fkey" FOREIGN KEY ("uploaded_by") REFERENCES "public"."members"("id");



ALTER TABLE ONLY "public"."visit_documents"
    ADD CONSTRAINT "visit_documents_visit_id_fkey" FOREIGN KEY ("visit_id") REFERENCES "public"."patient_visits"("id") ON DELETE CASCADE;



CREATE POLICY "Admins can create invitations" ON "public"."invitations" FOR INSERT WITH CHECK ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "invitations"."organization_id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Admins can create roles" ON "public"."roles" FOR INSERT WITH CHECK ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "roles"."organization_id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Admins can create trials" ON "public"."trials" FOR INSERT WITH CHECK ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "trials"."organization_id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Admins can insert members" ON "public"."members" FOR INSERT WITH CHECK ((("organization_id" = "public"."get_user_organization_id"()) AND (("invited_by" IS NULL) OR (EXISTS ( SELECT 1
   FROM "public"."members" "members_1"
  WHERE (("members_1"."profile_id" = "auth"."uid"()) AND ("members_1"."organization_id" = "members_1"."organization_id") AND ("members_1"."default_role" = 'admin'::"public"."organization_member_type")))))));



CREATE POLICY "Admins can manage trial_members_pending in their organization" ON "public"."trial_members_pending" USING (("trial_id" IN ( SELECT "t"."id"
   FROM (("public"."trials" "t"
     JOIN "public"."members" "m" ON (("m"."organization_id" = "t"."organization_id")))
     JOIN "public"."profiles" "p" ON (("p"."id" = "m"."profile_id")))
  WHERE (("p"."id" = "auth"."uid"()) AND ("m"."default_role" = 'admin'::"public"."organization_member_type")))));



CREATE POLICY "Admins can update members" ON "public"."members" FOR UPDATE USING ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members" "members_1"
  WHERE (("members_1"."profile_id" = "auth"."uid"()) AND ("members_1"."organization_id" = "members_1"."organization_id") AND ("members_1"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Admins can update organization" ON "public"."organizations" FOR UPDATE USING ((("id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "members"."id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Admins can update roles" ON "public"."roles" FOR UPDATE USING ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "roles"."organization_id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Admins can view invitations" ON "public"."invitations" FOR SELECT USING ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "invitations"."organization_id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type"))))));



CREATE POLICY "Members can create QA in their trials" ON "public"."qa_repository" FOR INSERT WITH CHECK (("trial_id" IN ( SELECT "tm"."trial_id"
   FROM ("public"."trial_members" "tm"
     JOIN "public"."members" "m" ON (("tm"."member_id" = "m"."id")))
  WHERE ("m"."profile_id" = "auth"."uid"()))));



CREATE POLICY "Members can create patient documents" ON "public"."patient_documents" FOR INSERT WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."patients" "p"
     JOIN "public"."members" "m" ON (("m"."organization_id" = "p"."organization_id")))
  WHERE (("p"."id" = "patient_documents"."patient_id") AND ("p"."organization_id" = "public"."get_user_organization_id"()) AND ("m"."profile_id" = "auth"."uid"())))));



CREATE POLICY "Members can create patients" ON "public"."patients" FOR INSERT WITH CHECK ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "patients"."organization_id"))))));



CREATE POLICY "Members can delete organization patients" ON "public"."patients" FOR DELETE USING ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "patients"."organization_id"))))));



CREATE POLICY "Members can delete patient documents" ON "public"."patient_documents" FOR DELETE USING ((EXISTS ( SELECT 1
   FROM ("public"."patients" "p"
     JOIN "public"."members" "m" ON (("m"."organization_id" = "p"."organization_id")))
  WHERE (("p"."id" = "patient_documents"."patient_id") AND ("p"."organization_id" = "public"."get_user_organization_id"()) AND ("m"."profile_id" = "auth"."uid"())))));



CREATE POLICY "Members can update organization patients" ON "public"."patients" FOR UPDATE USING ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "patients"."organization_id")))))) WITH CHECK ((("organization_id" = "public"."get_user_organization_id"()) AND (EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "patients"."organization_id"))))));



CREATE POLICY "Members can update patient documents" ON "public"."patient_documents" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM ("public"."patients" "p"
     JOIN "public"."members" "m" ON (("m"."organization_id" = "p"."organization_id")))
  WHERE (("p"."id" = "patient_documents"."patient_id") AND ("p"."organization_id" = "public"."get_user_organization_id"()) AND ("m"."profile_id" = "auth"."uid"()))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."patients" "p"
     JOIN "public"."members" "m" ON (("m"."organization_id" = "p"."organization_id")))
  WHERE (("p"."id" = "patient_documents"."patient_id") AND ("p"."organization_id" = "public"."get_user_organization_id"()) AND ("m"."profile_id" = "auth"."uid"())))));



CREATE POLICY "Members can update their own QA" ON "public"."qa_repository" FOR UPDATE USING (("created_by" IN ( SELECT "members"."id"
   FROM "public"."members"
  WHERE ("members"."profile_id" = "auth"."uid"()))));



CREATE POLICY "Members can view QA from their trials" ON "public"."qa_repository" FOR SELECT USING (("trial_id" IN ( SELECT "tm"."trial_id"
   FROM ("public"."trial_members" "tm"
     JOIN "public"."members" "m" ON (("tm"."member_id" = "m"."id")))
  WHERE ("m"."profile_id" = "auth"."uid"()))));



CREATE POLICY "System can update invitations" ON "public"."invitations" FOR UPDATE USING (true);



CREATE POLICY "Themison admin full access invitations" ON "public"."invitations" USING ("public"."is_themison_admin"());



CREATE POLICY "Themison admin full access organizations" ON "public"."organizations" USING ("public"."is_themison_admin"());



CREATE POLICY "Themison admins can manage admin table" ON "public"."themison_admins" USING ("public"."is_themison_admin"());



CREATE POLICY "Themison admins can view admin table" ON "public"."themison_admins" FOR SELECT USING ("public"."is_themison_admin"());



CREATE POLICY "Trial admins can update trials" ON "public"."trials" FOR UPDATE USING ((("organization_id" = "public"."get_user_organization_id"()) AND ((EXISTS ( SELECT 1
   FROM "public"."members"
  WHERE (("members"."profile_id" = "auth"."uid"()) AND ("members"."organization_id" = "trials"."organization_id") AND ("members"."default_role" = 'admin'::"public"."organization_member_type")))) OR (EXISTS ( SELECT 1
   FROM (("public"."trial_members" "tm"
     JOIN "public"."members" "m" ON (("tm"."member_id" = "m"."id")))
     JOIN "public"."roles" "r" ON (("tm"."role_id" = "r"."id")))
  WHERE (("m"."profile_id" = "auth"."uid"()) AND ("tm"."trial_id" = "trials"."id") AND ("r"."permission_level" = 'admin'::"public"."permission_level") AND ("tm"."is_active" = true)))))));



CREATE POLICY "Trial editors can manage patients" ON "public"."trial_patients" USING ((EXISTS ( SELECT 1
   FROM ((("public"."trial_members" "tm"
     JOIN "public"."members" "m" ON (("tm"."member_id" = "m"."id")))
     JOIN "public"."roles" "r" ON (("tm"."role_id" = "r"."id")))
     JOIN "public"."trials" "t" ON (("tm"."trial_id" = "t"."id")))
  WHERE (("m"."profile_id" = "auth"."uid"()) AND ("tm"."trial_id" = "trial_patients"."trial_id") AND ("r"."permission_level" = ANY (ARRAY['edit'::"public"."permission_level", 'admin'::"public"."permission_level"])) AND ("tm"."is_active" = true)))));



CREATE POLICY "Trial members can delete QA from their trials" ON "public"."qa_repository" FOR DELETE USING (("trial_id" IN ( SELECT "tm"."trial_id"
   FROM ("public"."trial_members" "tm"
     JOIN "public"."members" "m" ON (("tm"."member_id" = "m"."id")))
  WHERE ("m"."profile_id" = "auth"."uid"()))));



CREATE POLICY "Users can access documents from their organization" ON "public"."trial_documents" USING (("trial_id" IN ( SELECT "t"."id"
   FROM (("public"."trials" "t"
     JOIN "public"."members" "m" ON (("t"."organization_id" = "m"."organization_id")))
     JOIN "public"."profiles" "p" ON (("m"."profile_id" = "p"."id")))
  WHERE ("p"."id" = "auth"."uid"()))));



CREATE POLICY "Users can insert own profile" ON "public"."profiles" FOR INSERT WITH CHECK (("id" = "auth"."uid"()));



CREATE POLICY "Users can manage documents in their organization" ON "public"."trial_documents" WITH CHECK (("trial_id" IN ( SELECT "t"."id"
   FROM (("public"."trials" "t"
     JOIN "public"."members" "m" ON (("t"."organization_id" = "m"."organization_id")))
     JOIN "public"."profiles" "p" ON (("m"."profile_id" = "p"."id")))
  WHERE ("p"."id" = "auth"."uid"()))));



CREATE POLICY "Users can update own profile" ON "public"."profiles" FOR UPDATE USING (("id" = "auth"."uid"()));



CREATE POLICY "Users can view own profile" ON "public"."profiles" FOR SELECT USING (("id" = "auth"."uid"()));



CREATE POLICY "Users can view their organization" ON "public"."organizations" FOR SELECT USING (("id" = "public"."get_user_organization_id"()));



CREATE POLICY "Users can view trial_members_pending in their organization" ON "public"."trial_members_pending" FOR SELECT USING (("trial_id" IN ( SELECT "t"."id"
   FROM (("public"."trials" "t"
     JOIN "public"."members" "m" ON (("m"."organization_id" = "t"."organization_id")))
     JOIN "public"."profiles" "p" ON (("p"."id" = "m"."profile_id")))
  WHERE ("p"."id" = "auth"."uid"()))));



CREATE POLICY "View organization members" ON "public"."members" FOR SELECT USING (("organization_id" = "public"."get_user_organization_id"()));



CREATE POLICY "View organization patient documents" ON "public"."patient_documents" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."patients" "p"
  WHERE (("p"."id" = "patient_documents"."patient_id") AND ("p"."organization_id" = "public"."get_user_organization_id"())))));



CREATE POLICY "View organization patients" ON "public"."patients" FOR SELECT USING (("organization_id" = "public"."get_user_organization_id"()));



CREATE POLICY "View organization roles" ON "public"."roles" FOR SELECT USING (("organization_id" = "public"."get_user_organization_id"()));



CREATE POLICY "View organization trials" ON "public"."trials" FOR SELECT USING (("organization_id" = "public"."get_user_organization_id"()));



CREATE POLICY "View trial patients" ON "public"."trial_patients" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."trials" "t"
  WHERE (("t"."id" = "trial_patients"."trial_id") AND ("t"."organization_id" = "public"."get_user_organization_id"())))));



ALTER TABLE "public"."invitations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."patient_documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."patients" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."qa_repository" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."themison_admins" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trial_documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trial_members_pending" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trial_patients" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."trials" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."visit_documents" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";


















































































































































































































































































































































































































































































































GRANT ALL ON FUNCTION "public"."create_trial_with_members"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."create_trial_with_members"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_trial_with_members"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."create_trial_with_members_debug"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."create_trial_with_members_debug"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_trial_with_members_debug"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."create_trial_with_members_extended"("trial_data" "jsonb", "confirmed_assignments" "jsonb"[], "pending_assignments" "jsonb"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."create_trial_with_members_extended"("trial_data" "jsonb", "confirmed_assignments" "jsonb"[], "pending_assignments" "jsonb"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_trial_with_members_extended"("trial_data" "jsonb", "confirmed_assignments" "jsonb"[], "pending_assignments" "jsonb"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."create_trial_with_mixed_assignments"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."create_trial_with_mixed_assignments"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_trial_with_mixed_assignments"("trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."debug_trial_creation"("org_id" "uuid", "user_profile_id" "uuid", "trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."debug_trial_creation"("org_id" "uuid", "user_profile_id" "uuid", "trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."debug_trial_creation"("org_id" "uuid", "user_profile_id" "uuid", "trial_data" "jsonb", "team_assignments" "jsonb"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_organization_roles"("org_id" "uuid", "search_term" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_organization_roles"("org_id" "uuid", "search_term" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_organization_roles"("org_id" "uuid", "search_term" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_trial_team"("trial_id_param" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_trial_team"("trial_id_param" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_trial_team"("trial_id_param" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_user_organization_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_user_organization_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_user_organization_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_user_organization_id_for_trial_members"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_user_organization_id_for_trial_members"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_user_organization_id_for_trial_members"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_email_confirmation"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_email_confirmation"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_email_confirmation"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_invited_user_signup"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_invited_user_signup"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_invited_user_signup"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_new_profile"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_new_profile"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_new_profile"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_pending_trial_assignments"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_pending_trial_assignments"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_pending_trial_assignments"() TO "service_role";





















GRANT ALL ON FUNCTION "public"."is_themison_admin"() TO "anon";
GRANT ALL ON FUNCTION "public"."is_themison_admin"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_themison_admin"() TO "service_role";



GRANT ALL ON FUNCTION "public"."kw_match_documents"("query_text" "text", "match_count" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."kw_match_documents"("query_text" "text", "match_count" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."kw_match_documents"("query_text" "text", "match_count" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."mock_calculate_burn_rate"("trial_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."mock_calculate_burn_rate"("trial_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."mock_calculate_burn_rate"("trial_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."mock_get_available_budget"("trial_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."mock_get_available_budget"("trial_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."mock_get_available_budget"("trial_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."mock_get_patient_total_cost"("patient_id" "uuid", "trial_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."mock_get_patient_total_cost"("patient_id" "uuid", "trial_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."mock_get_patient_total_cost"("patient_id" "uuid", "trial_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."mock_populate_patient_costs"() TO "anon";
GRANT ALL ON FUNCTION "public"."mock_populate_patient_costs"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."mock_populate_patient_costs"() TO "service_role";



GRANT ALL ON FUNCTION "public"."mock_populate_trial_budget"() TO "anon";
GRANT ALL ON FUNCTION "public"."mock_populate_trial_budget"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."mock_populate_trial_budget"() TO "service_role";



GRANT ALL ON FUNCTION "public"."mock_populate_visit_costs"() TO "anon";
GRANT ALL ON FUNCTION "public"."mock_populate_visit_costs"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."mock_populate_visit_costs"() TO "service_role";



GRANT ALL ON FUNCTION "public"."populate_patient_data"() TO "anon";
GRANT ALL ON FUNCTION "public"."populate_patient_data"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."populate_patient_data"() TO "service_role";



GRANT ALL ON FUNCTION "public"."send_invitation_email_dynamic"() TO "anon";
GRANT ALL ON FUNCTION "public"."send_invitation_email_dynamic"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."send_invitation_email_dynamic"() TO "service_role";



GRANT ALL ON FUNCTION "public"."send_invitation_email_simple"() TO "anon";
GRANT ALL ON FUNCTION "public"."send_invitation_email_simple"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."send_invitation_email_simple"() TO "service_role";






GRANT ALL ON FUNCTION "public"."update_qa_repository_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_qa_repository_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_qa_repository_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."user_belongs_to_organization"() TO "anon";
GRANT ALL ON FUNCTION "public"."user_belongs_to_organization"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."user_belongs_to_organization"() TO "service_role";



GRANT ALL ON FUNCTION "public"."user_can_access_trial"("trial_id_param" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."user_can_access_trial"("trial_id_param" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."user_can_access_trial"("trial_id_param" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."user_can_create_trials"("user_profile_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."user_can_create_trials"("user_profile_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."user_can_create_trials"("user_profile_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."user_organization_status"("user_profile_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."user_organization_status"("user_profile_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."user_organization_status"("user_profile_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."user_trial_permission"("user_profile_id" "uuid", "trial_id_param" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."user_trial_permission"("user_profile_id" "uuid", "trial_id_param" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."user_trial_permission"("user_profile_id" "uuid", "trial_id_param" "uuid") TO "service_role";






























GRANT ALL ON TABLE "public"."chat_document_links" TO "anon";
GRANT ALL ON TABLE "public"."chat_document_links" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_document_links" TO "service_role";



GRANT ALL ON TABLE "public"."chat_messages" TO "anon";
GRANT ALL ON TABLE "public"."chat_messages" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_messages" TO "service_role";



GRANT ALL ON TABLE "public"."chat_sessions" TO "anon";
GRANT ALL ON TABLE "public"."chat_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."chat_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."document_chunks" TO "anon";
GRANT ALL ON TABLE "public"."document_chunks" TO "authenticated";
GRANT ALL ON TABLE "public"."document_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."document_chunks_docling" TO "anon";
GRANT ALL ON TABLE "public"."document_chunks_docling" TO "authenticated";
GRANT ALL ON TABLE "public"."document_chunks_docling" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."invitations" TO "anon";
GRANT ALL ON TABLE "public"."invitations" TO "authenticated";
GRANT ALL ON TABLE "public"."invitations" TO "service_role";



GRANT ALL ON TABLE "public"."members" TO "anon";
GRANT ALL ON TABLE "public"."members" TO "authenticated";
GRANT ALL ON TABLE "public"."members" TO "service_role";
GRANT SELECT ON TABLE "public"."members" TO PUBLIC;



GRANT ALL ON TABLE "public"."organizations" TO "anon";
GRANT ALL ON TABLE "public"."organizations" TO "authenticated";
GRANT ALL ON TABLE "public"."organizations" TO "service_role";



GRANT ALL ON TABLE "public"."patient_documents" TO "anon";
GRANT ALL ON TABLE "public"."patient_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."patient_documents" TO "service_role";



GRANT ALL ON TABLE "public"."patient_visits" TO "anon";
GRANT ALL ON TABLE "public"."patient_visits" TO "authenticated";
GRANT ALL ON TABLE "public"."patient_visits" TO "service_role";



GRANT ALL ON TABLE "public"."patients" TO "anon";
GRANT ALL ON TABLE "public"."patients" TO "authenticated";
GRANT ALL ON TABLE "public"."patients" TO "service_role";



GRANT ALL ON TABLE "public"."trials" TO "anon";
GRANT ALL ON TABLE "public"."trials" TO "authenticated";
GRANT ALL ON TABLE "public"."trials" TO "service_role";
GRANT SELECT ON TABLE "public"."trials" TO PUBLIC;



GRANT ALL ON TABLE "public"."patient_visits_detailed" TO "anon";
GRANT ALL ON TABLE "public"."patient_visits_detailed" TO "authenticated";
GRANT ALL ON TABLE "public"."patient_visits_detailed" TO "service_role";



GRANT ALL ON TABLE "public"."profiles" TO "anon";
GRANT ALL ON TABLE "public"."profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."profiles" TO "service_role";



GRANT ALL ON TABLE "public"."protocol_chunks" TO "anon";
GRANT ALL ON TABLE "public"."protocol_chunks" TO "authenticated";
GRANT ALL ON TABLE "public"."protocol_chunks" TO "service_role";



GRANT ALL ON TABLE "public"."protocol_chunks_biobert" TO "anon";
GRANT ALL ON TABLE "public"."protocol_chunks_biobert" TO "authenticated";
GRANT ALL ON TABLE "public"."protocol_chunks_biobert" TO "service_role";



GRANT ALL ON TABLE "public"."protocols" TO "anon";
GRANT ALL ON TABLE "public"."protocols" TO "authenticated";
GRANT ALL ON TABLE "public"."protocols" TO "service_role";



GRANT ALL ON TABLE "public"."protocols_biobert" TO "anon";
GRANT ALL ON TABLE "public"."protocols_biobert" TO "authenticated";
GRANT ALL ON TABLE "public"."protocols_biobert" TO "service_role";



GRANT ALL ON TABLE "public"."qa_repository" TO "anon";
GRANT ALL ON TABLE "public"."qa_repository" TO "authenticated";
GRANT ALL ON TABLE "public"."qa_repository" TO "service_role";



GRANT ALL ON TABLE "public"."roles" TO "anon";
GRANT ALL ON TABLE "public"."roles" TO "authenticated";
GRANT ALL ON TABLE "public"."roles" TO "service_role";



GRANT ALL ON TABLE "public"."themison_admins" TO "anon";
GRANT ALL ON TABLE "public"."themison_admins" TO "authenticated";
GRANT ALL ON TABLE "public"."themison_admins" TO "service_role";



GRANT ALL ON TABLE "public"."trial_documents" TO "anon";
GRANT ALL ON TABLE "public"."trial_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."trial_documents" TO "service_role";



GRANT ALL ON TABLE "public"."trial_members" TO "anon";
GRANT ALL ON TABLE "public"."trial_members" TO "authenticated";
GRANT ALL ON TABLE "public"."trial_members" TO "service_role";



GRANT ALL ON TABLE "public"."trial_members_pending" TO "anon";
GRANT ALL ON TABLE "public"."trial_members_pending" TO "authenticated";
GRANT ALL ON TABLE "public"."trial_members_pending" TO "service_role";



GRANT ALL ON TABLE "public"."trial_patients" TO "anon";
GRANT ALL ON TABLE "public"."trial_patients" TO "authenticated";
GRANT ALL ON TABLE "public"."trial_patients" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON TABLE "public"."visit_documents" TO "anon";
GRANT ALL ON TABLE "public"."visit_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."visit_documents" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






























