"""
app/modules/bots/engine.py
────────────────────────────
Bot Execution Engine — async stub functions with Redis pub/sub telemetry.

These stubs simulate the lifecycle of a live trading bot and publish SSE-ready
JSON events to a per-user Redis channel so the frontend receives live updates.

Lifecycle stubs:
  start_bot(bot_id, user_id?)  – Connect to exchange, begin signal loop
  pause_bot(bot_id, user_id?)  – Halt signal loop, preserve open positions
  stop_bot(bot_id, user_id?)   – Close positions, archive state

Redis publishing
────────────────
Each stub publishes a SUCCESS event on completion (or an ERROR event on failure)
to `channel:user_{user_id}:events` (falling back to `channel:global:events`).
The SSE endpoint in bots.py subscribes to this channel and streams events to
the frontend in real-time.

BackgroundTask contract
───────────────────────
Called as FastAPI BackgroundTasks after DB commit — must never raise.
All exceptions are caught, logged, and published as ERROR events.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.modules.bots.events import channel_name, make_event
from app.db.session import get_db
from app.db.models import BotModel, PaperTradeLedgerModel, ApiKeyModel
from app.core.security import decrypt_api_key
from app.services.market_data.binance import get_binance_testnet_client

logger = logging.getLogger(__name__)


# ─── Internal publish helper ──────────────────────────────────────────────────

async def _publish(
    user_id: Optional[str],
    event_type: str,
    message: str,
    bot_id: Optional[str] = None,
) -> None:
    """
    Publish a single SSE event to the user's Redis channel.
    Silently no-ops if Redis is not configured.
    """
    redis = get_redis()
    if redis is None:
        return
    channel = channel_name(user_id)
    payload = json.dumps({"type": event_type, "message": message, **({"bot_id": bot_id} if bot_id else {})})
    try:
        await redis.publish(channel, payload)
        logger.debug("[Engine] Published %s to %s", event_type, channel)
    except Exception as exc:
        # Never let a publish failure propagate — it would crash the BackgroundTask
        logger.warning("[Engine] Redis publish failed (channel=%s): %s", channel, exc)


async def execute_trade(bot_id: str, side: str, user_id: str, quantity: float = 10.0, symbol: str = "BTCUSDT") -> None:
    """
    Called by the bot logic when deciding to place a trade.
    """
    logger.info("[Engine] Executing trade %s for bot_id=%s", side, bot_id)
    try:
        async with get_db() as session:
            result = await session.execute(select(BotModel).where(BotModel.id == bot_id))
            bot = result.scalar_one_or_none()
            if not bot:
                return

            if bot.environment == "TESTNET":
                logger.info("[Engine] TESTNET environment detected, placing paper trade for bot_id=%s", bot_id)
                # Retrieve the user's decrypted Binance Testnet API keys
                key_result = await session.execute(select(ApiKeyModel).where(ApiKeyModel.user_id == user_id))
                api_key_record = key_result.scalar_one_or_none()
                if not api_key_record:
                    raise Exception("No paper trading keys found for user.")
                
                api_key = decrypt_api_key(api_key_record.binance_testnet_api_key)
                secret = decrypt_api_key(api_key_record.binance_testnet_secret)

                exchange = get_binance_testnet_client(api_key, secret)
                
                try:
                    # Use CCXT testnet to execute a live MARKET order
                    order = await exchange.create_market_order(bot.symbol, side.lower(), quantity)
                    exec_price = order.get('average') or order.get('price') or 0.0
                    
                    # Calculate cost (simplified pnl logic here, can be expanded)
                    # Insert a new row into PaperTradeLedgerModel
                    ledger_entry = PaperTradeLedgerModel(
                        bot_id=bot_id,
                        pair=bot.symbol,
                        side=side.upper(),
                        execution_price=exec_price,
                        quantity=quantity,
                        realized_pnl=0.0,
                        is_win=True
                    )
                    session.add(ledger_entry)
                    await session.commit()
                    
                    # Emit SSE telemetry event using make_event structure
                    await _publish(
                        user_id=user_id,
                        event_type="SUCCESS",
                        message=f"Paper trade executed: {side} {quantity} {bot.symbol} @ {exec_price}",
                        bot_id=bot_id
                    )
                except Exception as exchange_exc:
                    await exchange.close()
                    raise exchange_exc
                finally:
                    await exchange.close()
            else:
                # MAINNET logic (Module 5) goes here
                pass

    except Exception as exc:
        logger.exception("[Engine] ERROR executing trade for bot_id=%s", bot_id)
        await _publish(
            user_id=user_id,
            event_type="ERROR",
            message=f"Bot {bot_id} trade failed: {str(exc)}",
            bot_id=bot_id,
        )


# ─── Engine stubs ─────────────────────────────────────────────────────────────

async def start_bot(bot_id: str, user_id: Optional[str] = None) -> None:
    """
    Stub: Start the trading loop for a bot.

    Real implementation will:
      1. Load bot config + strategy parameters from DB
      2. Subscribe to the Binance WebSocket market data stream (Module 3)
      3. Initialise the signal generator with the bot's strategy
      4. Begin the real-time order placement loop (Module 5)
    """
    logger.info("[Engine] START  bot_id=%s — initialising trading loop", bot_id)
    try:
        # Simulate async initialisation work (exchange handshake, data load, etc.)
        await asyncio.sleep(0.1)
        logger.info("[Engine] START  bot_id=%s — trading loop active ✓", bot_id)
        await _publish(
            user_id=user_id,
            event_type="SUCCESS",
            message=f"Bot {bot_id} started — trading loop is active.",
            bot_id=bot_id,
        )
    except Exception:
        logger.exception("[Engine] START  bot_id=%s — unexpected error", bot_id)
        await _publish(
            user_id=user_id,
            event_type="ERROR",
            message=f"Bot {bot_id} failed to start. Check logs.",
            bot_id=bot_id,
        )


async def pause_bot(bot_id: str, user_id: Optional[str] = None) -> None:
    """
    Stub: Pause the trading loop for a bot.

    Real implementation will:
      1. Signal the running coroutine to halt new order placement
      2. Keep existing open positions unchanged (no forced close)
      3. Unsubscribe from the WebSocket stream to reduce load
      4. Persist the paused state snapshot to DB
    """
    logger.info("[Engine] PAUSE  bot_id=%s — suspending signal loop", bot_id)
    try:
        # Simulate async teardown work (flush pending orders, checkpoint state)
        await asyncio.sleep(0.1)
        logger.info("[Engine] PAUSE  bot_id=%s — signal loop suspended ✓", bot_id)
        await _publish(
            user_id=user_id,
            event_type="SUCCESS",
            message=f"Bot {bot_id} paused — open positions preserved.",
            bot_id=bot_id,
        )
    except Exception:
        logger.exception("[Engine] PAUSE  bot_id=%s — unexpected error", bot_id)
        await _publish(
            user_id=user_id,
            event_type="ERROR",
            message=f"Bot {bot_id} failed to pause. Check logs.",
            bot_id=bot_id,
        )


async def stop_bot(bot_id: str, user_id: Optional[str] = None) -> None:
    """
    Stub: Permanently stop a bot and close all open positions.

    Real implementation will:
      1. Force-close all open positions via market orders (Module 5)
      2. Unsubscribe from all WebSocket streams
      3. Mark the bot as STOPPED in DB (already done by the route before dispatch)
      4. Archive the final PnL snapshot and trade log
    """
    logger.info("[Engine] STOP   bot_id=%s — closing positions & archiving", bot_id)
    try:
        # Simulate async cleanup (position close, stream teardown, DB archive)
        await asyncio.sleep(0.1)
        logger.info("[Engine] STOP   bot_id=%s — bot archived ✓", bot_id)
        await _publish(
            user_id=user_id,
            event_type="SUCCESS",
            message=f"Bot {bot_id} stopped — positions closed, state archived.",
            bot_id=bot_id,
        )
    except Exception:
        logger.exception("[Engine] STOP   bot_id=%s — unexpected error", bot_id)
        await _publish(
            user_id=user_id,
            event_type="ERROR",
            message=f"Bot {bot_id} failed to stop cleanly. Check logs.",
            bot_id=bot_id,
        )


async def trigger_circuit_breaker(
    bot_id: str,
    user_id: Optional[str],
    reason: str,
) -> None:
    """
    Publish a CIRCUIT_BREAKER event when the daily PnL limit is hit.
    Called by the engine's risk monitor (Module 4 integration point).
    """
    logger.warning("[Engine] CIRCUIT_BREAKER bot_id=%s reason=%s", bot_id, reason)
    await _publish(
        user_id=user_id,
        event_type="CIRCUIT_BREAKER",
        message=reason,
        bot_id=bot_id,
    )


# ─── Dispatch table ───────────────────────────────────────────────────────────
# Maps the normalised frontend status string → engine handler.

_DISPATCH = {
    "RUNNING": start_bot,
    "PAUSED":  pause_bot,
    "STOPPED": stop_bot,
}


async def dispatch(
    bot_id: str,
    target_status: str,
    user_id: Optional[str] = None,
) -> None:
    """
    Route layer calls this via BackgroundTasks after a successful DB commit.
    Selects the correct engine stub and passes both bot_id and user_id.
    """
    handler = _DISPATCH.get(target_status.upper())
    if handler is None:
        logger.warning(
            "[Engine] dispatch bot_id=%s — unknown target_status=%s, skipping",
            bot_id, target_status,
        )
        return
    await handler(bot_id, user_id)
