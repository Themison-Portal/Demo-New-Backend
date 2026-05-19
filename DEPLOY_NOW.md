# 🚀 Deploy to Your Google Cloud Project - Step by Step

Your Google Cloud project is already set up: **braided-visitor-484216-i0**

## Quick Deployment Steps

### Step 1: Enable Required APIs

```powershell
# Enable Compute Engine API
gcloud services enable compute.googleapis.com --project=braided-visitor-484216-i0

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com --project=braided-visitor-484216-i0
```

### Step 2: Create Firewall Rules

```powershell
# Allow HTTP traffic
gcloud compute firewall-rules create allow-themison-http `
    --project=braided-visitor-484216-i0 `
    --allow=tcp:80,tcp:8000 `
    --target-tags=http-server `
    --description="Allow HTTP traffic to Themison backend"

# Allow HTTPS traffic
gcloud compute firewall-rules create allow-themison-https `
    --project=braided-visitor-484216-i0 `
    --allow=tcp:443 `
    --target-tags=https-server `
    --description="Allow HTTPS traffic to Themison backend"
```

### Step 3: Create VM Instance

```powershell
# Create VM with Docker pre-installed
gcloud compute instances create themison-backend-vm `
    --project=braided-visitor-484216-i0 `
    --zone=us-central1-a `
    --machine-type=e2-medium `
    --image-family=cos-stable `
    --image-project=cos-cloud `
    --boot-disk-size=50GB `
    --boot-disk-type=pd-balanced `
    --tags=http-server,https-server `
    --metadata=startup-script='#!/bin/bash
echo "Themison VM is ready"
docker --version'
```

### Step 4: Get VM External IP

```powershell
gcloud compute instances describe themison-backend-vm `
    --zone=us-central1-a `
    --project=braided-visitor-484216-i0 `
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### Step 5: Create Secrets in Secret Manager

You'll need these API keys ready:
- OpenAI API Key
- Anthropic API Key
- Supabase URL
- Supabase Service Key
- Supabase Anon Key

```powershell
# Create secrets (you'll be prompted for values)
echo "YOUR_OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=- --project=braided-visitor-484216-i0

echo "YOUR_ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=- --project=braided-visitor-484216-i0

echo "YOUR_SUPABASE_URL" | gcloud secrets create supabase-url --data-file=- --project=braided-visitor-484216-i0

echo "YOUR_SUPABASE_SERVICE_KEY" | gcloud secrets create supabase-service-key --data-file=- --project=braided-visitor-484216-i0

echo "YOUR_SUPABASE_ANON_KEY" | gcloud secrets create supabase-anon-key --data-file=- --project=braided-visitor-484216-i0
```

### Step 6: Grant VM Access to Secrets

```powershell
# Get project number
$PROJECT_NUMBER = gcloud projects describe braided-visitor-484216-i0 --format='value(projectNumber)'
$SERVICE_ACCOUNT = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

# Grant access to each secret
gcloud secrets add-iam-policy-binding openai-api-key `
    --member="serviceAccount:$SERVICE_ACCOUNT" `
    --role="roles/secretmanager.secretAccessor" `
    --project=braided-visitor-484216-i0

gcloud secrets add-iam-policy-binding anthropic-api-key `
    --member="serviceAccount:$SERVICE_ACCOUNT" `
    --role="roles/secretmanager.secretAccessor" `
    --project=braided-visitor-484216-i0

gcloud secrets add-iam-policy-binding supabase-url `
    --member="serviceAccount:$SERVICE_ACCOUNT" `
    --role="roles/secretmanager.secretAccessor" `
    --project=braided-visitor-484216-i0

gcloud secrets add-iam-policy-binding supabase-service-key `
    --member="serviceAccount:$SERVICE_ACCOUNT" `
    --role="roles/secretmanager.secretAccessor" `
    --project=braided-visitor-484216-i0

gcloud secrets add-iam-policy-binding supabase-anon-key `
    --member="serviceAccount:$SERVICE_ACCOUNT" `
    --role="roles/secretmanager.secretAccessor" `
    --project=braided-visitor-484216-i0
```

### Step 7: Deploy Application to VM

```powershell
# SSH into VM and deploy
gcloud compute ssh themison-backend-vm --zone=us-central1-a --project=braided-visitor-484216-i0
```

Once inside the VM, run:

```bash
# Clone repository
git clone https://github.com/Themison-Portal/core-backend.V4.git
cd core-backend.V4

# Create .env.production file
cat > .env.production << 'EOF'
OPENAI_API_KEY=$(gcloud secrets versions access latest --secret="openai-api-key")
ANTHROPIC_API_KEY=$(gcloud secrets versions access latest --secret="anthropic-api-key")
SUPABASE_URL=$(gcloud secrets versions access latest --secret="supabase-url")
SUPABASE_SERVICE_KEY=$(gcloud secrets versions access latest --secret="supabase-service-key")
SUPABASE_ANON_KEY=$(gcloud secrets versions access latest --secret="supabase-anon-key")
SUPABASE_DB_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
SUPABASE_DB_PASSWORD=postgres
REDIS_URL=redis://redis:6379
FRONTEND_URL=https://your-frontend-domain.com
ENVIRONMENT=production
EOF

# Start Docker containers
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker ps

# View logs
docker-compose logs -f
```

### Step 8: Access Your Application

Get your VM's external IP and access:
- **API**: `http://YOUR_VM_IP:8000`
- **Health Check**: `http://YOUR_VM_IP:8000/health`
- **API Docs**: `http://YOUR_VM_IP:8000/docs`

---

## 🎯 One-Command Deployment (Automated)

Or simply run the automated script:

```powershell
.\deploy-gcp.ps1 -ProjectId "braided-visitor-484216-i0"
```

This will execute all the steps above automatically!

---

## ✅ Verification

After deployment, verify everything is working:

```powershell
# Get VM IP
$VM_IP = gcloud compute instances describe themison-backend-vm `
    --zone=us-central1-a `
    --project=braided-visitor-484216-i0 `
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Test health endpoint
curl "http://$VM_IP:8000/health"
```

---

## 🔧 Management Commands

```powershell
# View VM status
gcloud compute instances list --project=braided-visitor-484216-i0

# SSH into VM
gcloud compute ssh themison-backend-vm --zone=us-central1-a --project=braided-visitor-484216-i0

# View application logs
gcloud compute ssh themison-backend-vm --zone=us-central1-a --project=braided-visitor-484216-i0 --command="docker-compose logs -f"

# Stop VM
gcloud compute instances stop themison-backend-vm --zone=us-central1-a --project=braided-visitor-484216-i0

# Start VM
gcloud compute instances start themison-backend-vm --zone=us-central1-a --project=braided-visitor-484216-i0

# Delete VM (when no longer needed)
gcloud compute instances delete themison-backend-vm --zone=us-central1-a --project=braided-visitor-484216-i0
```

---

**Your Project**: `braided-visitor-484216-i0`  
**Ready to Deploy**: ✅  
**Estimated Time**: 15-20 minutes
