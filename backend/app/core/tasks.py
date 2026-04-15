import asyncio
import logging
from datetime import datetime
from sqlalchemy.future import select

from app.core.redis import get_redis
from app.db.session import get_db
from app.db.models import ApiKeyModel, PortfolioHistoryModel
from app.services.market_data.binance import get_binance_testnet_client
from app.core.security import decrypt_api_key

logger = logging.getLogger(__name__)

async def run_portfolio_snapshot() -> None:
    """
    Executes the background snapshot logic.
    For MVP, connects to DB, finds all users with testnet keys, securely
    invokes CCXT to fetch exactly the total balance, and pushes to
    PortfolioHistoryModel.
    """
    logger.info("Executing periodic testnet portfolio snapshot.")
    
    # We use sync session block here if needed, but since we are in async, 
    # we should get an async session directly wrapper.
    # Wait, get_db is an async generator inside deps, but we can do it manually.
    
    async with get_db() as session:
        if session is None:
            return
        
        # 1. Fetch all unique APIKeys
        result = await session.execute(select(ApiKeyModel))
        api_keys = result.scalars().all()
        
        if not api_keys:
            logger.debug("No testnet keys found; skipping portfolio snapshot.")
            return

        snapshot_timestamp = datetime.utcnow()
        new_records = []
        
        for key in api_keys:
            # 2. Invoke async CCXT
            try:
                dec_key = decrypt_api_key(key.binance_testnet_api_key)
                dec_secret = decrypt_api_key(key.binance_testnet_secret)
                
                exchange = get_binance_testnet_client(dec_key, dec_secret)
                balance = await exchange.fetch_balance()
                await exchange.close()
                
                # Fetch total USDT balance safely
                total_balance = balance.get("USDT", {}).get("total", 0.0)
                if not total_balance:
                    total_balance = 0.0
                
                logger.debug(f"Fetched {total_balance} for User {key.user_id}")
                
                new_records.append(
                    PortfolioHistoryModel(
                        user_id=key.user_id,
                        environment="TESTNET",
                        total_balance=total_balance,
                        timestamp=snapshot_timestamp,
                    )
                )
            except Exception as e:
                logger.error(f"Failed pulling balance for User {key.user_id}: {e}")
        
        # 3. Batch insert
        if new_records:
            session.add_all(new_records)
            await session.commit()
            logger.info(f"Inserted {len(new_records)} portfolio snapshots.")

async def portfolio_snapshot_task() -> None:
    """
    Long-running background task that attempts to record portfolio values
    every 15 minutes. Uses Redis distributed lock `SETNX` so multiple uviorn
    workers don't duplicate the table rows.
    """
    redis_client = get_redis()
    interval_seconds = 15 * 60  # 15 minutes

    while True:
        try:
            if redis_client:
                # Attempt to get a 14-minute lock.
                # If True, we execute. If False, another worker handles it.
                lock_acquired = await redis_client.set(
                    "paper_snapshot_lock", 
                    "LOCKED", 
                    nx=True, 
                    ex=14 * 60
                )
            else:
                # If Redis is unset, just execute it locally.
                # In production with multiple workers, Redis is strictly required.
                lock_acquired = True

            if lock_acquired:
                await run_portfolio_snapshot()
        except Exception as e:
            logger.error(f"Error in portfolio snapshot background task: {e}")
        
        await asyncio.sleep(interval_seconds)
