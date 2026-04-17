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
from typing import Optional, Dict, Any

import pandas as pd                     
import numpy as np

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.modules.bots.events import channel_name, make_event
from app.db.session import get_db
from app.db.models import BotModel, PaperTradeLedgerModel, ApiKeyModel
from app.core.security import decrypt_api_key
from app.services.market_data.binance import get_binance_testnet_client

logger = logging.getLogger(__name__)

_ACTIVE_BOT_TASKS: Dict[str, asyncio.Task] = {}
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

# ─── Strategy Math ────────────────────────────────────────────────────────────

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Standard RSI calculation matching your backtest logic."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

# ─── The Evaluator Loop ───────────────────────────────────────────────────────

async def _bot_trading_loop(bot_id: str, user_id: str) -> None:
    """
    The heart of the bot. Runs continuously, evaluates market data against
    strategy parameters, and triggers trades.
    """
    logger.info(f"[Engine] Loop started for bot {bot_id}")
    
    while True:
        try:
            # 1. Fetch the latest bot state and parameters from DB
            async with get_db() as session:
                bot = (await session.execute(
                    select(BotModel).options(selectinload(BotModel.state)).where(BotModel.id == bot_id)
                )).scalar_one_or_none()
                
                # Exit loop if bot was deleted or is no longer RUNNING
                if not bot or bot.status != "RUNNING":
                    logger.info(f"[Engine] Bot {bot_id} is not RUNNING. Exiting loop.")
                    break
                
                params = bot.parameters or {}
                current_position = bot.state.current_position if bot.state else "FLAT"

                # 2. Fetch the last 50 candles (1m timeframe)
                exchange = get_binance_testnet_client("", "") # Anonymous client just for public market data
                try:
                    normalized_symbol = bot.symbol.upper()
                    if "/" not in normalized_symbol and len(normalized_symbol) > 3:
                        if normalized_symbol.endswith("USDT"):
                            normalized_symbol = f"{normalized_symbol[:-4]}/USDT"
                    # fetch_ohlcv returns: [timestamp, open, high, low, close, volume]
                    candles = await exchange.fetch_ohlcv(normalized_symbol, timeframe='1m', limit=50)
                finally:
                    await exchange.close()

                # 3. Process data & calculate indicators
                # Process data & calculate indicators
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                if "RSI" in bot.strategy_id:
                    period = int(params.get("period", 14))
                    oversold = float(params.get("oversold", 30.0))
                    overbought = float(params.get("overbought", 70.0))
                    
                    # Extract the dynamic trade size (default to 0.01 if missing)
                    trade_quantity = float(params.get("trade_size", 0.01))
                    
                    df['rsi'] = calculate_rsi(df['close'], period)
                    
                    if len(df['rsi'].dropna()) >= 2:
                        last_rsi = df['rsi'].iloc[-1]
                        prev_rsi = df['rsi'].iloc[-2]

                        # BUY SIGNAL
                        if current_position == "FLAT" and prev_rsi <= oversold and last_rsi > oversold:
                            logger.info(f"[{bot.symbol}] BUY SIGNAL! RSI crossed up: {prev_rsi:.2f} -> {last_rsi:.2f}")
                            # Pass trade_quantity instead of 0.01
                            await execute_trade(bot_id, "BUY", user_id, quantity=trade_quantity, symbol=bot.symbol)
                            
                            bot.state.current_position = "LONG"
                            await session.commit()

                        # SELL SIGNAL
                        elif current_position == "LONG" and prev_rsi >= overbought and last_rsi < overbought:
                            logger.info(f"[{bot.symbol}] SELL SIGNAL! RSI crossed down: {prev_rsi:.2f} -> {last_rsi:.2f}")
                            # Pass trade_quantity instead of 0.01
                            await execute_trade(bot_id, "SELL", user_id, quantity=trade_quantity, symbol=bot.symbol)
                            
                            bot.state.current_position = "FLAT"
                            await session.commit()
            
        except asyncio.CancelledError:
            # Task was canceled by pause/stop
            logger.info(f"[Engine] Loop for bot {bot_id} was cancelled.")
            break
        except Exception as e:
            logger.error(f"[Engine] Error in bot loop {bot_id}: {e}")
            
        # Wait 20 seconds before checking the market again
        await asyncio.sleep(20)

# ─── Trade Execution ──────────────────────────────────────────────────────────
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
                if not api_key_record or not api_key_record.binance_testnet_api_key:
                    logger.warning("[Engine] No Testnet keys found. Falling back to internal DB paper simulation.")
                    from app.modules.live_trading.engine import live_trading_engine
                    await live_trading_engine.process_bot_signal(
                        user_id=user_id,
                        bot_id=bot_id,
                        symbol=bot.symbol,
                        side=side.upper(),
                        quantity=quantity,
                        execution_mode="PAPER"
                    )
                    return
                
                api_key = decrypt_api_key(api_key_record.binance_testnet_api_key)
                secret = decrypt_api_key(api_key_record.binance_testnet_secret)

                exchange = get_binance_testnet_client(api_key, secret)
                
                try:
                    normalized_symbol = bot.symbol.upper()
                    if "/" not in normalized_symbol and len(normalized_symbol) > 3:
                        if normalized_symbol.endswith("USDT"):
                            normalized_symbol = f"{normalized_symbol[:-4]}/USDT"

                    # 2. Load markets and format precision
                    await exchange.load_markets()
                    precise_amount = float(exchange.amount_to_precision(normalized_symbol, quantity))
                    # Use CCXT testnet to execute a live MARKET order
                    order = await exchange.create_market_order(normalized_symbol, side.lower(), precise_amount)
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
                from app.modules.live_trading.engine import live_trading_engine
                
                await live_trading_engine.process_bot_signal(
                    user_id=user_id,
                    bot_id=bot_id,
                    symbol=bot.symbol,
                    side=side.upper(),
                    quantity=quantity,
                    execution_mode="LIVE"
                )
                
                await _publish(
                    user_id=user_id,
                    event_type="SUCCESS",
                    message=f"Live signal processed: {side} {quantity} {bot.symbol}",
                    bot_id=bot_id
                )

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
        # Check if already running
        if bot_id in _ACTIVE_BOT_TASKS and not _ACTIVE_BOT_TASKS[bot_id].done():
            logger.warning(f"Bot {bot_id} is already running in memory.")
            return

        # Spawn the background task and save it to the registry
        task = asyncio.create_task(_bot_trading_loop(bot_id, user_id))
        _ACTIVE_BOT_TASKS[bot_id] = task
        
        await _publish(user_id, "SUCCESS", f"Bot {bot_id} started — trading loop is active.", bot_id)
    except Exception as e:
        logger.exception(f"Failed to start bot {bot_id}")
        await _publish(user_id, "ERROR", f"Bot {bot_id} failed to start: {e}", bot_id)


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
        # Find the task and cancel it
        task = _ACTIVE_BOT_TASKS.get(bot_id)
        if task and not task.done():
            task.cancel()
            del _ACTIVE_BOT_TASKS[bot_id]
            
        await _publish(user_id, "SUCCESS", f"Bot {bot_id} paused.", bot_id)
    except Exception as e:
        await _publish(user_id, "ERROR", f"Failed to pause bot: {e}", bot_id)


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
        # Find the task and cancel it
        task = _ACTIVE_BOT_TASKS.get(bot_id)
        if task and not task.done():
            task.cancel()
            del _ACTIVE_BOT_TASKS[bot_id]
            
        # TODO: Add logic here to execute market close orders if desired.
            
        await _publish(user_id, "SUCCESS", f"Bot {bot_id} stopped permanently.", bot_id)
    except Exception as e:
        await _publish(user_id, "ERROR", f"Failed to stop bot: {e}", bot_id)


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
    await pause_bot(bot_id=bot_id, user_id=user_id)


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
