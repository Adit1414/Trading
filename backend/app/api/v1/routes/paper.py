"""
app/api/v1/routes/paper.py
──────────────────────────
Paper Trading endpoints.
"""
import datetime
import logging
import random
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

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
    """
    Return portfolio history snapshots for the chart.
    Attempts a live CCXT testnet balance fetch to append the latest real-time
    data point. If the testnet is unavailable, falls back gracefully to
    DB-only snapshot data so the endpoint never returns 500.
    """
    async with get_db() as session:
        result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
        api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="No paper trading keys found")

    # ── Attempt live balance (non-fatal) ─────────────────────────────────────
    tot_usdt: float | None = None
    dec_key = decrypt_api_key(api_key.binance_testnet_api_key)
    dec_secret = decrypt_api_key(api_key.binance_testnet_secret)
    exchange = get_binance_testnet_client(dec_key, dec_secret)
    try:
        balance = await exchange.fetch_balance()
        live_val = balance.get("USDT", {}).get("total", 0.0)
        tot_usdt = float(live_val) if live_val else 0.0
    except Exception as exc:
        # Testnet can be intermittently down — log and continue with DB data
        logger.warning("[Paper] Live testnet fetch failed (non-fatal): %s", exc)
        tot_usdt = None
    finally:
        try:
            await exchange.close()
        except Exception:
            pass

    # ── Time-window selection ─────────────────────────────────────────────────
    now = datetime.datetime.now(datetime.timezone.utc)
    if tf == "1H":
        start_time = now - datetime.timedelta(hours=1)
        time_fmt = "%H:%M"
    elif tf == "4H":
        start_time = now - datetime.timedelta(hours=4)
        time_fmt = "%H:%M"
    elif tf == "1W":
        start_time = now - datetime.timedelta(days=7)
        time_fmt = "%b %d"
    else:  # "1D" default
        start_time = now - datetime.timedelta(hours=24)
        time_fmt = "%H:%M"

    # ── Fetch history from DB ─────────────────────────────────────────────────
    async with get_db() as session:
        result = await session.execute(
            select(PortfolioHistoryModel)
            .where(PortfolioHistoryModel.user_id == user_id)
            .where(PortfolioHistoryModel.environment == "TESTNET")
            .where(PortfolioHistoryModel.timestamp >= start_time)
            .order_by(PortfolioHistoryModel.timestamp.asc())
        )
        history = result.scalars().all()

    data = [
        {"name": record.timestamp.strftime(time_fmt), "equity": round(float(record.total_balance), 2)}
        for record in history
    ]

    # Append real-time point only when the live fetch succeeded
    if tot_usdt is not None:
        data.append({"name": now.strftime(time_fmt), "equity": round(tot_usdt, 2)})

    # If we have no data at all, return a single zero-equity placeholder so
    # the chart component never receives an empty array.
    if not data:
        data.append({"name": now.strftime(time_fmt), "equity": 0.0})

    return data
