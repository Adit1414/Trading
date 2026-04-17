from __future__ import annotations
import pandas as pd
from app.modules.backtest.strategies.base import BaseStrategy

class ColorStrategy(BaseStrategy):
    """
    Color Strategy:
    A momentum-based strategy that looks at the color of the previous candles.
    
    Buy Signal: N consecutive 'Green' (Bullish) candles.
    Sell Signal: N consecutive 'Red' (Bearish) candles.
    """
    
    display_name = "Bar Color Momentum"
    description = "Trades based on sequences of bullish or bearish candle colors."
    
    # JSON Schema for the frontend to build the configuration form
    config_schema = {
        "title": "ColorStrategyParams",
        "type": "object",
        "properties": {
            "lookback_count": {
                "title": "Lookback Count",
                "type": "integer",
                "default": 3,
                "description": "Number of consecutive same-color bars required to signal."
            }
        },
        "required": ["lookback_count"]
    }

    def __init__(self, parameters: dict):
        super().__init__(parameters)
        self.lookback_count = int(parameters.get("lookback_count", 3))

    @classmethod
    def get_min_bars_required(cls) -> int:
        return 10  # Enough bars to establish a trend

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals: 1 (Buy), -1 (Sell), 0 (Hold).
        """
        signals = pd.Series(0, index=df.index)
        
        # 1. Determine candle color: Close > Open is Bullish (1), else Bearish (-1)
        # Using a small epsilon to handle flat candles if necessary
        is_bullish = (df['close'] > df['open']).astype(int)
        is_bearish = (df['close'] < df['open']).astype(int)

        # 2. Rolling sum of bullish/bearish flags
        consecutive_bullish = is_bullish.rolling(window=self.lookback_count).sum()
        consecutive_bearish = is_bearish.rolling(window=self.lookback_count).sum()

        # 3. Apply logic
        # If the last N bars were all bullish, signal Buy (1)
        signals.loc[consecutive_bullish == self.lookback_count] = 1
        # If the last N bars were all bearish, signal Sell (-1)
        signals.loc[consecutive_bearish == self.lookback_count] = -1

        df['signal'] = signals
        return df