# 🌍 Database Migration: US → Europe

## Quick Start

### Option 1: Default (Belgium)
```powershell
.\migrate-to-europe.ps1
```

### Option 2: Choose Specific European Region
```powershell
# Frankfurt, Germany
.\migrate-to-europe.ps1 -Zone "europe-west3-a"

# London, UK
.\migrate-to-europe.ps1 -Zone "europe-west2-a"

# Netherlands
.\migrate-to-europe.ps1 -Zone "europe-west4-a"

# Finland (cheapest)
.\migrate-to-europe.ps1 -Zone "europe-north1-a"
```

---

## 📋 What the Script Does

1. ✅ **Exports** database from current US VM (`themison-db-vm`)
2. ✅ **Downloads** backup to your local machine
3. ✅ **Creates** new VM in European region (`themison-db-vm-eu`)
4. ✅ **Deploys** PostgreSQL + Redis via Docker
5. ✅ **Imports** database data to new VM
6. ✅ **Provides** new connection details

---

## ⏱️ Estimated Time
- **Total:** ~10-15 minutes
- Database export: 2-3 min
- VM creation: 3-4 min
- Service setup: 2-3 min
- Database import: 3-5 min

---

## 🌍 European Region Options

| Region | Location | Zone | Latency (EU) | Cost |
|--------|----------|------|--------------|------|
| `europe-west1` | Belgium | `europe-west1-b` | Low | Medium |
| `europe-west2` | London, UK | `europe-west2-a` | Low | Higher |
| `europe-west3` | Frankfurt, DE | `europe-west3-a` | Low | Medium |
| `europe-west4` | Netherlands | `europe-west4-a` | Low | Medium |
| `europe-north1` | Finland | `europe-north1-a` | Medium | **Lowest** |

**Recommendation:** `europe-west1-b` (Belgium) - Best balance of cost/latency

---

## 📝 Pre-Migration Checklist

- [ ] Ensure `docker-compose.prod.yml` exists
- [ ] Ensure `pre-init.sql` exists (optional)
- [ ] Have gcloud CLI authenticated
- [ ] Have backup of any important data
- [ ] Notify users of potential downtime

---

## 🚀 Running the Migration

### Step 1: Run Migration Script
```powershell
cd c:\Users\JONAATH\.gemini\antigravity\scratch\core-backend.V4
.\migrate-to-europe.ps1
```

### Step 2: Wait for Completion
The script will:
- Show progress for each step
- Display any errors
- Provide new connection details at the end

### Step 3: Update Environment Variables
After migration, update `.env.production` with the **new Internal IP**:

```env
# OLD (US):
SUPABASE_DB_URL=postgresql+asyncpg://postgres:postgres@10.128.0.2:5432/postgres
REDIS_URL=redis://10.128.0.2:6379

# NEW (Europe) - Use IP from migration output:
SUPABASE_DB_URL=postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres
REDIS_URL=redis://10.132.0.2:6379
```

**Note:** The new IP will be displayed after migration completes.

---

## ✅ Post-Migration Verification

### 1. Test Database Connection
```powershell
# SSH into new VM
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b

# Check containers
docker ps

# Verify database
docker exec -it postgres-db psql -U postgres -d postgres -c "\dt"

# Count records in a table
docker exec -it postgres-db psql -U postgres -d postgres -c "SELECT COUNT(*) FROM trials;"
```

### 2. Test Backend Connection
Update your backend's `.env.production` and test connection.

### 3. Verify Data Integrity
```sql
-- Check table counts
SELECT 
    schemaname,
    tablename,
    (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
FROM (
    SELECT 
        schemaname, 
        tablename,
        query_to_xml(format('select count(*) as cnt from %I.%I', schemaname, tablename), false, true, '') as xml_count
    FROM pg_tables
    WHERE schemaname = 'public'
) t;
```

---

## 🗑️ Cleanup Old US VM

**⚠️ Only after verifying the European VM works!**

```powershell
# Delete old US VM
gcloud compute instances delete themison-db-vm --project=braided-visitor-484216-i0 --zone=us-central1-a --quiet

# Verify deletion
gcloud compute instances list --project=braided-visitor-484216-i0
```

---

## 🆘 Troubleshooting

### Issue: "Permission Denied" during export
```powershell
# Ensure you're authenticated
gcloud auth login
gcloud config set project braided-visitor-484216-i0
```

### Issue: VM Already Exists
The script will prompt you to delete and recreate. Choose `yes` to proceed.

### Issue: Database Import Fails
```powershell
# Check logs
gcloud compute ssh themison-db-vm-eu --zone=europe-west1-b
docker logs postgres-db

# Manually try import
docker exec -it postgres-db psql -U postgres -d postgres < /tmp/database_backup.sql
```

### Issue: Connection Timeout
```powershell
# Ensure VM is running
gcloud compute instances list --project=braided-visitor-484216-i0

# Check firewall rules
gcloud compute firewall-rules list --project=braided-visitor-484216-i0
```

---

## 📊 Cost Comparison

**Current Setup (US):**
- VM: `e2-medium` in `us-central1-a`
- Cost: ~$25/month

**After Migration (Europe):**
- VM: `e2-medium` in `europe-west1-b`
- Cost: ~$27/month (+8% for EU region)

**Cheapest EU Option:**
- VM: `e2-medium` in `europe-north1-a` (Finland)
- Cost: ~$23/month (-8% vs US)

---

## 🔐 Security Notes

- Internal IP will change (e.g., from `10.128.0.2` to `10.132.0.2`)
- Firewall rules remain the same (SSH only)
- Database remains internal-only
- No public access to PostgreSQL or Redis

---

## 📞 Support

If migration fails:
1. Check migration logs in terminal
2. Verify gcloud authentication
3. Check GCP quotas for European region
4. Ensure billing is enabled for the project

**Emergency Rollback:**
The old US VM (`themison-db-vm`) remains running until you manually delete it.

---

## ✨ Summary

**Before Migration:**
- VM: `themison-db-vm` in `us-central1-a`
- IP: `10.128.0.2`

**After Migration:**
- VM: `themison-db-vm-eu` in `europe-west1-b` (or chosen zone)
- IP: New IP (displayed after migration)
- Both VMs running (until you delete old one)

---

**Migration Date:** `<pending>`  
**Status:** Ready to execute 🚀
