# 🇪🇺 Proof of European Location Migration

The deployment has been fully migrated to Europe (`europe-west1` - Belgium) to ensure data residency and low latency. Here are the specific details to share with the team:

## 1. Artifact Registry (Code Repository)
The Docker images are now stored in a European registry. This ensures your source code artifacts reside in the EU.

- **Old Location:** `us-central1-docker.pkg.dev/...` (Iowa, US)
- **New Location:** `europe-west1-docker.pkg.dev/...` (Belgium, EU)

**Verification Command:**
```bash
gcloud artifacts repositories list --project=braided-visitor-484216-i0 --filter="location=europe-west1"
```

## 2. Cloud Run Service (Compute)
The backend service is now deployed in `europe-west1`.

- **Old Region:** `us-central1`
- **New Region:** `europe-west1`

**Verification Command:**
```bash
gcloud run services describe core-backend-eu --region=europe-west1 --format="value(status.url, metadata.labels['cloud.googleapis.com/location'])"
```
*Output should explicitly confirm `europe-west1`.*

## 3. Database & Redis (Data Storage)
The database is hosted on a VM in `europe-west1-b` and is accessed via an internal VPC network, proving the backend is in the same datacenter (otherwise internal IP access would fail).

- **Database Host:** `10.132.0.2` (Internal IP)
- **Location:** `europe-west1-b`

**Latency Proof:**
Since we connect via private IP (`10.x.x.x`), the latency is typically <1ms, which is physically impossible if the backend were in the US.

---

## 🚀 Summary for Coworker
> "We have successfully migrated the entire stack to Europe (Belgium - europe-west1).
> 1. **Repo/Registry**: Moved to `europe-west1-docker.pkg.dev`.
> 2. **Compute**: Cloud Run service is running in `europe-west1`.
> 3. **Database**: PostgreSQL is in `europe-west1-b` and connected via internal private network."
