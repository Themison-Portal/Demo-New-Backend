import asyncio
import asyncpg
import os

async def main():
    db_url = "postgresql://postgres:postgres@34.77.93.209:5432/postgres"
    print(f"Connecting to {db_url}")
    conn = await asyncpg.connect(db_url)
    
    with open("seed_test_data.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    print("Running sql...")
    await conn.execute(sql)
    print("Done")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
