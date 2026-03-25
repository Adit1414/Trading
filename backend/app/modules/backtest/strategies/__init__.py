"""
app/modules/backtest/strategies/__init__.py
────────────────────────────────────────────
Strategy Registry — Binance Cryptocurrency

To add a new strategy:
  1. Subclass BaseStrategy in a new file.
  2. Import and add to STRATEGY_REGISTRY.
  3. Add its name to app/schemas/backtest.py::StrategyName.
  4. Add its config schema to STRATEGY_CONFIG_SCHEMAS.
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
    cls = STRATEGY_REGISTRY.get(strategy_id.upper())
    if cls is None:
        raise KeyError(
            f"Unknown strategy '{strategy_id}'. Available: {list(STRATEGY_REGISTRY)}"
        )
    return cls(config)


def list_strategies() -> list[dict]:
    """
    Return rich metadata for each strategy — used by the frontend to:
      • Populate the strategy selector dropdown.
      • Dynamically build the parameter configuration form
        (field names, types, defaults, min/max, descriptions).
    """
    from app.schemas.backtest import STRATEGY_CONFIG_SCHEMAS
    results = []
    for sid, cls in STRATEGY_REGISTRY.items():
        # Instantiate with defaults to get min_bars_required
        try:
            instance = cls({})
            min_bars = instance.min_bars_required
        except Exception:
            min_bars = 0

        # Export the config schema as JSON Schema for frontend form generation
        config_cls = STRATEGY_CONFIG_SCHEMAS.get(sid)
        schema = config_cls.model_json_schema() if config_cls else {}

        results.append({
            "id":               sid,
            "display_name":     cls.display_name,
            "description":      getattr(cls, "description", ""),
            "min_bars_required": min_bars,
            "config_schema":    schema,
        })
    return results


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