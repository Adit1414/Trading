import pytest
import pandas as pd
from app.modules.backtest.performance import calculate_statistics

def test_calculate_statistics_no_trades():
    # Empty trade log
    trades = []
    stats = calculate_statistics(trades, initial_capital=10000.0)
    assert stats["net_profit"] == 0.0
    assert stats["total_trades"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["max_drawdown"] == 0.0

def test_calculate_statistics_with_trades():
    trades = [
        {"timestamp": "2023-01-01", "pnl": 100.0, "capital": 10100.0},
        {"timestamp": "2023-01-02", "pnl": -50.0, "capital": 10050.0},
        {"timestamp": "2023-01-03", "pnl": 200.0, "capital": 10250.0},
    ]
    stats = calculate_statistics(trades, initial_capital=10000.0)
    assert stats["net_profit"] == 250.0
    assert stats["total_trades"] == 3
    assert stats["win_bytes"] == 2  # Assuming logic defines win_trades
    assert stats["win_rate"] == 66.67
