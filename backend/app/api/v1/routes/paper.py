"""
app/api/v1/routes/paper.py
──────────────────────────
Paper Trading endpoints.
"""
import datetime
import random
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.db.session import get_db
from app.core.security import encrypt_api_key, decrypt_api_key
from app.db.models import BotModel, PaperTradeLedgerModel, ApiKeyModel, StrategyModel, PortfolioHistoryModel
from app.services.market_data.binance import get_binance_testnet_client
import ccxt.async_support as ccxt

router = APIRouter(prefix="/paper", tags=["Paper Trading"])

class KeySubmit(BaseModel):
    api_key: str
    secret: str

class PaperBotResponse(BaseModel):
    id: str
    pair: str
    strategy: str
    pnl: float
    isWin: bool
    uptime: str

class PaperLedgerResponse(BaseModel):
    pair: str
    side: str
    price: float
    time: str
    pnl: float
    isWin: bool

@router.get("/bots", response_model=List[PaperBotResponse])
async def get_paper_bots(user_id: str = Depends(get_current_user)):
    """Fetch all bots where environment='TESTNET'"""
    async with get_db() as session:
        result = await session.execute(
            select(BotModel, StrategyModel)
            .join(StrategyModel, BotModel.strategy_id == StrategyModel.id)
            .options(selectinload(BotModel.state))
            .where(BotModel.user_id == user_id, BotModel.environment == "TESTNET")
        )
        rows = result.all()

        bots = []
        for bot, strategy in rows:
            # uptime based on created_at
            now = datetime.datetime.now(datetime.timezone.utc)
            delta = now - bot.created_at
            days, seconds = delta.days, delta.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if days > 0:
                uptime = f"{days}d {hours}h"
            else:
                uptime = f"{hours}h {minutes}m"

            # pnl logic
            state = getattr(bot, "state", None)
            realized = float(state.daily_realized_pnl) if state else 0.0
            unrealized = float(state.daily_unrealized_pnl) if state else 0.0
            pnl = realized + unrealized

            bots.append(PaperBotResponse(
                id=bot.id,
                pair=bot.symbol,
                strategy=strategy.name,
                pnl=pnl,
                isWin=(pnl >= 0),
                uptime=uptime
            ))
        return bots

@router.get("/ledger", response_model=List[PaperLedgerResponse])
async def get_paper_ledger(user_id: str = Depends(get_current_user)):
    """Query the PaperTradeLedgerModel for the user"""
    async with get_db() as session:
        result = await session.execute(
            select(PaperTradeLedgerModel)
            .join(BotModel, PaperTradeLedgerModel.bot_id == BotModel.id)
            .where(BotModel.user_id == user_id)
            .order_by(PaperTradeLedgerModel.timestamp.desc())
        )
        ledger_entries = result.scalars().all()

        return [
            PaperLedgerResponse(
                pair=entry.pair,
                side=entry.side,
                price=float(entry.execution_price),
                time=entry.timestamp.isoformat(),
                pnl=float(entry.realized_pnl) if entry.realized_pnl is not None else 0.0,
                isWin=bool(entry.is_win) if entry.is_win is not None else False
            )
            for entry in ledger_entries
        ]

@router.post("/keys", status_code=status.HTTP_200_OK)
async def submit_paper_keys(body: KeySubmit, user_id: str = Depends(get_current_user)):
    """Accept and encrypt keys, verify them first"""
    exchange = get_binance_testnet_client(body.api_key, body.secret)
    try:
        await exchange.fetch_balance()
    except Exception as e:
        await exchange.close()
        raise HTTPException(status_code=400, detail=f"Invalid testnet keys: {str(e)}")
    await exchange.close()

    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        existing_key = result.scalar_one_or_none()

        enc_key = encrypt_api_key(body.api_key)
        enc_secret = encrypt_api_key(body.secret)

        if existing_key:
            existing_key.binance_testnet_api_key = enc_key
            existing_key.binance_testnet_secret = enc_secret
        else:
            new_key = ApiKeyModel(
                user_id=user_id,
                binance_testnet_api_key=enc_key,
                binance_testnet_secret=enc_secret
            )
            session.add(new_key)
        await session.commit()
    return {"message": "Keys saved securely"}

@router.delete("/keys", status_code=status.HTTP_200_OK)
async def revoke_paper_keys(user_id: str = Depends(get_current_user)):
    """Delete the user's paper trading API keys"""
    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        existing_key = result.scalar_one_or_none()
        
        if existing_key:
            await session.delete(existing_key)
            await session.commit()
            
    return {"message": "Keys revoked successfully"}

@router.get("/portfolio")
async def get_paper_portfolio(
    tf: str = "1D",
    user_id: str = Depends(get_current_user)
):
    """Query CCXT testnet for fake account balance and return AreaChart format"""
    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="No paper trading keys found")

    dec_key = decrypt_api_key(api_key.binance_testnet_api_key)
    dec_secret = decrypt_api_key(api_key.binance_testnet_secret)

    exchange = get_binance_testnet_client(dec_key, dec_secret)
    try:
        balance = await exchange.fetch_balance()
        # Fallback to 10000.0 if not trading yet or total is missing on testnet
        tot_usdt = balance.get('USDT', {}).get('total', 0.0) 
        if not tot_usdt:
            tot_usdt = 0.0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CCXT Error: {str(e)}")
    finally:
        await exchange.close()

    now = datetime.datetime.now(datetime.timezone.utc)
    data = []
    
    if tf == "1H":
        # Get snapshots from the last 1 hour
        start_time = now - datetime.timedelta(hours=1)
        time_fmt = "%H:%M"
    elif tf == "4H":
        # Get snapshots from the last 4 hours
        start_time = now - datetime.timedelta(hours=4)
        time_fmt = "%H:%M"
    elif tf == "1W":
        # Get snapshots from the last 7 days
        start_time = now - datetime.timedelta(days=7)
        time_fmt = "%b %d"
    else:  # "1D" default
        # Get snapshots from the last 24 hours
        start_time = now - datetime.timedelta(hours=24)
        time_fmt = "%H:%M"

    async with get_db() as session:
        result = await session.execute(
            select(PortfolioHistoryModel)
            .where(PortfolioHistoryModel.user_id == user_id)
            .where(PortfolioHistoryModel.environment == "TESTNET")
            .where(PortfolioHistoryModel.timestamp >= start_time)
            .order_by(PortfolioHistoryModel.timestamp.asc())
        )
        history = result.scalars().all()

    for record in history:
        # Convert timestamp to local or display format
        data.append({
            "name": record.timestamp.strftime(time_fmt),
            "equity": round(float(record.total_balance), 2)
        })

    # Always append the absolute latest real-time live value from CCXT
    # If there wasn't any history, we at least show this single point.
    data.append({"name": now.strftime(time_fmt), "equity": round(tot_usdt, 2)})

    return data
