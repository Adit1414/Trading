import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from app.schemas.backtest import BacktestRunRequest
from app.modules.backtest.engine import run_backtest

async def main():
    request = BacktestRunRequest(
        strategy="EMA_CROSSOVER",
        strategy_config={"fast_period": 12, "slow_period": 26, "source": "CLOSE"},
        name="My EMA Test",
        symbol="BTCUSDT",
        contract_type="SPOT",
        trading_market="BINANCE",
        interval="1d",
        initial_cash=10000,
        commission=0.001,
        slippage=0.0005,
        order_size_mode="PCT_EQUITY",
        order_size_pct=100.0,
        intraday=False,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 6, 30),
    )

    result = await run_backtest(request)

    # ── Key results ──
    print(f"Return:  {result.statistics.total_return_pct:.2f}%")
    print(f"Sharpe:  {result.statistics.sharpe_ratio:.2f}")
    print(f"Trades:  {result.statistics.total_trades}")
    print(f"Win %:   {result.statistics.win_rate:.1f}%")
    print(f"MaxDD:   {result.statistics.max_drawdown_pct:.2f}%")
    print(result.statistics)

    # ── Save the chart ──
    with open("chart.html", "w", encoding="utf-8") as f:
        f.write(result.chart_html)

asyncio.run(main())
