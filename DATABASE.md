# Database Schema Analysis

## Goal
Create a clean database for a new project, keeping all business tables but dropping legacy/dead RAG tables.

---

## Current Schema Analysis (27 tables in Supabase)

### Tables in schema.sql

| Table | Category | Status | Recommendation |
|-------|----------|--------|----------------|
| `document_chunks_docling` | RAG | **Active** | **KEEP** |
| `semantic_cache_responses` | RAG | **Active** | **KEEP** (created by app) |
| `document_chunks` | Legacy RAG | Dead code | **DROP** |
| `documents` | Legacy | Dead code | **DROP** |
| `protocol_chunks` | Legacy RAG | Dead code | **DROP** |
| `protocol_chunks_biobert` | Legacy RAG | Dead code | **DROP** |
| `protocols` | Legacy | Dead code | **DROP** |
| `protocols_biobert` | Legacy | Dead code | **DROP** |
| `trial_documents` | Business | Active | **KEEP** |
| `chat_sessions` | Business | Active | **KEEP** |
| `chat_messages` | Business | Active | **KEEP** |
| `chat_document_links` | Business | Active | **KEEP** |
| `users` | Business | Active | **KEEP** |
| `profiles` | Business | Active | **KEEP** |
| `organizations` | Business | Active | **KEEP** |
| `members` | Business | Active | **KEEP** |
| `invitations` | Business | Active | **KEEP** |
| `trials` | Business | Active | **KEEP** |
| `trial_members` | Business | Active | **KEEP** |
| `trial_members_pending` | Business | Active | **KEEP** |
| `patients` | Business | Active | **KEEP** |
| `trial_patients` | Business | Active | **KEEP** |
| `patient_visits` | Business | Active | **KEEP** |
| `patient_documents` | Business | Active | **KEEP** |
| `visit_documents` | Business | Active | **KEEP** |
| `qa_repository` | Business | Active | **KEEP** |
| `roles` | Business | Active | **KEEP** |
| `themison_admins` | Business | Active | **KEEP** |

---

## Tables to DROP (6 Legacy/Dead)

These tables are not used anywhere in the active codebase:

| Table | Reason |
|-------|--------|
| `document_chunks` | Replaced by `document_chunks_docling` |
| `documents` | Old document storage, not used |
| `protocol_chunks` | Old protocol system |
| `protocol_chunks_biobert` | Old BioBERT embeddings (768-dim) |
| `protocols` | Old protocol metadata |
| `protocols_biobert` | Old BioBERT protocol metadata |

---

## Tables to KEEP (22)

### RAG Tables (2)
- `document_chunks_docling` - vector store with pgvector
- `semantic_cache_responses` - semantic response caching (created by app)

### Business Tables (20)
- **Auth/Users**: `users`, `profiles`, `themison_admins`
- **Organizations**: `organizations`, `members`, `invitations`, `roles`
- **Trials**: `trials`, `trial_members`, `trial_members_pending`, `trial_documents`
- **Patients**: `patients`, `trial_patients`, `patient_visits`, `patient_documents`, `visit_documents`
- **Chat**: `chat_sessions`, `chat_messages`, `chat_document_links`
- **Other**: `qa_repository`

---

## Migration Steps

1. **Create new PostgreSQL database** with pgvector extension
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Export schema from Supabase** (excluding dropped tables):
   ```bash
   pg_dump --schema-only --exclude-table=document_chunks \
     --exclude-table=documents --exclude-table=protocol_chunks \
     --exclude-table=protocol_chunks_biobert --exclude-table=protocols \
     --exclude-table=protocols_biobert $OLD_DB_URL > schema.sql
   ```

3. **Import schema to new database**:
   ```bash
   psql $NEW_DB_URL < schema.sql
   ```

4. **Migrate data** (if needed):
   ```sql
   -- Migrate all business tables + RAG chunks
   INSERT INTO new_db.table_name SELECT * FROM old_db.table_name;
   ```

5. **Create HNSW indexes** (critical for performance):
   ```sql
   CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks_docling
       USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
   CREATE INDEX idx_chunks_content_gin ON document_chunks_docling
       USING GIN (content_tsv);
   ```

6. **Update connection strings** and test

---

## Environment Variables

```env
# New database (replaces SUPABASE_DB_URL)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/new_db

# Redis (unchanged)
REDIS_URL=redis://localhost:6379

# AI APIs (unchanged)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# API Key (unchanged)
UPLOAD_API_KEY=your-api-key
```

---

## Benefits

| Aspect | Before (27 tables) | After (22 tables) |
|--------|-------------------|-------------------|
| Legacy tables | 6 dead tables | Removed |
| Schema cleanliness | Mixed old/new | Clean |
| Vector indexes | May be missing | Properly configured |
| Decoupled | No | Yes (new project) |

---

## Notes

- Keep all foreign key relationships between business tables
- pgvector extension must be enabled before creating tables
- HNSW indexes are critical for vector search performance
- GIN index on `content_tsv` enables BM25 hybrid search
- `semantic_cache_responses` is auto-created by SQLAlchemy if missing
- Consider adding RLS policies if multi-tenant access is needed

---

## Docker Deployment

### Prerequisites

- Docker Desktop installed and running
- Ports 54322 (PostgreSQL) and 6379 (Redis) available

### Quick Start

```bash
# From core-backend.V2/ directory

# Start services (PostgreSQL + Redis + Supabase Studio)
docker-compose up -d

# Verify containers are running
docker ps
```

### Services

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| PostgreSQL | themison-db | 54322 | pgvector/pgvector:pg16 with vector extension |
| Redis | themison-redis | 6379 | Caching (embeddings, chunks, responses) |
| Supabase Studio | themison-studio | 54323 | Database GUI (optional) |

### Connection Details

```
Host:     localhost
Port:     54322
User:     postgres
Password: postgres
Database: postgres
```

**Connection String (asyncpg):**
```
postgresql+asyncpg://postgres:postgres@localhost:54322/postgres
```

### Environment Variables

Update `.env` to use Docker database:

```env
# Docker PostgreSQL
SUPABASE_DB_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres

# Docker Redis
REDIS_URL=redis://localhost:6379

# AI APIs (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# API Key for /query endpoint
UPLOAD_API_KEY=your-api-key
```

### Database Schema

The schema is auto-initialized from `docker/init.sql` on first startup:

- **22 tables** (2 RAG + 20 business)
- **8 enums** (organization_member_type, document_type_enum, etc.)
- **38 indexes** including HNSW for vector search and GIN for BM25

### Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services (preserves data)
docker-compose down

# Reset database (deletes all data)
docker-compose down -v && docker-compose up -d

# View logs
docker-compose logs -f db

# Connect to PostgreSQL
docker exec -it themison-db psql -U postgres

# List tables
docker exec themison-db psql -U postgres -c "\dt"

# List indexes
docker exec themison-db psql -U postgres -c "\di"

# Check extensions
docker exec themison-db psql -U postgres -c "SELECT extname FROM pg_extension;"
```

### RAG Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `document_chunks_docling` | Vector store | `embedding vector(1536)`, `content_tsv` (BM25) |
| `semantic_cache_responses` | Query cache | `query_embedding vector(1536)`, `response_data JSONB` |

### Indexes for Search Performance

| Index | Table | Type | Purpose |
|-------|-------|------|---------|
| `idx_chunks_embedding_hnsw` | document_chunks_docling | HNSW | Fast vector similarity search |
| `idx_chunks_content_gin` | document_chunks_docling | GIN | BM25 full-text search |
| `idx_semantic_cache_embedding_hnsw` | semantic_cache_responses | HNSW | Semantic cache lookup |

### Query Endpoint Dependencies

The `/query` endpoint only requires these tables:

1. `document_chunks_docling` - for vector/hybrid search
2. `semantic_cache_responses` - for caching (optional)

All other tables are for the business application (trials, patients, etc.).

### Troubleshooting

**Port already in use:**
```bash
# Check what's using port 54322
netstat -ano | findstr :54322

# Or change port in docker-compose.yml
ports:
  - "54323:5432"  # Use different host port
```

**Schema not initialized:**
```bash
# Check if init.sql ran
docker logs themison-db | grep "Themison Database Initialized"

# Force reinitialize
docker-compose down -v && docker-compose up -d
```

**Vector extension missing:**
```bash
# Verify extension
docker exec themison-db psql -U postgres -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# Should return: vector
```
