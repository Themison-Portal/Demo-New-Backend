import asyncio
import os
import sys
from uuid import uuid4

# Mock settings
class Settings:
    rag_service_address = "rag-service-eu-768873408671.europe-west1.run.app:443"
    rag_service_timeout = 30.0

def get_settings():
    return Settings()

# Mock the app.config to avoid complex imports
import app
app.config.get_settings = get_settings

from app.clients.rag_client import RagClient

async def test_rag_health():
    print(f"Testing RAG Service health at {Settings.rag_service_address}...")
    client = RagClient()
    try:
        health = await client.health_check()
        print(f"Health Response: {health}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_rag_health())
