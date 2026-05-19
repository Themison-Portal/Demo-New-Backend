import httpx
url = "https://core-backend-eu-573lfhdaza-ew.a.run.app/api/trial-documents/upload"
trial_id = "55555555-5555-5555-5555-555555555555"

files = {'file': ('test.pdf', b'dummy content', 'application/pdf')}
data = {
    'trial_id': trial_id,
    'document_name': 'Test Upload after Fix',
    'document_type': 'protocol'
}

response = httpx.post(url, data=data, files=files, timeout=30.0)
print(f"Status: {response.status_code}")
print(response.text)
