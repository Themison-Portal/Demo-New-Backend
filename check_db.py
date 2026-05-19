import asyncio
import asyncpg
import os

async def main():
    db_url = "postgresql://postgres:postgres@34.77.93.209:5432/postgres"
    print(f"Connecting to {db_url}")
    conn = await asyncpg.connect(db_url)
    
    print("Running sql...")
    records = await conn.fetch("SELECT id, name FROM trials;")
    for row in records:
        print(f"Trial ID: {row['id']}, Name: {row['name']}")
    
    print("\nAdmins:")
    admins = await conn.fetch("SELECT id, email FROM themison_admins;")
    for row in admins:
        print(f"Admin ID: {row['id']}, Email: {row['email']}")

    print("\nDocuments:")
    docs = await conn.fetch("SELECT id, document_name FROM trial_documents;")
    for row in docs:
        print(f"Doc ID: {row['id']}, Name: {row['document_name']}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
