# Production Setup Guide

This guide covers environment configuration for running Themison in two modes:
1. **Local Docker** - Full stack on your machine for development and testing
2. **Production (Google Cloud)** - Deployed to GCP with managed services

---

## Architecture Overview

```
                         +------------------+
    Frontend (React)  -->|  FastAPI Backend  |---> PostgreSQL (pgvector)
                         |   port 8000      |---> Redis (caching)
                         +--------+---------+
                                  |
                          gRPC (port 50051)
                                  |
                         +--------+---------+
                         |   RAG Service    |---> PostgreSQL (shared)
                         |  (gRPC server)   |
                         +------------------+
```

**Services:**

| Service       | Role                                        | Port  |
|---------------|---------------------------------------------|-------|
| backend       | FastAPI REST API (auth, upload, query, CRUD) | 8000  |
| rag-service   | gRPC microservice (ingest PDF, RAG query)   | 50051 |
| db            | PostgreSQL 16 + pgvector                    | 54322 (host) / 5432 (internal) |
| redis         | 3-tier cache (embeddings, chunks, responses) | 6379  |

---

## 1. Local Docker Setup

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key (for embeddings)
- Anthropic API key (for Claude LLM generation)

### Step 1: Create `.env`

Copy the Docker-ready env file (has correct defaults for `AUTH_DISABLED`, `USE_GRPC_RAG`, etc.):

```bash
cp docker/.env.docker .env
```

Then fill in your two API keys:

```env
OPENAI_API_KEY=sk-proj-your-real-key
ANTHROPIC_API_KEY=sk-ant-api03-your-real-key
```

That's it. All other values have working defaults. See `docker/.env.docker` for full reference.

### Step 2: Start all services

```bash
docker-compose up -d --build
```

This starts 4 containers:
- `themison-db` (PostgreSQL + pgvector, auto-initialized with `docker/init.sql` + seed data from `docker/seed.sql`)
- `themison-redis`
- `themison-rag-service` (gRPC, builds from `../../rag-service`)
- `themison-backend` (FastAPI, builds from current directory)

### Seed Data

On first startup, `docker/seed.sql` populates the database with test records so the API is immediately usable:

| Record | ID | Purpose |
|--------|----|---------|
| Themison Admin | `00000000-0000-0000-0000-000000000001` | Organization creator |
| Organization | `10000000-0000-0000-0000-000000000001` | "Themison Dev Org" |
| Profile | `20000000-0000-0000-0000-000000000001` | Auth mock user (test@themison.com) |
| Member | `30000000-0000-0000-0000-000000000001` | Links profile to org (admin role) |
| Trial | `50000000-0000-0000-0000-000000000001` | "BEACON-1 Phase III Study" |

With `AUTH_DISABLED=true`, all authenticated endpoints use the seeded member automatically. No Auth0 token needed.

To re-seed an existing database without destroying data:
```bash
docker exec -i themison-db psql -U postgres -d postgres < docker/seed.sql
```

### Step 3: Verify

```bash
# Check all containers are healthy
docker-compose ps

# Swagger UI
open http://localhost:8000/docs
```

### Step 4: Test the full flow

All seed data IDs are fixed for easy copy-paste. Use Swagger UI at `http://localhost:8000/docs`.

**1. Upload a PDF**
```
POST /api/trial-documents/upload
  Authorization: (not required when AUTH_DISABLED=true)
  Form data:
    file:          <attach any PDF>
    trial_id:      50000000-0000-0000-0000-000000000001
    document_name: Clinical Protocol
    document_type: protocol
```
Save `id` and `document_url` from the response.

**2. Ingest the PDF (RAG pipeline)**
```
POST /upload/upload-pdf
  X-API-KEY: <your UPLOAD_API_KEY from .env>
  Body (JSON):
    {
      "document_url": "<document_url from step 1>",
      "document_id": "<id from step 1>"
    }
```
Save `job_id` from the response.

**3. Poll ingestion status**
```
GET /upload/status/{job_id}
```
Repeat until `status` is `"completed"`.

**4. Query the document**
```
POST /query
  X-API-KEY: <your UPLOAD_API_KEY from .env>
  Body (JSON):
    {
      "query": "What is the primary endpoint of this study?",
      "document_id": "<id from step 1>",
      "document_name": "Clinical Protocol"
    }
```

### File Storage in Local Docker

When `GCS_BUCKET_TRIAL_DOCUMENTS` is **not set** (or empty), the backend automatically uses `LocalStorageService`:

- Files are saved to `./uploads/` (Docker volume: `backend_uploads`)
- Served via `GET /local-files/{path}` endpoint
- URLs look like `http://backend:8000/local-files/trials/{id}/file.pdf`
- The upload endpoint translates `localhost:8000` to `backend:8000` for Docker-internal networking

No GCS credentials needed for local development.

### Docker Networking

Inside Docker, services reference each other by container name, not `localhost`:

| From         | To              | Address               |
|--------------|-----------------|----------------------|
| backend      | PostgreSQL      | `db:5432`            |
| backend      | Redis           | `redis:6379`         |
| backend      | RAG service     | `rag-service:50051`  |
| rag-service  | PostgreSQL      | `db:5432`            |
| rag-service  | backend (files) | `backend:8000`       |

The `docker-compose.yml` handles this mapping. The backend `DATABASE_URL` inside Docker is set to `postgresql+asyncpg://postgres:postgres@db:5432/postgres` (not the host-exposed port 54322).

### Running Backend Outside Docker (hybrid)

If you want to run only the backend locally (with `uvicorn`) while keeping DB/Redis/RAG in Docker:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres
REDIS_URL=redis://localhost:6379
RAG_SERVICE_ADDRESS=localhost:50051
USE_GRPC_RAG=true
```

Note: Port `54322` is the host-mapped port for PostgreSQL.

---

## 2. Production Setup (Google Cloud)

### Required Environment Variables

```env
# ===================
# API Keys
# ===================
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-api03-...
UPLOAD_API_KEY=<strong-random-secret>

# ===================
# Database
# ===================
# Cloud SQL or Supabase PostgreSQL with pgvector extension
DATABASE_URL=postgresql+asyncpg://user:password@/dbname?host=/cloudsql/project:region:instance
# or for Supabase:
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:6543/postgres

# ===================
# Redis
# ===================
# Cloud Memorystore, Upstash, or Redis Cloud
REDIS_URL=redis://:password@redis-host:6379/0

# ===================
# Auth0
# ===================
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://api.themison.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH_DISABLED=false

# ===================
# Google Cloud Storage
# ===================
GCS_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_TRIAL_DOCUMENTS=themison-trial-documents
GCS_BUCKET_PATIENT_DOCUMENTS=themison-patient-documents
GCS_CREDENTIALS_PATH=                  # Leave empty on GCE/Cloud Run (uses ADC)
# or, if running outside GCP:
GCS_CREDENTIALS_PATH=/secrets/gcs-service-account.json

# ===================
# gRPC RAG Service
# ===================
USE_GRPC_RAG=true
RAG_SERVICE_ADDRESS=rag-service:50051  # Internal Cloud Run / GKE service address

# ===================
# Frontend CORS
# ===================
FRONTEND_URL=https://app.themison.com
ALLOW_ALL_ORIGINS=false
```

### GCS Bucket Configuration

The `GCS_BUCKET_TRIAL_DOCUMENTS` and `GCS_BUCKET_PATIENT_DOCUMENTS` values are **just the bucket name** (not a full URL):

```
GCS_BUCKET_TRIAL_DOCUMENTS=themison-trial-documents
```

This is passed to `gcs.Client.bucket("themison-trial-documents")` internally. Files are stored as blobs like `trials/{trial_id}/{filename}.pdf`.

**Bucket setup:**
1. Create buckets in Google Cloud Console or via `gsutil`:
   ```bash
   gsutil mb -l us-central1 gs://themison-trial-documents
   gsutil mb -l us-central1 gs://themison-patient-documents
   ```
2. Grant the service account (or Cloud Run identity) the `Storage Object Admin` role on both buckets.

### GCS Authentication

Two options:

| Scenario | Configuration |
|----------|--------------|
| **Cloud Run / GCE / GKE** | Leave `GCS_CREDENTIALS_PATH` empty. Uses Application Default Credentials (ADC) from the instance's service account. |
| **Outside GCP** (VM, on-prem) | Set `GCS_CREDENTIALS_PATH=/path/to/service-account-key.json` pointing to a downloaded JSON key file. |

### Storage Auto-Detection

The backend automatically selects the storage backend based on whether `GCS_BUCKET_TRIAL_DOCUMENTS` is set:

```python
# app/dependencies/storage.py
if settings.gcs_bucket_trial_documents:
    return GCSStorageService()      # Production: GCS
else:
    return LocalStorageService()    # Local: filesystem + /local-files/ endpoint
```

No code changes needed between environments.

### Database Requirements

PostgreSQL must have these extensions enabled (handled by `docker/init.sql` locally):

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector
```

For Supabase, pgvector is pre-installed. For Cloud SQL, enable the `pgvector` extension in the Cloud Console.

HNSW indexes for fast vector search are created by `init.sql`. If using a managed database, run the index creation statements manually or via migration:

```sql
CREATE INDEX idx_chunks_embedding_hnsw
ON document_chunks_docling USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Connection Pooling

The backend configures SQLAlchemy async pooling in `app/db/session.py`:
- `pool_size=10`
- `max_overflow=20`
- `pool_recycle=1800` (30 min)
- Statement timeout: 60s

For production with higher traffic, increase `pool_size` and `max_overflow`, or use PgBouncer / Supabase connection pooler.

---

## 3. Configuration Reference

### All Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key for text-embedding-3-small |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `UPLOAD_API_KEY` | Yes | — | API key for `/upload` and `/query` endpoints (sent as `X-API-KEY` header) |
| `DATABASE_URL` | Yes | — | PostgreSQL asyncpg connection string |
| `REDIS_URL` | Yes | `""` | Redis connection URL |
| `AUTH0_DOMAIN` | Prod | `""` | Auth0 tenant domain |
| `AUTH0_AUDIENCE` | Prod | `""` | Auth0 API audience |
| `AUTH0_CLIENT_ID` | Prod | `""` | Auth0 client ID |
| `AUTH0_CLIENT_SECRET` | Prod | `""` | Auth0 client secret |
| `AUTH_DISABLED` | No | `false` | Bypass Auth0 for local testing |
| `GCS_PROJECT_ID` | Prod | `""` | Google Cloud project ID |
| `GCS_BUCKET_TRIAL_DOCUMENTS` | Prod | `""` | GCS bucket name for trial docs |
| `GCS_BUCKET_PATIENT_DOCUMENTS` | Prod | `""` | GCS bucket name for patient docs |
| `GCS_CREDENTIALS_PATH` | No | `""` | Path to GCS service account JSON (empty = ADC) |
| `USE_GRPC_RAG` | No | `false` | Enable gRPC routing to RAG service |
| `RAG_SERVICE_ADDRESS` | No | `localhost:50051` | RAG gRPC service address |
| `FRONTEND_URL` | No | `http://localhost:3000` | Allowed CORS origin |
| `ALLOW_ALL_ORIGINS` | No | `false` | Allow all CORS origins (dev only) |
| `SEMANTIC_CACHE_SIMILARITY_THRESHOLD` | No | `0.90` | Cosine similarity threshold for semantic cache hits |
| `HYBRID_SEARCH_ENABLED` | No | `true` | Enable BM25 + vector hybrid search |
| `RETRIEVAL_TOP_K` | No | `20` | Number of chunks to retrieve |
| `RETRIEVAL_MIN_SCORE` | No | `0.04` | Minimum cosine similarity for vector search |

### RAG Service Environment Variables

These are set in `docker-compose.yml` for the `rag-service` container:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection (shared with backend) |
| `OPENAI_API_KEY` | — | For embeddings |
| `ANTHROPIC_API_KEY` | — | For Claude LLM |
| `GRPC_PORT` | `50051` | gRPC listen port |
| `GRPC_MAX_WORKERS` | `10` | gRPC thread pool size |
| `HYBRID_SEARCH_ENABLED` | `true` | Enable hybrid search |
| `SEMANTIC_CACHE_SIMILARITY_THRESHOLD` | `0.90` | Cache similarity threshold |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Claude model for generation |

---

## 4. Quick Start Cheat Sheet

### Local Docker (full stack)

```bash
# 1. Set API keys in .env
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, ANTHROPIC_API_KEY, UPLOAD_API_KEY
# Set AUTH_DISABLED=true, USE_GRPC_RAG=true

# 2. Start everything
docker-compose up -d --build

# 3. Open Swagger
# http://localhost:8000/docs
```

### Production Deploy

```bash
# 1. Create GCS buckets
gsutil mb gs://themison-trial-documents
gsutil mb gs://themison-patient-documents

# 2. Set all env vars (see section 2 above)
# Key differences from local:
#   AUTH_DISABLED=false
#   GCS_BUCKET_TRIAL_DOCUMENTS=themison-trial-documents
#   GCS_BUCKET_PATIENT_DOCUMENTS=themison-patient-documents
#   FRONTEND_URL=https://app.themison.com
#   ALLOW_ALL_ORIGINS=false

# 3. Deploy backend + rag-service containers
# (Cloud Run, GKE, or docker-compose on a VM)

# 4. Run database migrations if not using Docker init.sql
psql $DATABASE_URL -f docker/init.sql
```

### Reset Local Database

```bash
docker-compose down -v && docker-compose up -d --build
```

This destroys all data (volumes) and re-creates from `docker/init.sql`.
