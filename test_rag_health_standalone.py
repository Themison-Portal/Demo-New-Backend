import asyncio
import grpc
from grpc import aio

# Import generated protobuf code
import sys
import os

# Add generated directory to path
sys.path.append(os.path.join(os.getcwd(), "app", "clients", "generated"))

try:
    from rag.v1.rag_service_pb2 import HealthCheckRequest
    from rag.v1.rag_service_pb2_grpc import RagServiceStub
except ImportError:
    # Try alternate path
    sys.path.append(os.getcwd())
    from app.clients.generated.rag.v1.rag_service_pb2 import HealthCheckRequest
    from app.clients.generated.rag.v1.rag_service_pb2_grpc import RagServiceStub

async def test_rag_health():
    address = "rag-service-eu-768873408671.europe-west1.run.app:443"
    print(f"Testing RAG Service health at {address}...")
    
    channel = aio.secure_channel(address, grpc.ssl_channel_credentials())
    stub = RagServiceStub(channel)
    
    try:
        response = await stub.HealthCheck(HealthCheckRequest(), timeout=10)
        print(f"Status: {response.status}")
        print(f"Version: {response.version}")
        for c in response.components:
            print(f" - {c.name}: {'Healthy' if c.healthy else 'Unhealthy'} ({c.message})")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await channel.close()

if __name__ == "__main__":
    asyncio.run(test_rag_health())
