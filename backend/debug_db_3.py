import asyncio
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import UserModel, ApiKeyModel, UserSettingsModel, ApiCredentialModel

async def test():
    async with get_db() as session:
        print("--- API KEYS ---")
        keys = (await session.execute(select(ApiKeyModel))).scalars().all()
        for k in keys: print(f"UserID: {k.user_id}, Key: {k.binance_testnet_api_key[:15]}...")
        
        print("--- USER SETTINGS ---")
        settings = (await session.execute(select(UserSettingsModel))).scalars().all()
        for s in settings: print(f"UserID: {s.user_id}, Key: {s.binance_api_key[:15] if s.binance_api_key else 'None'}...")
        
        print("--- API CREDENTIALS ---")
        creds = (await session.execute(select(ApiCredentialModel))).scalars().all()
        for c in creds: print(f"UserID: {c.user_id}")

if __name__ == "__main__":
    asyncio.run(test())
