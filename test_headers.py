import httpx

BASE_URL = "https://core-backend-eu-573lfhdaza-ew.a.run.app"
KEY = "themison-test-key-2026"

def test_headers():
    variations = ["X-API-KEY", "x-api-key", "X-Api-Key", "api-key"]
    for h in variations:
        print(f"Testing header: {h}")
        try:
            resp = httpx.post(
                f"{BASE_URL}/upload/upload-pdf",
                headers={h: KEY},
                json={"document_url": "https://example.com/test.pdf", "document_id": "00000000-0000-0000-0000-000000000001"}
            )
            print(f"Status: {resp.status_code} | Body: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_headers()
