import asyncio
import asyncpg
import os

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    # Use DATABASE_URL from .env (fallback to the tunnel address)
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    
    # asyncpg expects postgresql:// (not postgresql+asyncpg://)
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to {db_url}...")
    try:
        conn = await asyncpg.connect(db_url)
        print("Connected successfully!")
        
        # Check if visit_activities table exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'visit_activities'
            );
        """)
        print(f"Table 'visit_activities' exists: {exists}")
        
        # Check if actual_date column exists in patient_visits
        col_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'patient_visits' AND column_name = 'actual_date'
            );
        """)
        print(f"Column 'actual_date' in 'patient_visits' exists: {col_exists}")
        
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
