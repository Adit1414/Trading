from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.exc import ProgrammingError

from app.core.security import decrypt_api_key
from app.db.models import BotModel, OrderModel, PositionModel, UserSettingsModel
from app.db.session import get_db
from app.services.live.exchange import get_binance_client
from app.services.live.ws_manager import live_ws_manager

logger = logging.getLogger(__name__)


def _is_missing_orders_table_error(exc: Exception) -> bool:
    """
    Detect the startup race where migrations are not applied yet and `orders`
    does not exist. asyncpg wraps this as ProgrammingError/UndefinedTableError.
    """
    if not isinstance(exc, ProgrammingError):
        return False
    message = str(exc).lower()
    return 'relation "orders" does not exist' in message or "undefinedtableerror" in message


class LiveTradingEngine:
    async def process_bot_signal(
        self,
        *,
        user_id: str,
        bot_id: str,
        symbol: str,
        side: str,
        quantity: float,
        execution_mode: str,
    ) -> OrderModel:
        async with get_db() as session:
            if session is None:
                raise RuntimeError("Database is not configured.")

            bot = (
                await session.execute(
                    select(BotModel).where(and_(BotModel.id == bot_id, BotModel.user_id == user_id))
                )
            ).scalar_one_or_none()
            if bot is None:
                raise ValueError("Bot not found for this user.")

            normalized_side = side.upper()
            normalized_mode = execution_mode.upper()

            if normalized_mode == "PAPER":
                order = await self._execute_paper(
                    session=session, user_id=user_id, bot_id=bot_id, symbol=symbol, side=normalized_side, quantity=quantity
                )
            elif normalized_mode == "LIVE" and not bot.requires_permission:
                order = await self._execute_live_autonomous(
                    session=session, user_id=user_id, bot_id=bot_id, symbol=symbol, side=normalized_side, quantity=quantity
                )
            elif normalized_mode == "LIVE" and bot.requires_permission:
                order = await self._queue_for_approval(
                    session=session, user_id=user_id, bot_id=bot_id, symbol=symbol, side=normalized_side, quantity=quantity
                )
            else:
                raise ValueError("Invalid execution mode.")

            await session.flush()
            return order

    async def _execute_paper(self, *, session, user_id: str, bot_id: str, symbol: str, side: str, quantity: float) -> OrderModel:
        simulated_price = 100.0
        order = OrderModel(
            user_id=user_id,
            bot_id=bot_id,
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            execution_mode="PAPER",
            status="FILLED",
            executed_price=simulated_price,
        )
        session.add(order)
        session.add(
            PositionModel(
                user_id=user_id,
                bot_id=bot_id,
                pair=symbol.upper(),
                side=side,
                size=quantity,
                entry_price=simulated_price,
                unrealized_pnl=0,
                is_open=True,
            )
        )
        await live_ws_manager.publish_private(
            user_id,
            "ORDER_EXECUTED",
            {"execution_mode": "PAPER", "symbol": symbol.upper(), "side": side, "quantity": quantity},
        )
        return order

    async def _execute_live_autonomous(self, *, session, user_id: str, bot_id: str, symbol: str, side: str, quantity: float) -> OrderModel:
        settings = (
            await session.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))
        ).scalar_one_or_none()
        if settings is None or not settings.binance_api_key or not settings.binance_secret:
            raise ValueError("Binance credentials are not configured.")

        exchange = get_binance_client(
            decrypt_api_key(settings.binance_api_key),
            decrypt_api_key(settings.binance_secret),
            sandbox=False,
        )
        try:
            response: dict[str, Any] = await exchange.create_market_order(symbol.upper(), side.lower(), quantity)
        finally:
            await exchange.close()

        executed_price = float(response.get("average") or response.get("price") or 0)
        order = OrderModel(
            user_id=user_id,
            bot_id=bot_id,
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            execution_mode="LIVE",
            status="FILLED",
            exchange_order_id=str(response.get("id") or ""),
            executed_price=executed_price,
        )
        session.add(order)
        session.add(
            PositionModel(
                user_id=user_id,
                bot_id=bot_id,
                pair=symbol.upper(),
                side=side,
                size=quantity,
                entry_price=executed_price or 0,
                unrealized_pnl=0,
                is_open=True,
            )
        )
        await live_ws_manager.publish_private(
            user_id, "ORDER_EXECUTED", {"execution_mode": "LIVE", "symbol": symbol.upper(), "side": side, "quantity": quantity}
        )
        return order

    async def _queue_for_approval(self, *, session, user_id: str, bot_id: str, symbol: str, side: str, quantity: float) -> OrderModel:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        order = OrderModel(
            user_id=user_id,
            bot_id=bot_id,
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            execution_mode="LIVE",
            status="PENDING_APPROVAL",
            expires_at=expires_at,
        )
        session.add(order)
        await live_ws_manager.publish_private(
            user_id,
            "ORDER_APPROVAL_REQUIRED",
            {"symbol": symbol.upper(), "side": side, "quantity": quantity, "expires_at": expires_at.isoformat()},
        )
        return order

    async def approve_order(self, *, user_id: str, order_id: str) -> OrderModel:
        async with get_db() as session:
            if session is None:
                raise RuntimeError("Database is not configured.")
            order = (
                await session.execute(select(OrderModel).where(and_(OrderModel.id == order_id, OrderModel.user_id == user_id)))
            ).scalar_one_or_none()
            if order is None:
                raise ValueError("Order not found.")
            if order.status != "PENDING_APPROVAL":
                raise ValueError("Only pending approval orders can be approved.")
            if order.expires_at and order.expires_at < datetime.now(timezone.utc):
                order.status = "EXPIRED"
                raise ValueError("Order already expired.")

            settings = (
                await session.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))
            ).scalar_one_or_none()
            if settings is None or not settings.binance_api_key or not settings.binance_secret:
                raise ValueError("Binance credentials are not configured.")

            exchange = get_binance_client(
                decrypt_api_key(settings.binance_api_key),
                decrypt_api_key(settings.binance_secret),
                sandbox=False,
            )
            try:
                response: dict[str, Any] = await exchange.create_market_order(order.symbol, order.side.lower(), float(order.quantity))
            finally:
                await exchange.close()

            order.status = "FILLED"
            order.exchange_order_id = str(response.get("id") or "")
            order.executed_price = float(response.get("average") or response.get("price") or 0)
            session.add(
                PositionModel(
                    user_id=user_id,
                    bot_id=order.bot_id,
                    pair=order.symbol,
                    side=order.side,
                    size=order.quantity,
                    entry_price=order.executed_price or 0,
                    unrealized_pnl=0,
                    is_open=True,
                )
            )
            await live_ws_manager.publish_private(user_id, "ORDER_APPROVED", {"order_id": order_id, "status": order.status})
            await session.flush()
            return order


async def expire_pending_orders_task() -> None:
    missing_table_reported = False
    while True:
        try:
            async with get_db() as session:
                if session is not None:
                    now = datetime.now(timezone.utc)
                    result = await session.execute(
                        select(OrderModel).where(
                            and_(
                                OrderModel.status == "PENDING_APPROVAL",
                                OrderModel.expires_at.is_not(None),
                                OrderModel.expires_at < now,
                            )
                        )
                    )
                    expired = result.scalars().all()
                    for order in expired:
                        order.status = "EXPIRED"
                        await live_ws_manager.publish_private(
                            order.user_id,
                            "ORDER_EXPIRED",
                            {"order_id": order.id, "symbol": order.symbol},
                        )
            missing_table_reported = False
        except Exception as exc:
            if _is_missing_orders_table_error(exc):
                if not missing_table_reported:
                    logger.warning(
                        "Pending order expiry loop paused: `orders` table is missing. "
                        "Run Alembic migrations (`alembic upgrade head`)."
                    )
                    missing_table_reported = True
            else:
                logger.warning("Pending order expiry loop failed: %s", exc)
        await asyncio.sleep(5)


live_trading_engine = LiveTradingEngine()
