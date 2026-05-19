import asyncio
import os
from sqlalchemy import text
from app.db.session import engine
from dotenv import load_dotenv

load_dotenv()

async def cleanup_trials():
    """
    Delete seeded trials and related data.
    """
    async with engine.connect() as conn:
        print("Cleaning up seeded trials...")
        
        # Trial IDs from seed_test_data.sql and docker/seed.sql
        seeded_trial_ids = [
            '55555555-5555-5555-5555-555555555555',
            '55555555-5555-5555-5555-555555555556',
            '55555555-5555-5555-5555-555555555557',
            '50000000-0000-0000-0000-000000000001'
        ]
        
        # Delete using ids
        for trial_id in seeded_trial_ids:
            # Cascade delete should handle documents, etc., but let's be safe
            await conn.execute(text(f"DELETE FROM trial_documents WHERE trial_id = '{trial_id}'"))
            await conn.execute(text(f"DELETE FROM trial_members WHERE trial_id = '{trial_id}'"))
            await conn.execute(text(f"DELETE FROM trial_patients WHERE trial_id = '{trial_id}'"))
            await conn.execute(text(f"DELETE FROM patient_visits WHERE trial_id = '{trial_id}'"))
            await conn.execute(text(f"DELETE FROM chat_sessions WHERE trial_id = '{trial_id}'"))
            await conn.execute(text(f"DELETE FROM trials WHERE id = '{trial_id}'"))
            print(f"  - Deleted trial: {trial_id}")
            
        await conn.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_trials())
