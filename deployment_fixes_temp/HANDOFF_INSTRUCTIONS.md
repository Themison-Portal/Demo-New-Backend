# 🚀 Backend Handoff & Connection Guide

## ✅ Current Status: MIGRATION COMPLETE (Europe-West1)
The backend is successfully deployed in **Europe-West1** (`core-backend-trials`) and is fully connected to the **NEW internal database VM** (`10.132.0.2`). The old Staging environment in `us-central1` is deprecated.

---

## 🛠️ Action Required (For The Backend / DevOps)

To connect the backend to the new cost-saving infrastructure, please perform the following update:

### 1. Redeploy to Europe (Critical)
The new database is in `europe-west1` to reduce latency and costs. The backend must be moved there.

*   **Service Name:** `core-backend-staging` (or create new `core-backend-prod`)
*   **Target Region:** `europe-west1`
*   **VPC Connector:** `themison-connector` (Already created in `europe-west1`)

### 2. Update Environment Variables
Set these variables during deployment to point to the new internal infrastructure:

| Variable | Value | Description |
| :--- | :--- | :--- |
| **DATABASE_URL** | `postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres` | Internal VM IP |
| **REDIS_URL** | `redis://10.132.0.2:6379` | Internal VM IP |
| **SUPABASE_DB_URL** | `postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres` | Legacy support |

### 3. Deploy Command (Example)
```bash
gcloud run deploy core-backend-prod \
  --image=us-central1-docker.pkg.dev/braided-visitor-484216-i0/cloud-run-source-deploy/core-backend:clean-build-v2 \
  --region=europe-west1 \
  --vpc-connector=themison-connector \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres,REDIS_URL=redis://10.132.0.2:6379" \
  --allow-unauthenticated
```

---

## 📊 Infrastructure Details

*   **Database VM:** `themison-db-vm-eu` (Zone: `europe-west1-b`)
*   **Internal IP:** `10.132.0.2` (Use this for backend connection)
*   **External IP:** `34.77.93.209` (Use this for SSH tunneling/debugging)
*   **VPC Connector:** `themison-connector` (Region: `europe-west1`)

---

### Deployment Fixes Applied (Feb 2026)
1. **Bypassed `start.sh`**: The `start.sh` script had Windows line ending issues (`\r`), causing crashes. Deployment now invokes `python -m uvicorn` directly in `service_final.yaml` CMD override.
2. **Increased Resources**: ML models (Sentence Transformers) caused OOM kills on 512Mi. Increased strict limits to **4Gi RAM** and **2 vCPU**.
3. **Internal Firewall**: Added `iptables` allow rule on VM for `10.8.0.0/28` (VPC Connector range).
4. **Hardcoded Config**: Using `app/config_hardcoded.py` to bypass Pydantic environment validation issues.

### Reverting to Standard Deployment
When refactoring, ensure:
1. `start.sh` is saved with **LF (Unix)** line endings.
2. Environment variables are correctly injected via Secret Manager.
3. Memory limits remain high (2Gi+) for ML workloads.

### 4. Configuration Note (Important)
Due to Cloud Run reliability issues, the current deployment uses a **hardcoded configuration file** (`app/config_hardcoded.py`) copied over `app/config.py` during build.
- This ensures all secrets (`OPENAI_API_KEY`, etc.) are present and Pydantic validation passes.
- **To change configuration:** You must update `app/config_hardcoded.py` (or revert Dockerfile to use standard `config.py`) and **rebuild the image`.
- **Long-term fix:** Debug Cloud Run secret injection and revert Dockerfile to use standard `config.py` with Secret Manager.

## 🔗 How to Verify After Deployment (Live Trials)
1. **Live URL (Active)**:
   `https://core-backend-trials-768873408671.europe-west1.run.app`
2. **Documentation**:
   [Swagger UI](https://core-backend-trials-768873408671.europe-west1.run.app/docs)
3. **Health Check**:
   `curl https://core-backend-trials-768873408671.europe-west1.run.app/` -> Returns `{"status": "ok"}`
   (Note: API endpoints are mounted at root, e.g., `/query`, `/auth`, `/upload`).

## 🌐 Network Infrastructure (Critical)
*   **Access:** Publicly accessible (IAM `allUsers` enabled).
*   **Outbound Connectivity:** **Cloud NAT (`themison-nat`)** is configured on `themison-router` in `europe-west1`. This allows the Cloud Run service to reach external APIs (HuggingFace, OpenAI) reliably via a stable IP, correcting previous timeout issues.
*   **Internal Connectivity:** **VPC Connector (`themison-connector`)** allows access to the database VM (`10.132.0.2`).

## 🧹 Cleanup (Cost Saving)
- To stop the service: `gcloud run services delete core-backend-trials`
- To stop the DB VM: `gcloud compute instances stop gpu-instance-1 --zone=europe-west1-b`
- **Important:** To stop Cloud NAT costs (~$1/day), remove the NAT gateway if trials end:
  `gcloud compute routers nats delete themison-nat --router=themison-router --region=europe-west1`
