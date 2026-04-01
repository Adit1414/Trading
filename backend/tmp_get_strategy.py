import asyncio
from app.db.session import SessionLocal
from sqlalchemy import text

async def main():
    async with SessionLocal() as s:
        res = await s.execute(text('SELECT id FROM strategies LIMIT 1'))
        ids = res.scalars().all()
        print('IDs:', ids)
        if not ids:
            print("No strategies found. Inserting a dummy strategy...")
            import uuid
            new_id = str(uuid.uuid4())
            await s.execute(text(f"INSERT INTO strategies (id, user_id, name, description, type, config) VALUES ('{new_id}', NULL, 'Test Strategy', 'Created by script', 'MOMENTUM', '{{}}')"))
            await s.commit()
            print('Inserted ID:', new_id)

asyncio.run(main())
