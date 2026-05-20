# Database Schema Analysis

## Goal
Migrate from the original platform to a new clean database, keeping all business and RAG tables,
fixing model inconsistencies, and adding new Collaboration Hub tables.

---

## Current Schema Analysis (28 tables from original platform)

### Tables from schema dump

| Table | Category | Status | Recommendation |
|-------|----------|--------|----------------|
| `document_chunks_docling` | RAG | **Active** | **KEEP** |
| `semantic_cache_responses` | RAG | **Active** | **KEEP** |
| `activity_types` | Business | Active | **KEEP** |
| `archive_folder` | Business | Active | **KEEP** |
| `chat_document_links` | Business | Active | **KEEP** |
| `chat_messages` | Business | Active | **KEEP** |
| `chat_sessions` | Business | Active | **KEEP** |
| `chat_threads` | Business | Active | **KEEP** (FK fixed) |
| `invitations` | Business | Active | **KEEP** |
| `members` | Business | Active | **KEEP** |
| `organizations` | Business | Active | **KEEP** |
| `patient_documents` | Business | Active | **KEEP** |
| `patient_visits` | Business | Active | **KEEP** |
| `patients` | Business | Active | **KEEP** |
| `profiles` | Business | Active | **KEEP** |
| `qa_repository` | Business | Active | **KEEP** |
| `response_folders` | Business | Active | **KEEP** |
| `responses_archived` | Business | Active | **KEEP** |
| `roles` | Business | Active | **KEEP** |
| `tasks` | Business | Active | **KEEP** |
| `themison_admins` | Business | Active | **KEEP** |
| `thread_participants` | Business | Active | **KEEP** (FK fixed) |
| `trial_activity_types` | Business | Active | **KEEP** |
| `trial_documents` | Business | Active | **KEEP** |
| `trial_members` | Business | Active | **KEEP** |
| `trial_members_pending` | Business | Active | **KEEP** |
| `trial_patients` | Business | Active | **KEEP** |
| `trials` | Business | Active | **KEEP** |
| `users` | Business | Active | **KEEP** |
| `visit_activities` | Business | Active | **KEEP** |
| `visit_documents` | Business | Active | **KEEP** |

---

## Tables Added (4 New — Collaboration Hub)

| Table | Reason |
|-------|--------|
| `inbox_messages` | New Collaboration Hub inbox feature |
| `direct_messages` | New Collaboration Hub DMs feature |
| `collaboration_threads` | New Collaboration Hub threads feature |
| `collaboration_thread_messages` | New Collaboration Hub thread replies |

---

## Schema Before vs After

| Aspect | Before (28 tables) | After (35 tables) |
|--------|-------------------|-------------------|
| Total tables | 28 | 35 |
| RAG tables | 2 | 2 (unchanged) |
| Business tables | 26 | 26 (unchanged) |
| Collaboration Hub tables | 0 | 4 (new) |
| Alembic version table | 0 | 1 (added by Alembic) |
| Migration system | Self-healing in `main.py` | Alembic version files |
| Model type accuracy | Mixed JSON/JSONB | All correct JSONB |
| Dead model files | 1 (`chat_messagesthreads.py`) | Removed |

---

## Tables to KEEP (35 total after migration)

### RAG Tables (2)
- `document_chunks_docling` — vector store with pgvector (1536-dim embeddings)
- `semantic_cache_responses` — semantic response caching

### Business Tables (26)
- **Auth/Users**: `users`, `profiles`, `themison_admins`
- **Organizations**: `organizations`, `members`, `invitations`, `roles`
- **Trials**: `trials`, `trial_members`, `trial_members_pending`, `trial_documents`, `trial_activity_types`
- **Patients**: `patients`, `trial_patients`, `patient_visits`, `patient_documents`, `visit_documents`, `visit_activities`
- **Tasks**: `tasks`, `activity_types`
- **Chat (AI)**: `chat_sessions`, `chat_messages`, `chat_document_links`, `chat_threads`, `thread_participants`
- **Archive**: `response_folders`, `responses_archived`
- **QA**: `qa_repository`

### New Collaboration Hub Tables (4)
- `inbox_messages` — email-style inbox with AI summary, labels, folder management
- `direct_messages` — 1:1 messages between members with optional task cards
- `collaboration_threads` — structured discussion threads (question/decision/general) with anchors
- `collaboration_thread_messages` — replies inside collaboration threads

### System Tables (1)
- `alembic_version` — tracks current migration version (added automatically by Alembic)

---

## Model Fixes Applied

The following model files had incorrect types or foreign keys that did not match the actual DB schema:

| File | Column | Before | After | Reason |
|------|--------|--------|-------|--------|
| `app/models/trials.py` | `budget_data`, `visit_schedule_template` | `JSON` | `JSONB` | Match DB |
| `app/models/trial_patients.py` | `cost_data`, `patient_data` | `JSON` | `JSONB` | Match DB |
| `app/models/patient_visits.py` | `cost_data` | `JSON` | `JSONB` | Match DB |
| `app/models/trial_members.py` | `settings` | `JSON` | `JSONB` | Match DB |
| `app/models/qa_repository.py` | `sources` | `JSON` | `JSONB` | Match DB |
| `app/models/semantic_cache.py` | `response_data` | `JSON` | `JSONB` | Match DB |
| `app/models/saved_response.py` | `raw_data` | `JSONB` | `Text` | Match DB |
| `app/models/chat_threads.py` | `created_by` FK | `members.profile_id` | `profiles.id` | Invalid FK |
| `app/models/thread_participants.py` | `user_id` FK | `members.profile_id` | `profiles.id` | Invalid FK |
| `app/models/user.py` | `password` | `UUID` | `Text` | Wrong type |
| `app/models/chat_messagesthreads.py` | — | Existed | **Deleted** | Duplicate of `chat_messages.py` |

---

## Migration Steps

1. **Dump schema from original Docker DB** (schema only, no data):
   ```bash
   docker exec -it themison-db pg_dump \
     --schema-only -U postgres -d postgres \
     > schema_dump.sql
   ```

2. **Start new Docker containers**:
   ```bash
   docker-compose up -d db redis
   ```

3. **Apply schema dump to new DB**:
   ```bash
   psql postgresql://postgres:postgres@localhost:5433/themison_new -f schema_dump.sql
   ```

4. **Stamp Alembic baseline** (schema already exists, do not re-run it):
   ```bash
   alembic -c alembic.ini stamp 001
   ```

5. **Apply new Collaboration Hub migration**:
   ```bash
   alembic -c alembic.ini upgrade head
   ```

6. **Verify all tables exist**:
   ```bash
   psql postgresql://postgres:postgres@localhost:5433/themison_new \
     -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
   ```

7. **Check current migration version**:
   ```bash
   alembic -c alembic.ini current
   # should show: head
   ```

---

## Environment Variables

```env
# New Docker PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/themison_new

# New Docker Redis
REDIS_URL=redis://localhost:6380/0

# Auth0
AUTH0_DOMAIN=your-tenant.eu.auth0.com
AUTH0_AUDIENCE=https://your-api-identifier
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH_DISABLED=false

# AI APIs (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
UPLOAD_API_KEY=your-api-key

# RAG service — shared with original platform
RAG_SERVICE_ADDRESS=localhost:50051
USE_GRPC_RAG=false

# CORS
FRONTEND_URL=http://localhost:3000
ALLOW_ALL_ORIGINS=true
```

---

## Docker Deployment

### Prerequisites

- Docker Desktop installed and running
- Ports `5433` (PostgreSQL) and `6380` (Redis) available
- Original platform may still be running on `54322` and `6379` — no conflict

### Quick Start

```bash
# From new-platform-backend/ directory

# Start DB and Redis
docker-compose up -d db redis

# Verify containers are running
docker ps | grep themison-new
```

### Services

| Service | Container | Host Port | Container Port | Description |
|---------|-----------|-----------|----------------|-------------|
| PostgreSQL | `themison-new-db` | `5433` | `5432` | pgvector/pgvector:pg16 with vector extension |
| Redis | `themison-new-redis` | `6380` | `6379` | Caching (sessions, responses) |
| Backend | `themison-new-backend` | `8081` | `8080` | FastAPI backend |

> **Why different ports?** To avoid conflicts with the original platform still running locally:

| Service | Original Platform | New Platform |
|---------|------------------|--------------|
| PostgreSQL | `54322` | `5433` |
| Redis | `6379` | `6380` |
| Backend | `8080` | `8081` |

> **RAG Service:** Shared with original platform — no new RAG container needed. Point `RAG_SERVICE_ADDRESS` to existing RAG service.

### Connection Details

```
Host:     localhost
Port:     5433
User:     postgres
Password: postgres
Database: themison_new
```

**Connection String (asyncpg):**
```
postgresql+asyncpg://postgres:postgres@localhost:5433/themison_new
```

### Database Schema

The schema is applied from `schema_dump.sql` on first setup:

- **35 tables** (2 RAG + 26 business + 4 collaboration hub + 1 alembic)
- **8 enums** (organization_member_type, document_type_enum, visit_status_enum, etc.)
- Indexes including HNSW for vector search and GIN for BM25

### Useful Commands

```bash
# Start services
docker-compose up -d db redis

# Start all including backend
docker-compose up -d

# Stop services (preserves data)
docker-compose down

# Reset database (deletes all data — use with caution)
docker-compose down -v && docker-compose up -d db redis

# View DB logs
docker-compose logs -f db

# Connect to PostgreSQL
docker exec -it themison-new-db psql -U postgres -d themison_new

# List all tables
docker exec themison-new-db psql -U postgres -d themison_new -c "\dt"

# List all indexes
docker exec themison-new-db psql -U postgres -d themison_new -c "\di"

# Check extensions
docker exec themison-new-db psql -U postgres -d themison_new \
  -c "SELECT extname FROM pg_extension;"

# Check current Alembic migration
alembic -c alembic.ini current

# Check Alembic migration history
alembic -c alembic.ini history
```

### RAG Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `document_chunks_docling` | Vector store | `embedding vector(1536)`, `content_tsv` (BM25) |
| `semantic_cache_responses` | Query cache | `query_embedding vector(1536)`, `response_data JSONB` |

### Indexes for Search Performance

| Index | Table | Type | Purpose |
|-------|-------|------|---------|
| `idx_chunks_embedding_hnsw` | `document_chunks_docling` | HNSW | Fast vector similarity search |
| `idx_chunks_content_gin` | `document_chunks_docling` | GIN | BM25 full-text search |
| `idx_semantic_cache_embedding_hnsw` | `semantic_cache_responses` | HNSW | Semantic cache lookup |
| `idx_inbox_messages_owner` | `inbox_messages` | BTREE | Inbox queries by owner |
| `idx_dm_conversation` | `direct_messages` | BTREE | DM conversation queries |
| `idx_collab_threads_org` | `collaboration_threads` | BTREE | Thread list by org |

---

## Alembic Migration Workflow

### Making a DB change — always follow this order

```
1. Edit or create model file in app/models/ (ORM style only)
        ↓
2. Generate migration automatically
   alembic -c alembic.ini revision --autogenerate -m "describe your change"
        ↓
3. Review generated file in alembic/versions/
        ↓
4. Apply locally
   alembic -c alembic.ini upgrade head
        ↓
5. Commit model + migration file together
   git add app/models/your_model.py alembic/versions/xxxx_your_change.py
   git commit -m "migration: describe your change"
   git push
```

### After pulling someone else's changes
```bash
git pull
alembic -c alembic.ini upgrade head
```

### Common Alembic commands

| Command | What it does |
|---------|-------------|
| `alembic -c alembic.ini upgrade head` | Apply all pending migrations |
| `alembic -c alembic.ini downgrade -1` | Roll back last migration |
| `alembic -c alembic.ini current` | Show current migration version |
| `alembic -c alembic.ini history` | Show all migrations in order |
| `alembic -c alembic.ini revision --autogenerate -m "msg"` | Generate migration from model changes |
| `alembic -c alembic.ini stamp head` | Mark DB as up to date without running migrations |

### Team rules

1. **Never edit an existing migration file** — create a new one instead
2. **Always generate migration when changing a model** — model + migration in same commit
3. **Always run `alembic upgrade head` after `git pull`**
4. **Never run raw `ALTER TABLE` on any DB directly** — always through Alembic
5. **Always use `JSONB` not `JSON`** for JSON columns in PostgreSQL models
6. **Always import `UUID`, `JSONB`, `ENUM` from `sqlalchemy.dialects.postgresql`** not from `sqlalchemy`

---

## Troubleshooting

**Port already in use:**
```bash
# Check what is using port 5433
lsof -i :5433

# Or change port in docker-compose.yml
ports:
  - "5434:5432"  # use different host port
```

**Schema not applied:**
```bash
# Check if tables exist
docker exec themison-new-db psql -U postgres -d themison_new -c "\dt"

# Force reset and reapply
docker-compose down -v && docker-compose up -d db redis
psql postgresql://postgres:postgres@localhost:5433/themison_new -f schema_dump.sql
alembic -c alembic.ini stamp 001
alembic -c alembic.ini upgrade head
```

**Vector extension missing:**
```bash
# Verify extension
docker exec themison-new-db psql -U postgres -d themison_new \
  -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# Should return: vector
# If missing, pgvector image was not used — check docker-compose.yml image name
```

**Alembic import errors:**
```bash
# Install missing packages
pip install pgvector python-dotenv psycopg2-binary alembic

# Check all model imports in alembic/env.py are correct
# UUID, JSONB, ENUM must come from sqlalchemy.dialects.postgresql
```

**`cannot import JSONB from sqlalchemy`:**
```python
# wrong
from sqlalchemy import JSONB

# correct
from sqlalchemy.dialects.postgresql import JSONB
```

**`no unique constraint on members`:**
```python
# wrong FK
ForeignKey("members.profile_id")

# correct FK
ForeignKey("profiles.id")
```

---

## Notes

- Keep all foreign key relationships between business tables
- pgvector extension is included in `pgvector/pgvector:pg16` image automatically
- HNSW indexes are critical for vector search performance
- GIN index on `content_tsv` enables BM25 hybrid search
- `alembic_version` table is created automatically by Alembic — do not delete it
- RAG service is shared with original platform — no changes needed there
- New platform uses Auth0 same tenant, same API audience — only `CLIENT_ID` differs
