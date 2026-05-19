# Database Deployment - Themison (Europe)

Your PostgreSQL database is now running on a secured Google Cloud VM in Europe for optimized performance and GDPR compliance.

## 🟢 System Status (Verified - European VM)

- **Project**: `braided-visitor-484216-i0` (Themison)
- **VM Name**: `themison-db-vm-eu` (Zone: `europe-west1-b`)
- **Internal IP**: `10.132.0.2`
- **Database**: `postgres-db` (PostgreSQL 16 + pgvector)
- **Redis**: `themison-redis` (Redis 7)
- **Security**: Port 5432 is **NOT** exposed to the internet. Access is via SSH tunnel or VPC Connector only.

## 🔑 How to Connect (Securely)

To connect using pgAdmin, DBeaver, or code from your local machine, creating a secure tunnel is the best practice.

### Step 1: Open SSH Tunnel
Run this command in your terminal:

```powershell
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b --ssh-flag="-L 5432:localhost:5432"
```

Keep this terminal window open.

### Step 2: Connect
Use these settings in your database client:
- **Host**: `localhost`
- **Port**: `5432`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `postgres`

## 🛠 Management Commands

### Check Status
```powershell
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b --command="sudo docker ps"
```

### View Logs
```powershell
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b --command="sudo docker logs postgres-db --tail 50"
```

### Restart Database
```powershell
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b --command="sudo docker restart postgres-db"
```

## 🔄 Re-Importing Schema

If you need to update the schema later:

1. Copy file to VM:
   ```powershell
   gcloud compute scp schema.sql themison-db-vm-eu:init.sql --project=braided-visitor-484216-i0 --zone=europe-west1-b
   ```

2. Execute inside container:
   ```powershell
   gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b --command="sudo docker exec -i postgres-db psql -U postgres -d postgres -f /init.sql"
   ```

## 📝 Infrastructure Note
The backend connects to this database via the **VPC Connector** `themison-connector` using the internal IP `10.132.0.2`.
The old US VM (`themison-db-vm`) has been deleted to save on costs.
