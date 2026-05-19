# Supabase Project Migration Guide

This guide explains how to migrate all data and auth users from the old Supabase project to the new one.

## Overview

- **Old Project**: `gpfyejxokywdkudkeywv`
- **New Project**: `nidpneaqxghqueniodus`

The migration preserves:
- All auth users (with their existing passwords)
- All application data (organizations, trials, documents, chat history)
- Document embeddings (vector data)

## Prerequisites

1. Python 3.10+ with asyncpg installed:
   ```bash
   pip install asyncpg
   ```

2. Access to both Supabase projects (database passwords)

3. New database should have the schema already created (tables must exist)

## Migration Order

**CRITICAL**: Follow this exact order to avoid foreign key constraint errors.

```
1. Run schema migrations on NEW database (if not done)
2. Export auth users from OLD database
3. Import auth users to NEW database
4. Export application data from OLD database
5. Import application data to NEW database
6. Update tsvector columns
7. Verify data
```

## Step-by-Step Instructions

### Step 1: Ensure Schema Exists on New Database

The new database should already have tables created. If not, run migrations in Supabase SQL Editor:

```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

### Step 2: Export Auth Users from Old Project

You need the **DIRECT** database connection (not pooler) to access the `auth` schema.

```powershell
# Set environment variable (get password from Supabase Dashboard > Settings > Database)
$env:OLD_SUPABASE_DB_URL = "postgresql://postgres:YOUR_PASSWORD@db.gpfyejxokywdkudkeywv.supabase.co:5432/postgres"

# Run export
python scripts/migration/export_auth_users.py
```

This creates:
- `scripts/migration/exported_data/auth_users.json`
- `scripts/migration/exported_data/auth_identities.json`

### Step 3: Import Auth Users to New Project

```powershell
# Set environment variable for NEW project (DIRECT connection)
$env:NEW_SUPABASE_DB_URL = "postgresql://postgres:YOUR_PASSWORD@db.nidpneaqxghqueniodus.supabase.co:5432/postgres"

# Run import
python scripts/migration/import_auth_users.py
```

### Step 4: Export Application Data from Old Project

```powershell
# Can use pooler connection for regular tables
$env:OLD_SUPABASE_DB_URL = "postgresql://postgres.gpfyejxokywdkudkeywv:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

# Run export
python scripts/migration/export_data.py
```

This creates JSON files for each table in `scripts/migration/exported_data/`.

### Step 5: Import Application Data to New Project

```powershell
# Can use pooler connection
$env:NEW_SUPABASE_DB_URL = "postgresql://postgres.nidpneaqxghqueniodus:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

# Run import
python scripts/migration/import_data.py
```

### Step 6: Post-Import Updates

Run these SQL commands in Supabase SQL Editor on the NEW database:

```sql
-- Update tsvector column for full-text search
UPDATE document_chunks_docling
SET content_tsv = to_tsvector('english', content)
WHERE content_tsv IS NULL;

-- Verify counts
SELECT
    'document_chunks_docling' as table_name,
    COUNT(*) as total_rows,
    COUNT(content_tsv) as rows_with_tsvector,
    COUNT(embedding) as rows_with_embedding
FROM document_chunks_docling;
```

### Step 7: Verify Migration

```sql
-- Count rows in main tables
SELECT 'organizations' as tbl, COUNT(*) FROM organizations
UNION ALL SELECT 'profiles', COUNT(*) FROM profiles
UNION ALL SELECT 'clinical_trials', COUNT(*) FROM clinical_trials
UNION ALL SELECT 'trial_documents', COUNT(*) FROM trial_documents
UNION ALL SELECT 'document_chunks_docling', COUNT(*) FROM document_chunks_docling
UNION ALL SELECT 'chat_sessions', COUNT(*) FROM chat_sessions;

-- Check auth users
SELECT COUNT(*) as user_count FROM auth.users;
```

## Connection String Formats

### Direct Connection (for auth schema)
```
postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres
```

### Pooler Connection (for regular tables)
```
postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

## Troubleshooting

### "Cannot access auth.users"
- Use DIRECT connection, not pooler
- Check database password is correct

### "Foreign key violation"
- Import auth users FIRST
- Tables must be imported in dependency order

### "Table does not exist"
- Run schema migrations on new database first
- The `semantic_cache_responses` table may need to be created

### "Invalid password"
- Get password from: Supabase Dashboard > Settings > Database
- For direct connection: Settings > Database > Connection string > URI
- For pooler: Settings > Database > Connection pooling

## New Schema Columns

The new embedding improvements added these columns (all nullable):
- `content_tsv` (tsvector) - For full-text BM25 search
- `embedding_large` (vector 2000) - For larger embedding model
- `contextual_summary` (text) - For contextual retrieval

These columns will be NULL after migration. They will be populated when:
1. `content_tsv` - When you run the UPDATE command above
2. `embedding_large` - When you enable larger embeddings and re-process documents
3. `contextual_summary` - When you enable contextual retrieval

## Files

```
scripts/migration/
├── MIGRATION_GUIDE.md     # This file
├── export_auth_users.py   # Export auth.users from old DB
├── export_data.py         # Export application data from old DB
├── import_auth_users.py   # Import auth users to new DB
├── import_data.py         # Import application data to new DB
└── exported_data/         # Created during export
    ├── _metadata.json
    ├── auth_users.json
    ├── auth_identities.json
    ├── organizations.json
    ├── profiles.json
    ├── clinical_trials.json
    ├── trial_documents.json
    ├── document_chunks_docling.json
    └── ...
```
