
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def enable_vector_extension():
    # Production DB URL from the logs
    db_url = "postgresql+asyncpg://postgres:postgres@10.132.0.2:5432/postgres"
    
    print(f"Connecting to {db_url}...")
    engine = create_async_engine(db_url)
    
    try:
        async with engine.connect() as conn:
            print("Enabling vector extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.commit()
            print("Successfully enabled pgvector extension.")
            
            # Verify
            result = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
            ext = result.scalar()
            print(f"Extension check: {ext}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(enable_vector_extension())
