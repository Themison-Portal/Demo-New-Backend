import asyncio
import grpc
from app.clients.generated.rag.v1.rag_service_pb2 import HealthCheckRequest
from app.clients.generated.rag.v1.rag_service_pb2_grpc import RagServiceStub

async def run():
    address = "rag-service-eu-573lfhdaza-ew.a.run.app:443"
    print(f"Connecting to {address}...")
    channel = grpc.aio.secure_channel(address, grpc.ssl_channel_credentials())
    stub = RagServiceStub(channel)
    try:
        response = await stub.HealthCheck(HealthCheckRequest())
        print(f"Status: {response.status}")
        print(f"Version: {response.version}")
        for comp in response.components:
            print(f" - {comp.name}: {comp.healthy} ({comp.message})")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await channel.close()

if __name__ == "__main__":
    asyncio.run(run())
