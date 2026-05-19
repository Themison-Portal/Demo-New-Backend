import httpx
try:
    resp = httpx.get("https://core-backend-eu-768873408671.europe-west1.run.app/health", timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
