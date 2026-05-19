
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check_db():
    try:
        async with engine.connect() as conn:
            # Check Invitations
            res = await conn.execute(text("SELECT count(*), status FROM invitations GROUP BY status"))
            invitations = res.all()
            print(f"Invitations: {invitations}")

            # Check for any specific invitation tokens
            res = await conn.execute(text("SELECT token, email, status FROM invitations LIMIT 5"))
            tokens = res.all()
            print(f"Sample tokens: {tokens}")

            # Check Organizations
            res = await conn.execute(text("SELECT count(*) FROM organizations"))
            orgs = res.scalar()
            print(f"Organizations count: {orgs}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
