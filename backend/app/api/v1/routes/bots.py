"""
app/api/v1/routes/bots.py
──────────────────────────
Bot management endpoints.

  GET  /api/v1/bots             List all bots (+ live PnL from bot_state)
  POST /api/v1/bots             Create a bot (also initialises bot_state row)
  PUT  /api/v1/bots/{id}/state  Change bot status (RUNNING | PAUSED | STOPPED)
  GET  /api/v1/bots/events      SSE heartbeat stream (kept for frontend compat)

Frontend contract
─────────────────
BotResponse shape:
  id, symbol, is_testnet, strategy_id, parameters,
  take_profit, stop_loss, status, pnl, created_at

Mapping notes
─────────────
  BotModel.environment         → is_testnet  (TESTNET → True, MAINNET → False)
  BotModel.daily_pnl_upper_limit → take_profit
  BotModel.daily_pnl_lower_limit → stop_loss
  BotModel.status              → exposed as-is but "PAUSED_LIMIT_REACHED" is
                                  normalised to "PAUSED" for the frontend
  BotStateModel.daily_realized_pnl
    + BotStateModel.daily_unrealized_pnl → pnl
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import UUID4, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.auth import decode_token, get_current_user
from app.core.idempotency import IdempotencyContext, idempotency_dep
from app.core.redis import get_redis
from app.db.models import BotModel, BotStateModel
from app.db.session import get_db
from app.modules.bots.engine import dispatch as engine_dispatch
from app.modules.bots.events import HEARTBEAT, channel_name, make_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bots", tags=["Bots"])


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class BotCreate(BaseModel):
    """POST /bots request body — matches the frontend modal fields."""
    symbol:      str            = Field(..., min_length=1, max_length=20,
                                        description="Trading pair, e.g. BTCUSDT")
    is_testnet:  bool           = Field(..., description="True → TESTNET, False → MAINNET")
    strategy_id: UUID4          = Field(..., description="UUID of the STRATEGIES row")
    parameters:  Dict[str, Any] = Field(default_factory=dict,
                                        description="Strategy-specific parameter values")
    take_profit: Optional[float] = Field(default=None, ge=0,
                                          description="Daily PnL upper-limit circuit breaker (USDT)")
    stop_loss:   Optional[float] = Field(default=None, le=0,
                                          description="Daily PnL lower-limit circuit breaker (USDT)")
    name:        str             = Field(default="My Bot", min_length=1, max_length=120)


class BotStateUpdate(BaseModel):
    """PUT /bots/{id}/state request body."""
    state: str = Field(..., description="One of: RUNNING, PAUSED, STOPPED")


class BotResponse(BaseModel):
    """
    Exact frontend contract shape.

    All derived/mapped fields are computed in `_to_response()`.
    """
    id:          str
    symbol:      str
    is_testnet:  bool
    strategy_id: str
    parameters:  Dict[str, Any]
    take_profit: Optional[float]
    stop_loss:   Optional[float]
    status:      str            # RUNNING | PAUSED | STOPPED
    pnl:         float
    created_at:  datetime

    model_config = {"from_attributes": True}


# ─── Helpers ─────────────────────────────────────────────────────────────────

# Status values that map to "PAUSED" in the frontend
_PAUSED_STATES = {"PAUSED_LIMIT_REACHED", "PAUSED"}

def _to_response(bot: BotModel) -> BotResponse:
    """
    Flatten BotModel + BotStateModel into the frontend BotResponse shape.
    Safe if `bot.state` is None (e.g. just after creation before flush).
    """
    state: Optional[BotStateModel] = getattr(bot, "state", None)
    realized   = float(state.daily_realized_pnl)   if state else 0.0
    unrealized = float(state.daily_unrealized_pnl) if state else 0.0
    pnl = realized + unrealized

    raw_status = bot.status or "STOPPED"
    # Normalise both PAUSED and PAUSED_LIMIT_REACHED → "PAUSED" for the frontend
    frontend_status = "PAUSED" if raw_status in _PAUSED_STATES else raw_status

    return BotResponse(
        id=bot.id,
        symbol=bot.symbol,
        is_testnet=(bot.environment == "TESTNET"),
        strategy_id=bot.strategy_id,
        parameters=bot.parameters or {},
        take_profit=float(bot.daily_pnl_upper_limit) if bot.daily_pnl_upper_limit is not None else None,
        stop_loss=float(bot.daily_pnl_lower_limit)   if bot.daily_pnl_lower_limit  is not None else None,
        status=frontend_status,
        pnl=pnl,
        created_at=bot.created_at,
    )


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[BotResponse],
    summary="List all bots",
)
async def get_bots(
    user_id: str = Depends(get_current_user),
) -> List[BotResponse]:
    """Return all bots belonging to the authenticated user with live PnL."""
    async with get_db() as session:
        if session is None:
            return []
        result = await session.execute(
            select(BotModel)
            .options(selectinload(BotModel.state))
            .where(BotModel.user_id == user_id)
            .order_by(BotModel.created_at.desc())
        )
        bots = result.scalars().all()
    return [_to_response(b) for b in bots]


@router.post(
    "",
    response_model=BotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bot",
)
async def create_bot(
    body: BotCreate,
    background_tasks: BackgroundTasks,
    ctx: IdempotencyContext = Depends(idempotency_dep),
    user_id: str = Depends(get_current_user),
) -> BotResponse:
    """
    Create a bot row and its companion bot_state row in one transaction.
    Status defaults to RUNNING. The engine's start_bot stub is dispatched
    as a background task after the DB commit so it never blocks the response.
    Idempotent: send the same Idempotency-Key header to prevent duplicates on retry.
    """
    async with get_db() as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured.",
            )

        bot_id = str(uuid.uuid4())
        environment = "TESTNET" if body.is_testnet else "MAINNET"

        bot = BotModel(
            id=bot_id,
            symbol=body.symbol.upper(),
            user_id=user_id,
            strategy_id=str(body.strategy_id),
            name=body.name,
            environment=environment,
            status="RUNNING",
            parameters=body.parameters,
            daily_pnl_upper_limit=body.take_profit,
            daily_pnl_lower_limit=body.stop_loss,
            trade_quantity=None,
        )
        session.add(bot)
        try:
            await session.flush()   # populate bot.id before creating state
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy_id '{body.strategy_id}': Strategy not found.",
            )

        state = BotStateModel(
            bot_id=bot_id,
            current_position="FLAT",
            active_quantity=0,
            average_entry_price=0,
            daily_realized_pnl=0,
            daily_unrealized_pnl=0,
        )
        session.add(state)
        await session.flush()
        await session.refresh(bot)
        await session.refresh(state)

        bot.state = state
        response = _to_response(bot)

    # DB transaction committed — dispatch engine in background
    background_tasks.add_task(engine_dispatch, bot_id, "RUNNING", user_id)

    # Store in Redis after the DB commit
    await ctx.store(response.model_dump(mode="json"), status_code=201)
    return response


@router.put(
    "/{bot_id}/state",
    response_model=BotResponse,
    summary="Change bot status",
)
async def update_bot_state(
    bot_id: str,
    body: BotStateUpdate,
    background_tasks: BackgroundTasks,
    ctx: IdempotencyContext = Depends(idempotency_dep),
    user_id: str = Depends(get_current_user),
) -> BotResponse:
    """
    Transition a bot between states.

    Allowed transitions:
      RUNNING          → PAUSED | STOPPED
      PAUSED           → RUNNING | STOPPED
      PAUSED_LIMIT_REACHED → RUNNING | STOPPED
      STOPPED          → ℕ (terminal — permanently archived, 400 on any attempt)

    Idempotent: send the same Idempotency-Key header to prevent duplicate transitions on retry.
    """
    target = body.state.upper()
    if target not in ("RUNNING", "PAUSED", "STOPPED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid state '{target}'. "
                "Accepted values: RUNNING, PAUSED, STOPPED."
            ),
        )

    async with get_db() as session:
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured.",
            )

        result = await session.execute(
            select(BotModel)
            .options(selectinload(BotModel.state))
            .where(BotModel.id == bot_id)
        )
        bot: Optional[BotModel] = result.scalar_one_or_none()

        if bot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot '{bot_id}' not found.",
            )

        # ── Strict terminal-state guard ─────────────────────────────────────────
        # STOPPED is permanent (archived). Frontend contract: 400 Bad Request.
        if bot.status == "STOPPED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Bot is permanently STOPPED and cannot be reactivated. "
                    "Create a new bot to resume trading."
                ),
            )

        # ── No-op guard ───────────────────────────────────────────────────────────
        # Treat PAUSED and PAUSED_LIMIT_REACHED both as logically "PAUSED".
        # If the target matches the current logical state, return immediately
        # without a DB write or engine dispatch.
        current_logical = "PAUSED" if bot.status in _PAUSED_STATES else bot.status
        if current_logical == target:
            # Nothing to do — return the current state without touching the DB
            return _to_response(bot)

        # ── Persist the transition ──────────────────────────────────────────────
        bot.status = target
        await session.flush()
        await session.refresh(bot)
        response = _to_response(bot)

    # DB transaction committed — dispatch the engine stub in the background
    background_tasks.add_task(engine_dispatch, bot_id, target, user_id)

    await ctx.store(response.model_dump(mode="json"), status_code=200)
    return response


# ─── SSE Telemetry Stream ────────────────────────────────────────────────────

HEARTBEAT_INTERVAL = 15  # seconds

import time

@router.get("/events", summary="Live bot telemetry stream (SSE)")
async def bot_events(
    token: str = Query(..., description="Supabase access_token passed as a query param (SSE cannot use headers)"),
):
    """
    Server-Sent Events endpoint — streams live bot telemetry to the frontend.

    Auth: because EventSource cannot send custom headers, the caller must
    append ?token=<access_token> to the URL.  The token is validated with
    the same JWT logic used by every other endpoint.

    Event types (all JSON-parseable via JSON.parse(event.data)):
      HEARTBEAT       — sent every 15 s to keep the connection alive
      SUCCESS         — bot lifecycle action completed
      CIRCUIT_BREAKER — daily PnL limit reached, bot auto-paused
      ERROR           — unrecoverable engine error

    Wire format:  data: {"type": "...", "message": "...", "bot_id": "..."}\n\n
    """
    try:
        user_id: str = decode_token(token)
    except Exception:
        # Return 401 as an SSE error event so the client can handle it gracefully
        async def _unauthorized():
            yield 'data: {"type": "ERROR", "message": "Unauthorized"}\n\n'
        return StreamingResponse(
            _unauthorized(),
            media_type="text/event-stream",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    channel = channel_name(user_id)
    redis = get_redis()

    async def event_generator():
        # ── Redis available: subscribe and stream real events ─────────────────
        if redis is not None:
            pubsub = redis.pubsub()
            try:
                await pubsub.subscribe(channel)
                logger.info("[SSE] Client subscribed to %s", channel)

                last_heartbeat = time.time()

                while True:
                    # Client disconnect is signalled by CancelledError from Starlette
                    # Check for new messages from the engine
                    message = await pubsub.get_message(ignore_subscribe_messages=True)

                    if message is not None:
                        # Forward the raw Redis payload as an SSE frame
                        raw = message.get("data", "")
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        if raw:
                            yield f"data: {raw}\n\n"
                    else:
                        # No message — wait briefly before polling again
                        await asyncio.sleep(0.5)

                    # Send heartbeat if the interval has elapsed
                    if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                        yield HEARTBEAT
                        last_heartbeat = time.time()

            except asyncio.CancelledError:
                pass
            finally:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.aclose()
                except Exception:
                    pass
                logger.info("[SSE] Cleaned up subscription for %s", channel)

        # ── Redis unavailable: heartbeat-only fallback ─────────────────────────
        else:
            logger.warning("[SSE] Redis not configured — serving heartbeat-only stream")
            while True:
                yield HEARTBEAT
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )