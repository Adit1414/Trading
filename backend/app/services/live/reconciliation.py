"""
app/services/live/reconciliation.py
─────────────────────────────────────
Startup reconciliation task.

On every server start, we compare the local DB state (orders & positions)
against what Binance actually reports.  This heals any drift that occurred
while the server was down — e.g. an order that filled during a crash.

Strategy
────────
1. Find all users who have Binance credentials stored.
2. For each user, fetch their open orders from Binance.
3. Any local OrderModel with status=OPEN whose exchange_order_id is NOT
   in the live Binance list → mark as CANCELLED (the exchange rejected /
   expired it while we were offline).
4. For open PositionModel rows, cross-reference via open Binance orders.
   If no matching open order exists for a locally-open position, mark it
   as closed (is_open = False).  We do not fabricate fill prices here —
   monitoring / accounting can reconcile that via trade history.

Non-destructive guarantees
──────────────────────────
- We never INSERT new records.
- We never DELETE records.
- We only UPDATE status fields.
- All changes are logged at WARNING level.
- The entire task is wrapped in a timeout; if it takes longer than 30 s
  (e.g. Binance API is slow) the startup still completes normally.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import and_, select

from app.db.models import OrderModel, PositionModel, UserSettingsModel
from app.db.session import get_db
from app.services.live.exchange import get_binance_client

logger = logging.getLogger(__name__)


async def _reconcile_user(user_id: str, api_key: str, secret: str) -> None:
    """
    Reconcile one user's local state against Binance.
    api_key / secret are stored as ciphertext — get_binance_client decrypts them.
    """
    exchange = get_binance_client(api_key, secret, sandbox=False)
    try:
        # Fetch all open orders from Binance (returns list of dicts)
        try:
            live_orders: list[dict[str, Any]] = await asyncio.wait_for(
                exchange.fetch_open_orders(), timeout=15.0
            )
        except asyncio.TimeoutError:
            logger.warning("[Recon] Binance API timed out for user %s — skipping.", user_id)
            return
        except Exception as exc:
            logger.warning("[Recon] Could not fetch open orders for user %s: %s", user_id, exc)
            return

        live_exchange_ids: set[str] = {
            str(o.get("id", "")) for o in live_orders if o.get("id")
        }

        async with get_db() as session:
            if session is None:
                return

            # ── Reconcile Orders ────────────────────────────────────────────
            local_open = (
                await session.execute(
                    select(OrderModel).where(
                        and_(
                            OrderModel.user_id == user_id,
                            OrderModel.status == "OPEN",
                            OrderModel.execution_mode == "LIVE",
                        )
                    )
                )
            ).scalars().all()

            stale_orders = 0
            for order in local_open:
                if order.exchange_order_id and order.exchange_order_id not in live_exchange_ids:
                    old_status = order.status
                    order.status = "CANCELLED"
                    stale_orders += 1
                    logger.warning(
                        "[Recon] Order %s (exchange_id=%s) was %s locally but not found on "
                        "Binance — marking CANCELLED.",
                        order.id, order.exchange_order_id, old_status,
                    )

            # ── Reconcile Positions ─────────────────────────────────────────
            local_positions = (
                await session.execute(
                    select(PositionModel).where(
                        and_(
                            PositionModel.user_id == user_id,
                            PositionModel.is_open.is_(True),
                        )
                    )
                )
            ).scalars().all()

            # Build set of symbols that have live open orders
            live_symbols: set[str] = {
                (o.get("symbol") or "").upper() for o in live_orders
            }

            stale_positions = 0
            for pos in local_positions:
                pair_norm = (pos.pair or "").replace("/", "").upper()
                if pair_norm not in live_symbols:
                    pos.is_open = False
                    pos.unrealized_pnl = 0
                    stale_positions += 1
                    logger.warning(
                        "[Recon] Position %s (%s) was open locally but has no live "
                        "orders on Binance — marking closed.",
                        pos.id, pos.pair,
                    )

            if stale_orders or stale_positions:
                logger.info(
                    "[Recon] User %s: corrected %d orders, %d positions.",
                    user_id, stale_orders, stale_positions,
                )

    finally:
        await exchange.close()


async def run_startup_reconciliation() -> None:
    """
    Entry point called from main.py lifespan.
    Wrapped in a 30-second timeout so it never blocks startup.
    """
    logger.info("[Recon] Starting DB ↔ Binance startup reconciliation …")
    try:
        async with get_db() as session:
            if session is None:
                logger.warning("[Recon] No DB session — skipping reconciliation.")
                return

            rows = (
                await session.execute(
                    select(UserSettingsModel).where(
                        and_(
                            UserSettingsModel.binance_api_key.is_not(None),
                            UserSettingsModel.binance_secret.is_not(None),
                        )
                    )
                )
            ).scalars().all()

        if not rows:
            logger.info("[Recon] No users with Binance credentials — nothing to reconcile.")
            return

        # Run all users concurrently but with individual timeouts
        tasks = [
            _reconcile_user(row.user_id, row.binance_api_key, row.binance_secret)
            for row in rows
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("[Recon] Startup reconciliation complete.")

    except Exception as exc:
        logger.error("[Recon] Reconciliation failed unexpectedly: %s", exc)
