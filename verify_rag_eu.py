import httpx
import time
import uuid
import sys
import os
import json
from dotenv import load_dotenv

# Load env to get the key we just synced
load_dotenv()

# Configuration
BASE_URL = "https://core-backend-eu-768873408671.europe-west1.run.app"
API_KEY = os.getenv("UPLOAD_API_KEY")

if not API_KEY:
    print("Error: UPLOAD_API_KEY not found in .env")
    sys.exit(1)

def run_test():
    print(f"--- RAG Verification (Europe) ---")
    print(f"Target: {BASE_URL}")
    
    with httpx.Client(timeout=60.0) as client:
        # 1. Health Check
        print("\n[1/3] Verifying Backend Health...")
        try:
            resp = client.get(f"{BASE_URL}/health")
            print(f"Response: {resp.status_code} - {resp.json()}")
        except Exception as e:
            print(f"[ERROR] Health Check Failed: {e}")
            return

        # 2. Trigger Ingestion
        print("\n[2/3] Triggering Async PDF Ingestion...")
        # Note: We use a random UUID. The backend will create this document 
        # in the DB if it doesn't exist, or just process it.
        doc_id = str(uuid.uuid4())
        payload = {
            "document_url": "https://gpfyejxokywdkudkeywv.supabase.co/storage/v1/object/public/trial-documents/1c8bab48-aed9-471d-bb49-030170ae589d/1764149955812-protocol_oncology.pdf",
            "document_id": doc_id,
            "chunk_size": 800
        }
        headers = {"X-API-KEY": API_KEY}
        
        try:
            resp = client.post(f"{BASE_URL}/upload/upload-pdf", json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"[ERROR] Upload Failed: {resp.status_code} - {resp.text}")
                return
            
            job_data = resp.json()
            job_id = job_data["job_id"]
            print(f"[SUCCESS] Job Created: {job_id}")
            print(f"   Document ID: {doc_id}")
        except Exception as e:
            print(f"[ERROR] Upload Request Failed: {e}")
            return

        # 3. Poll for Status
        print("\n[3/3] Polling Ingestion Status (this verifies RAG Service -> DB)...")
        max_retries = 40
        for i in range(max_retries):
            try:
                resp = client.get(f"{BASE_URL}/upload/status/{job_id}")
                if resp.status_code != 200:
                    print(f"   Status check failed: {resp.status_code}")
                    time.sleep(5)
                    continue

                status_data = resp.json()
                status = status_data["status"]
                stage = status_data.get("current_stage", "queued")
                progress = status_data.get("progress_percent", 0)
                message = status_data.get("message", "")
                
                print(f"   [{i+1}/{max_retries}] Status: {status} | Stage: {stage} | Progress: {progress}% | {message}")
                
                if status == "completed":
                    print("\n[COMPLETE] RAG Pipeline is fully functional.")
                    print(f"   Result: {json.dumps(status_data.get('result', {}), indent=2)}")
                    return
                elif status == "failed":
                    print(f"\n[FAILED] INGESTION FAILED!")
                    print(f"   Error: {status_data.get('error')}")
                    return
                
                time.sleep(10)
            except Exception as e:
                print(f"   Polling error: {e}")
                time.sleep(10)

        print("\n⚠️ Test timed out. Ingestion is likely still running in the background.")

if __name__ == "__main__":
    run_test()
