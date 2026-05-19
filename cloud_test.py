import httpx
import json

def test_cloud_backend():
    url = "https://core-backend-eu-573lfhdaza-ew.a.run.app/"
    print(f"Testing root endpoint: {url}")
    try:
        response = httpx.get(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # Test a dummy query to see if it fails on Auth or gRPC
    query_url = "https://core-backend-eu-573lfhdaza-ew.a.run.app/query"
    print(f"\nTesting query endpoint (expecting 401/404/500): {query_url}")
    headers = {"X-API-KEY": "dummy-key"}
    data = {
        "query": "Is the RAG service connected?",
        "document_id": "00000000-0000-0000-0000-000000000000",
        "document_name": "test.pdf"
    }
    try:
        response = httpx.post(query_url, headers=headers, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_cloud_backend()
