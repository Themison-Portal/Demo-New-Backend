# Quick European VM Setup Fix

**Issue:** Migration script created VM but Docker containers may not be running.

**Solution:** Manually start the containers

## Step 1: Upload docker-compose file (if not already done)
```powershell
gcloud compute scp docker-compose.prod.yml themison-db-vm-eu:/tmp/docker-compose.yml --project=braided-visitor-484216-i0 --zone=europe-west1-b
gcloud compute scp pre-init.sql themison-db-vm-eu:/tmp/pre-init.sql --project=braided-visitor-484216-i0 --zone=europe-west1-b
gcloud compute scp database_backup.dump themison-db-vm-eu:/tmp/database_backup.dump --project=braided-visitor-484216-i0 --zone=europe-west1-b
```

## Step 2: SSH into VM and start containers
```powershell
gcloud compute ssh themison-db-vm-eu --project=braided-visitor-484216-i0 --zone=europe-west1-b
```

## Step 3: Inside VM, run:
```bash
# Install docker-compose
sudo mkdir -p /usr/local/bin
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create directories
sudo mkdir -p /var/lib/postgresql/data /var/lib/redis/data /docker-entrypoint-initdb.d

# Copy pre-init script
sudo cp /tmp/pre-init.sql /docker-entrypoint-initdb.d/ 2>/dev/null || true

# Start services
cd /tmp
sudo docker-compose -f docker-compose.yml up -d

# Wait and check
sleep 15
sudo docker ps

# Import database
sudo docker cp /tmp/database_backup.dump postgres-db:/tmp/database_backup.dump
sudo docker exec postgres-db pg_restore -U postgres -d postgres --clean --if-exists -F c /tmp/database_backup.dump

# Verify
sudo docker exec postgres-db psql -U postgres -d postgres -c "\dt"
```

## Step 4: Verification
```bash
# Check containers are running
sudo docker ps

# Check database connection
sudo docker exec postgres-db psql -U postgres -d postgres -c "SELECT COUNT(*) FROM trials;"
```

## Exit VM
```bash
exit
```

## ✅ Migration Complete!
New connection details are already in `.env.production` using IP `10.132.0.2`
