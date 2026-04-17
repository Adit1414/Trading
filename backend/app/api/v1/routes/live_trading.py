from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select

from app.core.auth import decode_token, get_current_user
from app.core.security import decrypt_api_key, encrypt_api_key
from app.db.models import BotModel, OrderModel, PositionModel, TradeLogModel, UserSettingsModel
from app.db.session import get_db
from app.modules.live_trading.engine import live_trading_engine
from app.services.live.exchange import get_binance_client
from app.services.live.ws_manager import live_ws_manager

router = APIRouter(tags=["Live Trading"])


class CredentialsIn(BaseModel):
    binance_api_key: str = Field(..., min_length=10)
    binance_secret: str = Field(..., min_length=10)


class BotSignalIn(BaseModel):
    bot_id: str
    symbol: str
    side: str
    quantity: float
    execution_mode: str


@router.post("/user/settings/binance", status_code=status.HTTP_200_OK)
async def set_live_credentials(body: CredentialsIn, user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        settings = (await session.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))).scalar_one_or_none()
        if settings is None:
            settings = UserSettingsModel(user_id=user_id)
            session.add(settings)
        settings.binance_api_key = encrypt_api_key(body.binance_api_key)
        settings.binance_secret = encrypt_api_key(body.binance_secret)
    return {"message": "Live Binance credentials saved securely."}


@router.get("/wallet/balances")
async def get_wallet_balances(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        settings = (await session.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))).scalar_one_or_none()
        if settings is None or not settings.binance_api_key or not settings.binance_secret:
            raise HTTPException(status_code=400, detail="Live Binance credentials are not configured.")
        exchange = get_binance_client(decrypt_api_key(settings.binance_api_key), decrypt_api_key(settings.binance_secret), sandbox=False)
        try:
            live_balance = await exchange.fetch_balance()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch Binance balances: {exc}") from exc
        finally:
            await exchange.close()

        paper = (
            await session.execute(
                select(PositionModel).where(and_(PositionModel.user_id == user_id, PositionModel.is_open.is_(True)))
            )
        ).scalars().all()
        paper_equity = sum(float(p.size) * float(p.entry_price) for p in paper)
        return {"live": live_balance.get("total", {}), "paper": {"total_equity": paper_equity}}


@router.get("/positions")
async def get_positions(user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        positions = (
            await session.execute(
                select(PositionModel).where(and_(PositionModel.user_id == user_id, PositionModel.is_open.is_(True)))
            )
        ).scalars().all()
        return [
            {
                "id": p.id,
                "pair": p.pair,
                "side": p.side,
                "size": float(p.size),
                "entry_price": float(p.entry_price),
                "unrealized_pnl": float(p.unrealized_pnl),
                "bot_id": p.bot_id,
            }
            for p in positions
        ]


@router.get("/orders")
async def get_orders(
    status: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        query = select(OrderModel).where(OrderModel.user_id == user_id)
        if status:
            query = query.where(OrderModel.status == status.upper())
        orders = (await session.execute(query.order_by(desc(OrderModel.created_at)))).scalars().all()
        return [
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": o.side,
                "quantity": float(o.quantity),
                "execution_mode": o.execution_mode,
                "status": o.status,
                "expires_at": o.expires_at,
                "exchange_order_id": o.exchange_order_id,
                "executed_price": float(o.executed_price) if o.executed_price is not None else None,
                "created_at": o.created_at,
            }
            for o in orders
        ]


@router.get("/trades/history")
async def get_trade_history(page: int = 1, page_size: int = 50, user_id: str = Depends(get_current_user)):
    offset = max(0, (page - 1) * page_size)
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        result = await session.execute(
            select(TradeLogModel)
            .where(TradeLogModel.user_id == user_id)
            .order_by(desc(TradeLogModel.executed_at))
            .offset(offset)
            .limit(page_size)
        )
        logs = result.scalars().all()
        return [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": float(t.quantity),
                "execution_price": float(t.execution_price),
                "environment": t.environment,
                "executed_at": t.executed_at,
            }
            for t in logs
        ]


@router.post("/positions/{position_id}/close")
async def panic_close_position(position_id: str, user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        position = (
            await session.execute(
                select(PositionModel)
                .where(and_(PositionModel.id == position_id, PositionModel.user_id == user_id))
                .with_for_update()
            )
        ).scalar_one_or_none()
        if position is None or not position.is_open:
            raise HTTPException(status_code=404, detail="Open position not found.")

        is_live = False
        if position.bot_id:
            bot = (await session.execute(select(BotModel).where(BotModel.id == position.bot_id))).scalar_one_or_none()
            is_live = bool(bot and bot.environment == "MAINNET")

        if is_live:
            settings = (await session.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))).scalar_one_or_none()
            if settings is None or not settings.binance_api_key or not settings.binance_secret:
                raise HTTPException(status_code=400, detail="Live Binance credentials are not configured.")

            exchange = get_binance_client(
                decrypt_api_key(settings.binance_api_key),
                decrypt_api_key(settings.binance_secret),
                sandbox=False,
            )
            try:
                close_side = "sell" if position.side.upper() == "BUY" else "buy"
                await exchange.create_market_order(position.pair, close_side, float(position.size))
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Failed to close LIVE position on Binance: {exc}") from exc
            finally:
                await exchange.close()

        position.is_open = False
        await live_ws_manager.publish_private(user_id, "PANIC_POSITION_CLOSED", {"position_id": position_id})
        return {"message": "Position closed."}


@router.delete("/orders/{order_id}")
async def panic_cancel_order(order_id: str, user_id: str = Depends(get_current_user)):
    async with get_db() as session:
        if session is None:
            raise HTTPException(status_code=503, detail="Database is not configured.")
        order = (
            await session.execute(
                select(OrderModel)
                .where(and_(OrderModel.id == order_id, OrderModel.user_id == user_id))
                .with_for_update()
            )
        ).scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found.")
        if order.status not in {"OPEN", "PENDING_APPROVAL"}:
            raise HTTPException(status_code=400, detail="Order is not cancellable.")

        if order.execution_mode == "LIVE" and order.exchange_order_id:
            settings = (await session.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))).scalar_one_or_none()
            if settings is None or not settings.binance_api_key or not settings.binance_secret:
                raise HTTPException(status_code=400, detail="Live Binance credentials are not configured.")

            exchange = get_binance_client(
                decrypt_api_key(settings.binance_api_key),
                decrypt_api_key(settings.binance_secret),
                sandbox=False,
            )
            try:
                await exchange.cancel_order(order.exchange_order_id, order.symbol)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Failed to cancel LIVE order on Binance: {exc}") from exc
            finally:
                await exchange.close()

        order.status = "CANCELLED"
        await live_ws_manager.publish_private(user_id, "ORDER_CANCELLED", {"order_id": order_id})
        return {"message": "Order cancelled."}


@router.post("/orders/{order_id}/approve")
async def approve_pending_order(order_id: str, user_id: str = Depends(get_current_user)):
    try:
        order = await live_trading_engine.approve_order(user_id=user_id, order_id=order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": order.id, "status": order.status, "executed_price": float(order.executed_price or 0)}


@router.post("/internal/bot-signal")
async def process_bot_signal(payload: BotSignalIn, user_id: str = Depends(get_current_user)):
    try:
        order = await live_trading_engine.process_bot_signal(
            user_id=user_id,
            bot_id=payload.bot_id,
            symbol=payload.symbol,
            side=payload.side,
            quantity=payload.quantity,
            execution_mode=payload.execution_mode,
        )
        return {"id": order.id, "status": order.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.websocket("/ws/market")
async def market_stream(websocket: WebSocket):
    await live_ws_manager.connect_public(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await live_ws_manager.disconnect(websocket)


@router.websocket("/ws/private")
async def private_stream(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        user_id = decode_token(token)
    except Exception:
        await websocket.close(code=4401)
        return
    await live_ws_manager.connect_private(websocket, user_id=user_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await live_ws_manager.disconnect(websocket, user_id=user_id)
