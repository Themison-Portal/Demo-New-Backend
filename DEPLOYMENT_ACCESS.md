# 🔐 Deployment Access & Verification Keys

## 1. Google Cloud Resources (Verification)

**✅ Database Server (Active - Europe):**
[View VM Instance in GCP Console](https://console.cloud.google.com/compute/instancesDetail/zones/europe-west1-b/instances/themison-db-vm-eu?project=braided-visitor-484216-i0)
*   **Status:** Running
*   **Region:** europe-west1-b (Belgium)
*   **Internal IP:** `10.132.0.2`

**🗑️ Old Server (Deleted - US):**
[View Deleted Instance](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/themison-db-vm?project=braided-visitor-484216-i0)
*   **Status:** Deleted (Billing Stopped)

---

## 2. Configuration for Backend Deployment

Use these environment variables when deploying the backend to **Cloud Run** or another service.

**⚠️ CRITICAL:** The backend must be deployed in the **`europe-west1`** region to verify connectivity to these internal IPs.

| Variable | Value |
| :--- | :--- |
| `SUPABASE_DB_URL` | `postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres` |
| `REDIS_URL` | `redis://10.132.0.2:6379` |
| `SUPABASE_DB_PASSWORD` | `postgres` |

---

## 3. Technical Access (SSH)

To verify the Docker containers manually:

**Terminal Command:**
```bash
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b
```

**Verification Commands (inside VM):**
```bash
# Check if Database and Redis are running
sudo docker ps 

# Check Database tables (Should show 27 tables)
sudo docker exec postgres-db psql -U postgres -d postgres -c "\dt"
```
