import asyncio
import uuid
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Hardcoded DB URL from your .env
DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

async def add_admin():
    print(f"Connecting to {DB_URL}...")
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # 1. Create a default Organization
        org_id = uuid.uuid4()
        await conn.execute(text(
            "INSERT INTO organizations (id, name, onboarding_completed, is_active) "
            "VALUES (:id, 'Themison Portal', true, true) "
            "ON CONFLICT DO NOTHING"
        ), {"id": org_id})
        
        # 2. Create your Profile
        profile_id = uuid.uuid4()
        email = "jonaath@themision.com"
        await conn.execute(text(
            "INSERT INTO profiles (id, email, first_name, last_name) "
            "VALUES (:id, :email, 'Jonaathan', 'Admin') "
            "ON CONFLICT (email) DO NOTHING"
        ), {"id": profile_id, "email": email})

        # Fetch existing profile_id if it was already there
        result = await conn.execute(text("SELECT id FROM profiles WHERE email = :email"), {"email": email})
        profile_id = result.scalar()
        
        # 3. Create your Membership
        member_id = uuid.uuid4()
        await conn.execute(text(
            "INSERT INTO members (id, profile_id, organization_id, email, name, default_role, is_active, onboarding_completed) "
            "VALUES (:id, :profile_id, :org_id, :email, 'Jonaathan', 'admin', true, true) "
            "ON CONFLICT DO NOTHING"
        ), {"id": member_id, "profile_id": profile_id, "org_id": org_id, "email": email})
        
        print(f"--- SUCCESS ---")
        print(f"Added {email} to the database.")
        print(f"You can now log in!")

if __name__ == "__main__":
    asyncio.run(add_admin())
