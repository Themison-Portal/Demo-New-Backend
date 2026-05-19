
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check_db_details():
    try:
        async with engine.connect() as conn:
            # Check Version
            version = await conn.execute(text("SELECT version()"))
            print(f"DB Version: {version.scalar()}")

            # Check columns in invitations
            col_check = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'invitations' AND column_name = 'token'
            """))
            print(f"Invitations 'token' column exists: {col_check.scalar() is not None}")

            # Check columns in trials
            col_check = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trials' AND column_name = 'visit_schedule_template'
            """))
            print(f"Trials 'visit_schedule_template' column exists: {col_check.scalar() is not None}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_db_details())
