# Database Deployment Handoff - Themison Portal

## ✅ Task Completed: PostgreSQL Database Deployed on Google Cloud

---

## 📊 Deployment Summary

| Resource | Status | Location |
|----------|--------|----------|
| PostgreSQL Database | ✅ Running | GCP VM (Docker) |
| Redis Cache | ✅ Running | GCP VM (Docker) |
| Schema Imported | ✅ Complete | 27 tables created |
| Supabase Roles | ✅ Created | Compatible with legacy code |

---

## 🔗 Google Cloud Console Links

### VM Instance (Database Server) - 🇪🇺 EUROPE
**Direct Link:**
```
https://console.cloud.google.com/compute/instancesDetail/zones/europe-west1-b/instances/themison-db-vm-eu?project=braided-visitor-484216-i0
```

**Legacy US VM (soon to be deleted):**
```
https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/themison-db-vm?project=braided-visitor-484216-i0
```

### Project Overview
```
https://console.cloud.google.com/home/dashboard?project=braided-visitor-484216-i0
```

---

## 🔐 Database Connection Credentials

### For Backend Application (Production)

**Connection String:**
```
postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres
```

**Individual Parameters:**
- **Host:** `10.132.0.2` (Internal GCP IP - 🇪🇺 Europe)
- **Port:** `5432`
- **Database:** `postgres`
- **Username:** `postgres`
- **Password:** `postgres`

### Redis Cache
```
redis://10.132.0.2:6379
```

⚠️ **Note:** Redis is currently configured for localhost only. If the backend runs on Cloud Run (different server), we need to update `docker-compose.prod.yml` to expose Redis on `0.0.0.0` instead of `127.0.0.1`.

---

## 🛠️ Environment Variables for Production

**Complete `.env.production` Configuration:**

```env
OPENAI_API_KEY=sk-proj-REDACTED
ANTHROPIC_API_KEY=sk-ant-REDACTED
REDIS_URL=redis://10.132.0.2:6379
FRONTEND_URL=http://localhost:8080
SUPABASE_URL=https://nidpneaqxghqueniodus.supabase.co
SUPABASE_SERVICE_KEY=REDACTED
SUPABASE_ANON_KEY=REDACTED
SUPABASE_DB_URL=postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres
SUPABASE_DB_PASSWORD=postgres
ENVIRONMENT=production
```

**Key Database Configuration:**
- ✅ `SUPABASE_DB_URL`: Points to GCP VM database at `10.132.0.2:5432` (🇪🇺 Europe)
- ✅ `SUPABASE_DB_PASSWORD`: `postgres`
- ✅ `REDIS_URL`: Points to Redis on same VM at `10.132.0.2:6379` (🇪🇺 Europe)



---

## 🔧 VM Configuration

- **VM Name:** `themison-db-vm-eu` 🇪🇺
- **Region:** `europe-west1` (Belgium)
- **Zone:** `europe-west1-b`
- **Machine Type:** `e2-medium`
- **OS:** Container-Optimized OS (with Docker pre-installed)
- **Internal IP:** `10.132.0.2`
- **Firewall:** SSH only (Port 22), Database is internal-only for security
- **Migration Date:** February 13, 2026

---

## 📦 Running Services (Docker Containers)

| Service | Container Name | Port | Image |
|---------|---------------|------|-------|
| PostgreSQL | `postgres-db` | 5432 | `pgvector/pgvector:pg16` |
| Redis | `themison-redis` | 6379 | `redis:7-alpine` |

---

## 📝 Database Schema

- **Total Tables:** 27
- **Key Tables:** `trials`, `members`, `organizations`, `patients`, `visits`, `visit_documents`, etc.
- **Extensions:** `pgvector` (for AI embeddings), `uuid-ossp`, `pgcrypto`
- **Supabase Roles:** `anon`, `authenticated`, `service_role`, `authenticator`, `supabase_admin`

---

## 🔒 Security Configuration

### Network Access
- ✅ **SSH Access:** Enabled (Port 22)
- ✅ **Database:** Internal-only (127.0.0.1 binding in production)
- ✅ **Redis:** Internal-only (127.0.0.1 binding in production)
- ❌ **Public Database Access:** Disabled for security

### Firewall Rules
- `allow-ssh-db`: Allows SSH connections to VM

---

## 🚀 Next Steps for Backend Deployment

### Option 1: Deploy Backend to Cloud Run (Recommended)
1. Ensure backend uses connection string: `postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres`
2. **Important:** Update `docker-compose.prod.yml` to change Redis binding from `127.0.0.1:6379:6379` to `0.0.0.0:6379:6379`
3. Deploy backend using `gcloud run deploy --region=europe-west1` (same region as database)
4. Ensure Cloud Run service is in the **same VPC** as the database VM

### Option 2: Run Backend on Same VM (Alternative)
1. SSH into VM: `gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b`
2. Add backend service to `docker-compose.yml`
3. Run `docker-compose up -d`

---

## 🧪 How to Verify Database

### SSH Tunnel Access (for DBeaver/pgAdmin)
```powershell
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b --ssh-flag="-L 5432:localhost:5432"
```

Then connect to `localhost:5432` with credentials above.

### Direct VM Access
```bash
# SSH into European VM
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b

# Check running containers
docker ps

# Access database CLI
docker exec -it postgres-db psql -U postgres -d postgres

# List tables
\dt
```

---

## 📂 Files for Reference

- **`schema.sql`** - Full database schema (with Supabase extensions commented out)
- **`pre-init.sql`** - Supabase roles creation script
- **`docker-compose.prod.yml`** - Production Docker configuration
- **`.env.production`** - Production environment variables (updated)
- **`setup-db-vm.ps1`** - Automated deployment script
- **`DB-DEPLOY-README.md`** - Database management guide

---

## ⚠️ Known Issues / Notes

1. **Supabase Extensions Removed:** `pg_net`, `pg_graphql`, and `supabase_vault` are commented out in `schema.sql` because they are not available in the standard `pgvector` image.
2. **Redis Configuration:** Currently localhost-only. Needs update if backend runs on separate server.
3. **SSL/TLS:** Database connections are currently unencrypted. Consider adding SSL for production.

---

## 👤 Support

For questions or issues:
- Repository: `https://github.com/Themison-Portal/core-backend.V4`
- Database Admin: Available via SSH to VM
- Logs: `docker logs postgres-db` or `docker logs themison-redis`

---

**Deployment Date:** February 10 2026  
**Deployed By:** Jonathan  
**Status:** ✅ Ready for Backend Integration
