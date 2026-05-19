import requests
import json

url = "https://core-backend-eu-768873408671.europe-west1.run.app/query"
headers = {
    "X-API-KEY": "qihNSX-dVMUJVCIiifr7LyRNhjXuF444CAqAOxNaH-IiM",
    "Content-Type": "application/json"
}
data = {
    "query": "What is this document about?",
    "document_id": "19630427-d6fb-487d-9431-026cd3bd5c0a",
    "document_name": "Test Upload after Fix"
}

print(f"Sending query to {url}...")
try:
    response = requests.post(url, headers=headers, json=data, timeout=60)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"An error occurred: {e}")
