import os
from dotenv import load_dotenv
from app.config import get_settings

def test_config():
    # Load from the test env
    load_dotenv(".env.test", override=True)
    
    settings = get_settings()
    print(f"Config Key: '{settings.upload_api_key}'")
    
    # Simulate the check in the route
    test_key = "themison-test-key-2026"
    if settings.upload_api_key == test_key:
        print("MATCH: Success!")
    else:
        print("NO MATCH: Fail!")
        print(f"Expected: '{test_key}'")
        print(f"Actual:   '{settings.upload_api_key}'")

if __name__ == "__main__":
    test_config()
