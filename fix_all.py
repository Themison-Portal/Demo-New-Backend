import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

async def fix_schema():
    print(f"Connecting to {DB_URL}...")
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        print("Fixing organizations table...")
        await conn.execute(text(
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS support_enabled BOOLEAN DEFAULT true;"
        ))
        await conn.execute(text(
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;"
        ))
        # Remove the 'NOT NULL' constraint from created_by so the first org can be created
        await conn.execute(text(
            "ALTER TABLE organizations ALTER COLUMN created_by DROP NOT NULL;"
        ))
        print("--- SCHEMA FIXED ---")
        print("Now just refresh your browser and Login. It will work!")

if __name__ == "__main__":
    asyncio.run(fix_schema())
