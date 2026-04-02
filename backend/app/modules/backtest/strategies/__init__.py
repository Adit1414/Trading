"""
app/modules/backtest/strategies/__init__.py
────────────────────────────────────────────
Strategy Registry

To add a new strategy:
  1. Implement BaseStrategy in a new file inside this package.
  2. Import it here and add it to STRATEGY_REGISTRY.
  3. Add its name to app/schemas/backtest.py::StrategyName.
"""

from __future__ import annotations

from typing import Any, Dict, Type

from app.modules.backtest.strategies.base import BaseStrategy
from app.modules.backtest.strategies.bollinger_bands import BollingerBandsStrategy
from app.modules.backtest.strategies.ema_crossover import EMACrossoverStrategy
from app.modules.backtest.strategies.macd_signal import MACDSignalStrategy
from app.modules.backtest.strategies.rsi_divergence import RSIDivergenceStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "EMA_CROSSOVER":   EMACrossoverStrategy,
    "RSI_DIVERGENCE":  RSIDivergenceStrategy,
    "BOLLINGER_BANDS": BollingerBandsStrategy,
    "MACD_SIGNAL":     MACDSignalStrategy,
}


def get_strategy_class(strategy_id: str) -> Type[BaseStrategy]:
    """
    Return strategy class by its ID.
    """
    cls = STRATEGY_REGISTRY.get(strategy_id.upper())
    if cls is None:
        raise KeyError(
            f"Unknown strategy '{strategy_id}'. "
            f"Available: {list(STRATEGY_REGISTRY)}"
        )
    return cls


def list_strategies() -> list[dict]:
    """Return metadata for all registered strategies."""
    return [
        {
            "id": key,
            "display_name": cls.display_name,
            "min_bars_required": cls.get_min_bars_required(),
        }
        for key, cls in STRATEGY_REGISTRY.items()
    ]


__all__ = [
    "BaseStrategy",
    "EMACrossoverStrategy",
    "RSIDivergenceStrategy",
    "BollingerBandsStrategy",
    "MACDSignalStrategy",
    "STRATEGY_REGISTRY",
    "get_strategy_class",
    "list_strategies",
]