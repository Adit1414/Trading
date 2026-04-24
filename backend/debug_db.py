import asyncio
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import ApiKeyModel

async def test():
    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel))
        keys = result.scalars().all()
        print(f"Total keys: {len(keys)}")
        for k in keys:
            print(f"User ID: {k.user_id}")

if __name__ == "__main__":
    asyncio.run(test())
