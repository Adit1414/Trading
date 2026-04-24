import asyncio
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import UserModel, ApiKeyModel

async def test():
    async with get_db() as session:
        result1 = await session.execute(select(UserModel))
        users = result1.scalars().all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f"User: {u.id} - {u.email}")
        
        result2 = await session.execute(select(ApiKeyModel))
        keys = result2.scalars().all()
        print(f"Total api keys: {len(keys)}")
        for k in keys:
            print(f"ApiKey UserID: {k.user_id}")

if __name__ == "__main__":
    asyncio.run(test())
