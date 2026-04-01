"""
app/modules/backtest/strategies/__init__.py
────────────────────────────────────────────
Strategy Registry

To add a new strategy:
  1. Implement BaseStrategy in a new file inside this package.
  2. Import it here and add it to STRATEGY_REGISTRY.
  3. Add its name to app/schemas/backtest.py::StrategyName.

Module 4 (Bot Execution) imports `get_strategy` from this registry
to instantiate the configured strategy for live trading.
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


def get_strategy(strategy_id: str, config: Dict[str, Any]) -> BaseStrategy:
    """
    Instantiate and return a configured strategy by its ID.

    Args:
        strategy_id: One of the keys in STRATEGY_REGISTRY.
        config:      Strategy-specific parameter dict.

    Raises:
        KeyError:              Unknown strategy_id.
        StrategyConfigError:   Invalid config parameters.
    """
    cls = STRATEGY_REGISTRY.get(strategy_id.upper())
    if cls is None:
        raise KeyError(
            f"Unknown strategy '{strategy_id}'. "
            f"Available: {list(STRATEGY_REGISTRY)}"
        )
    return cls(config)


def list_strategies() -> list[dict]:
    """Return metadata for all registered strategies (for a /strategies endpoint)."""
    return [
        {
            "id": key,
            "display_name": cls.display_name,
            "min_bars_required": cls({}).min_bars_required
            if hasattr(cls({}), "min_bars_required")
            else None,
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
    "get_strategy",
    "list_strategies",
]