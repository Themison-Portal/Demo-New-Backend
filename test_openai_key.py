import httpx
import sys

def test_key(key):
    print(f"Testing key ending in ...{key[-4:]}")
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    data = {
        "input": "test",
        "model": "text-embedding-3-small"
    }
    try:
        resp = httpx.post(url, headers=headers, json=data, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("SUCCESS! Key is valid.")
        else:
            print(f"FAILURE: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    key = sys.argv[1] if len(sys.argv) > 1 else os.getenv("OPENAI_API_KEY")
    
    if not key:
        print("Usage: python test_openai_key.py <key>")
        print("Or set OPENAI_API_KEY in your .env file.")
        sys.exit(1)
        
    test_key(key)
