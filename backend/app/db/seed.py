"""
app/db/seed.py
──────────────
Seeds the STRATEGIES table with the 4 built-in strategies.

Called once on startup (idempotent — uses INSERT ... ON CONFLICT DO UPDATE).
The parameter_schema is the JSON Schema exported from the Pydantic config
models and is used by the frontend to dynamically build strategy config forms.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StrategyModel

logger = logging.getLogger(__name__)

# ── Strategy seed data ────────────────────────────────────────────────────────
# parameter_schema mirrors EMACrossoverConfig / RSIDivergenceConfig /
# BollingerBandsConfig / MACDSignalConfig from app/schemas/backtest.py.
# Keeping it here (rather than importing Pydantic models) avoids a circular
# import and lets the DB layer stay independent of the backtest engine.

_STRATEGIES: List[Dict[str, Any]] = [
    {
        "type_code":   "EMA_CROSSOVER",
        "name":        "EMA CrossOver",
        "description": (
            "Generates buy signals when the fast EMA crosses above the slow EMA "
            "(bullish momentum) and sell signals on the reverse crossover."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "fast_period": {
                    "type": "integer", "default": 12, "minimum": 3, "maximum": 50,
                    "description": "Short-term EMA period (range 3–50)",
                },
                "slow_period": {
                    "type": "integer", "default": 26, "minimum": 15, "maximum": 200,
                    "description": "Long-term EMA period (range 15–200)",
                },
                "source": {
                    "type": "string", "default": "CLOSE",
                    "enum": ["CLOSE", "OPEN", "HL2"],
                    "description": "Price source: CLOSE | OPEN | HL2",
                },
            },
            "required": ["fast_period", "slow_period", "source"],
        },
    },
    {
        "type_code":   "RSI_DIVERGENCE",
        "name":        "RSI Divergence",
        "description": (
            "Detects bullish/bearish divergence between price and RSI momentum. "
            "Buy when price makes a lower low but RSI makes a higher low; "
            "sell on the reverse."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "integer", "default": 14, "minimum": 2, "maximum": 50,
                    "description": "RSI calculation period (range 2–50)",
                },
                "oversold": {
                    "type": "integer", "default": 30, "minimum": 10, "maximum": 40,
                    "description": "Oversold threshold (range 10–40)",
                },
                "overbought": {
                    "type": "integer", "default": 70, "minimum": 60, "maximum": 90,
                    "description": "Overbought threshold (range 60–90)",
                },
                "lookback_periods": {
                    "type": "integer", "default": 5, "minimum": 3, "maximum": 10,
                    "description": "Bars to look back for divergence (range 3–10)",
                },
                "source": {
                    "type": "string", "default": "CLOSE",
                    "enum": ["CLOSE", "OPEN", "HL2"],
                    "description": "Price source: CLOSE | OPEN | HL2",
                },
            },
            "required": ["period", "oversold", "overbought", "lookback_periods", "source"],
        },
    },
    {
        "type_code":   "BOLLINGER_BANDS",
        "name":        "Bollinger Bands",
        "description": (
            "Mean-reversion strategy. Buys when price crosses below the lower band "
            "(oversold) and sells when price crosses above the upper band (overbought)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "integer", "default": 20, "minimum": 10, "maximum": 50,
                    "description": "SMA/std period (range 10–50)",
                },
                "std_dev": {
                    "type": "number", "default": 2.0, "minimum": 0.5, "maximum": 3.0,
                    "description": "Std deviation multiplier (range 0.5–3.0)",
                },
                "source": {
                    "type": "string", "default": "CLOSE",
                    "enum": ["CLOSE", "OPEN", "HL2"],
                    "description": "Price source: CLOSE | OPEN | HL2",
                },
            },
            "required": ["period", "std_dev", "source"],
        },
    },
    {
        "type_code":   "MACD_SIGNAL",
        "name":        "MACD Signal",
        "description": (
            "Buys when the MACD line crosses above the signal line (bullish momentum) "
            "and sells on the reverse crossover."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "fast_period": {
                    "type": "integer", "default": 12, "minimum": 6, "maximum": 30,
                    "description": "Fast EMA period (range 6–30)",
                },
                "slow_period": {
                    "type": "integer", "default": 26, "minimum": 15, "maximum": 50,
                    "description": "Slow EMA period (range 15–50)",
                },
                "signal_period": {
                    "type": "integer", "default": 9, "minimum": 5, "maximum": 15,
                    "description": "Signal line EMA period (range 5–15)",
                },
                "source": {
                    "type": "string", "default": "CLOSE",
                    "enum": ["CLOSE", "OPEN", "HL2"],
                    "description": "Price source: CLOSE | OPEN | HL2",
                },
            },
            "required": ["fast_period", "slow_period", "signal_period", "source"],
        },
    },
]


async def seed_strategies(session: AsyncSession) -> None:
    """
    Upsert the 4 built-in strategies into the STRATEGIES table.
    Uses INSERT ... ON CONFLICT (type_code) DO UPDATE so it is safe
    to run on every startup without duplicating rows.
    """
    for data in _STRATEGIES:
        stmt = (
            pg_insert(StrategyModel)
            .values(
                name=data["name"],
                type_code=data["type_code"],
                description=data["description"],
                parameter_schema=data["parameter_schema"],
            )
            .on_conflict_do_update(
                index_elements=["type_code"],
                set_={
                    "name":             data["name"],
                    "description":      data["description"],
                    "parameter_schema": data["parameter_schema"],
                },
            )
        )
        await session.execute(stmt)

    logger.info("Strategy seed complete (%d strategies).", len(_STRATEGIES))
