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
from app.db.models import BotModel, PaperTradeLedgerModel, ApiKeyModel, StrategyModel
from app.core.security import encrypt_api_key, decrypt_api_key
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

    now = datetime.datetime.now()
    data = []
    
    if tf == "1H":
        # Simulate last 60 minutes, ticks every 10 min
        steps = 6
        delta = datetime.timedelta(minutes=10)
        time_fmt = "%H:%M"
    elif tf == "4H":
        # Simulate last 4 hours, ticks every 30 min
        steps = 8
        delta = datetime.timedelta(minutes=30)
        time_fmt = "%H:%M"
    elif tf == "1W":
        # Simulate last 7 days, ticks every day
        steps = 7
        delta = datetime.timedelta(days=1)
        time_fmt = "%b %d"
    else:  # "1D" default
        # Simulate last 24 hours, ticks every 4 hours
        steps = 6
        delta = datetime.timedelta(hours=4)
        time_fmt = "%H:%M"

    for i in range(steps, 0, -1):
        dt = now - (delta * i)
        offset = random.uniform(-0.02, 0.02) * tot_usdt
        val = max(tot_usdt + offset, 0)
        data.append({"name": dt.strftime(time_fmt), "equity": round(val, 2)})
    
    data.append({"name": now.strftime(time_fmt), "equity": round(tot_usdt, 2)})

    return data
