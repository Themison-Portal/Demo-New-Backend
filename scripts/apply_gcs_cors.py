import os
import json
from google.cloud import storage
from dotenv import load_dotenv

def apply_cors():
    load_dotenv()
    
    project_id = os.getenv("GCS_PROJECT_ID")
    bucket_names = [
        os.getenv("GCS_BUCKET_TRIAL_DOCUMENTS"),
        os.getenv("GCS_BUCKET_PATIENT_DOCUMENTS")
    ]
    
    # Filter out None/empty bucket names
    bucket_names = [b for b in bucket_names if b]
    
    if not bucket_names:
        print("Error: No GCS buckets found in .env")
        return

    # Load CORS policy
    cors_file = "gcs-cors.json"
    if not os.path.exists(cors_file):
        print(f"Error: {cors_file} not found")
        return
        
    with open(cors_file, "r") as f:
        cors_configuration = json.load(f)

    client = storage.Client(project=project_id)

    for bucket_name in bucket_names:
        print(f"Applying CORS to bucket: {bucket_name}...")
        try:
            bucket = client.get_bucket(bucket_name)
            bucket.cors = cors_configuration
            bucket.patch()
            print(f"Successfully applied CORS to {bucket_name}")
        except Exception as e:
            print(f"Failed to apply CORS to {bucket_name}: {e}")

if __name__ == "__main__":
    apply_cors()
