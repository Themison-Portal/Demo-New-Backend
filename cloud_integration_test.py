import httpx
import time
import uuid
import sys
import os

# Configuration
BASE_URL = "https://core-backend-eu-573lfhdaza-ew.a.run.app"
API_KEY = "themison-test-key-2026"

if not API_KEY:
    print("Error: UPLOAD_API_KEY environment variable not set")
    sys.exit(1)

def run_test():
    with httpx.Client(timeout=30.0) as client:
        # 1. Health Check
        print("Checking Backend Health...")
        try:
            resp = client.get(f"{BASE_URL}/")
            print(f"Health Response: {resp.status_code} - {resp.json()}")
        except Exception as e:
            print(f"Health Check Failed: {e}")
            return

        # 2. Trigger Ingestion
        print("\nTriggering PDF Ingestion (Verifies Backend -> Redis -> RAG Service connection)...")
        doc_id = str(uuid.uuid4())
        payload = {
            "document_url": "https://gpfyejxokywdkudkeywv.supabase.co/storage/v1/object/public/trial-documents/1c8bab48-aed9-471d-bb49-030170ae589d/1764149955812-protocol_oncology.pdf",
            "document_id": doc_id,
            "chunk_size": 1000
        }
        headers = {"X-API-KEY": API_KEY}
        
        try:
            resp = client.post(f"{BASE_URL}/upload/upload-pdf", json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"Upload Failed: {resp.status_code} - {resp.text}")
                return
            
            job_data = resp.json()
            job_id = job_data["job_id"]
            print(f"Job Created: {job_id} for Document: {doc_id}")
        except Exception as e:
            print(f"Upload Request Failed: {e}")
            return

        # 3. Poll for Status
        print("\nPolling for Ingestion Status (Verifies RAG Service processing and DB storage)...")
        max_retries = 30
        for i in range(max_retries):
            try:
                resp = client.get(f"{BASE_URL}/upload/status/{job_id}")
                status_data = resp.json()
                
                status = status_data["status"]
                stage = status_data.get("current_stage", "unknown")
                progress = status_data.get("progress_percent", 0)
                message = status_data.get("message", "")
                
                print(f"[{i+1}/{max_retries}] Status: {status} | Stage: {stage} | Progress: {progress}% | Message: {message}")
                
                if status == "complete":
                    print("\nSUCCESS! Ingestion complete.")
                    print(f"Final Result: {json.dumps(status_data['result'], indent=2)}")
                    return
                elif status == "error":
                    print(f"\nFAILED! Error: {status_data.get('error')}")
                    return
                
                time.sleep(5)
            except Exception as e:
                print(f"Polling failed: {e}")
                time.sleep(5)

        print("\nTest timed out waiting for completion.")

if __name__ == "__main__":
    import json
    run_test()
