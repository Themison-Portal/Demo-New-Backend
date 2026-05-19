import asyncio
import os
from dotenv import load_dotenv
import httpx
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sendgrid():
    # Load env from the root of core-backend.V4
    load_dotenv(".env")
    
    api_key = os.getenv("SENDGRID_API_KEY")
    email_from = os.getenv("EMAIL_FROM", "noreply@themison.com")
    
    if not api_key:
        print("ERROR: SENDGRID_API_KEY not found in .env")
        return

    print(f"Testing SendGrid with API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Target email for testing
    test_email = "test-recipient@themison.app" # Replace with a real one if needed manually
    name = "Test User"
    token = "test-token-2026"
    org_name = "Themison Test Org"
    signup_link = f"https://example.com/signup?token={token}"

    payload = {
        "personalizations": [{"to": [{"email": test_email}]}],
        "from": {
            "email": email_from,
            "name": "Themison Portal Test"
        },
        "subject": f"TEST: Invitation to join {org_name}",
        "content": [
            {"type": "text/plain", "value": f"Hello {name}, test invite link: {signup_link}"}
        ]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            print("Sending request to SendGrid...")
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers
            )
            
            if resp.status_code >= 400:
                print(f"SendGrid Error {resp.status_code}: {resp.text}")
            else:
                print(f"SUCCESS! Status Code: {resp.status_code}")
                print(f"Successfully sent invitation email to {test_email}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sendgrid())
