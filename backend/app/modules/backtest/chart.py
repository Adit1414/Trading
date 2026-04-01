"""
app/modules/backtest/chart.py
──────────────────────────────
Interactive Plotly chart builder for backtest results.

Generates a 3-panel (or 4-panel for RSI) interactive chart:
  Row 1 – Candlestick + strategy-specific indicators + buy/sell markers
  Row 2 – Equity curve  (Strategy vs Buy & Hold)
  Row 3 – Volume bars
  Row 4 – RSI panel (only for RSI_DIVERGENCE strategy)

Ported from backtest.ipynb and generalised to support all four strategies.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Directory to persist generated chart HTML files
_CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "charts")


def _ensure_charts_dir() -> str:
    """Create the charts directory if it doesn't exist and return its path."""
    charts_path = os.path.abspath(_CHARTS_DIR)
    os.makedirs(charts_path, exist_ok=True)
    return charts_path


def _compute_chart_stats(
    df: pd.DataFrame,
    initial_cash: float,
) -> Dict[str, str]:
    """
    Compute summary statistics for the chart banner.

    Uses the 'strat_equity' column built by prepare_chart_dataframe().
    """
    strat_ret = df["strat_ret"].dropna()
    final_equity = df["strat_equity"].iloc[-1]
    total_return_pct = (final_equity - initial_cash) / initial_cash * 100

    # Sharpe ratio (annualised, assuming daily bars)
    if strat_ret.std() > 0:
        sharpe = strat_ret.mean() / strat_ret.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    # Maximum drawdown
    running_max = df["strat_equity"].cummax()
    drawdown = (df["strat_equity"] - running_max) / running_max
    max_dd = drawdown.min() * 100

    # Round trips (buy-sell pairs)
    if "position" in df.columns:
        round_trips = int(df["position"].abs().sum() // 2)
    else:
        round_trips = int(df["signal"].abs().sum() // 2)

    return {
        "Final Equity": f"${final_equity:,.2f}",
        "Total Return": f"{total_return_pct:.2f}%",
        "Sharpe Ratio": f"{sharpe:.2f}",
        "Max Drawdown": f"{max_dd:.2f}%",
        "# Round Trips": str(round_trips),
    }


def prepare_chart_dataframe(
    df: pd.DataFrame,
    initial_cash: float,
) -> pd.DataFrame:
    """
    Enrich the signal-annotated DataFrame with equity-curve columns
    needed for charting.

    Adds:
      - position      (diff of binary signal for detecting entry/exit)
      - trade         (shifted signal — acts on next bar)
      - mkt_ret       (market daily return)
      - strat_ret     (strategy daily return)
      - mkt_equity    (buy & hold equity curve)
      - strat_equity  (strategy equity curve)
      - buy_signal    (price at buy points, NaN elsewhere)
      - sell_signal   (price at sell points, NaN elsewhere)
    """
    df = df.copy()

    # Binary position: 1 when in market, 0 when out
    df["binary_signal"] = np.where(df["signal"] >= 1, 1, 0)
    # Forward-fill: once we buy, stay in until a sell
    # Better approach: use signal column to track state
    position = 0
    positions = []
    for sig in df["signal"].values:
        if sig == 1:
            position = 1
        elif sig == -1:
            position = 0
        positions.append(position)
    df["trade"] = pd.Series(positions, index=df.index).shift(1).fillna(0)

    # Detect transitions for buy/sell markers
    df["position"] = df["trade"].diff().fillna(0)

    df["mkt_ret"] = df["close"].pct_change().fillna(0)
    df["strat_ret"] = df["trade"] * df["mkt_ret"]

    df["mkt_equity"] = initial_cash * (1 + df["mkt_ret"]).cumprod()
    df["strat_equity"] = initial_cash * (1 + df["strat_ret"]).cumprod()

    df["buy_signal"] = np.where(df["position"] == 1, df["close"], np.nan)
    df["sell_signal"] = np.where(df["position"] == -1, df["close"], np.nan)

    return df


def build_backtest_chart(
    df: pd.DataFrame,
    stats: Dict[str, str],
    strategy_name: str = "EMA_CROSSOVER",
) -> "go.Figure":
    """
    Build the multi-panel interactive Plotly figure.

    Args:
        df:            DataFrame from prepare_chart_dataframe() with indicator
                       columns (e.g. ema_fast, ema_slow, rsi, bb_upper, …).
        stats:         Summary statistics dict from _compute_chart_stats().
        strategy_name: One of the registered strategy IDs.

    Returns:
        A plotly Figure object ready for rendering or serialisation.
    """
    if not PLOTLY_AVAILABLE:
        raise RuntimeError("plotly is not installed – run: pip install plotly")

    # Determine if we need an extra RSI row
    has_rsi = "rsi" in df.columns and strategy_name == "RSI_DIVERGENCE"
    has_macd = all(c in df.columns for c in ["macd_line", "macd_signal", "macd_hist"]) and strategy_name == "MACD_SIGNAL"

    if has_rsi:
        n_rows = 4
        row_heights = [0.40, 0.25, 0.15, 0.20]
        subtitles = (
            _price_subtitle(strategy_name),
            "Equity Curve  (Strategy vs Buy & Hold)",
            "Volume",
            "RSI",
        )
    elif has_macd:
        n_rows = 4
        row_heights = [0.40, 0.20, 0.15, 0.25]
        subtitles = (
            _price_subtitle(strategy_name),
            "Equity Curve  (Strategy vs Buy & Hold)",
            "Volume",
            "MACD",
        )
    else:
        n_rows = 3
        row_heights = [0.50, 0.30, 0.20]
        subtitles = (
            _price_subtitle(strategy_name),
            "Equity Curve  (Strategy vs Buy & Hold)",
            "Volume",
        )

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.04,
        subplot_titles=subtitles,
    )

    # ── Row 1: Candlestick ──────────────────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    # ── Strategy-specific overlays on Row 1 ─────────────────────────────────
    if "ema_fast" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["ema_fast"],
                name="EMA Fast",
                line=dict(color="#f9a825", width=1.5),
            ),
            row=1, col=1,
        )
    if "ema_slow" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["ema_slow"],
                name="EMA Slow",
                line=dict(color="#7c4dff", width=1.5),
            ),
            row=1, col=1,
        )
    if "bb_upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["bb_upper"],
                name="BB Upper",
                line=dict(color="#ff9800", width=1, dash="dot"),
            ),
            row=1, col=1,
        )
    if "bb_mid" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["bb_mid"],
                name="BB Mid",
                line=dict(color="#9e9e9e", width=1, dash="dash"),
            ),
            row=1, col=1,
        )
    if "bb_lower" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["bb_lower"],
                name="BB Lower",
                line=dict(color="#ff9800", width=1, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(255,152,0,0.06)",
            ),
            row=1, col=1,
        )

    # ── Buy / Sell markers ──────────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["buy_signal"],
            mode="markers",
            name="Buy",
            marker=dict(symbol="triangle-up", size=12, color="#00e676"),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["sell_signal"],
            mode="markers",
            name="Sell",
            marker=dict(symbol="triangle-down", size=12, color="#ff1744"),
        ),
        row=1, col=1,
    )

    # ── Row 2: Equity curve ─────────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["strat_equity"],
            name="Strategy",
            line=dict(color="#00bcd4", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,188,212,0.08)",
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["mkt_equity"],
            name="Buy & Hold",
            line=dict(color="#ff9800", width=2, dash="dot"),
        ),
        row=2, col=1,
    )

    # ── Row 3: Volume ───────────────────────────────────────────────────────
    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["close"].values, df["open"].values)
    ]
    fig.add_trace(
        go.Bar(
            x=df.index, y=df["volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.7,
        ),
        row=3, col=1,
    )

    # ── Row 4 (optional): RSI ──────────────────────────────────────────────
    if has_rsi:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["rsi"],
                name="RSI",
                line=dict(color="#e040fb", width=1.5),
            ),
            row=4, col=1,
        )
        # Overbought / oversold reference lines
        fig.add_hline(y=70, line_dash="dash", line_color="#ff5252", line_width=0.8, row=4, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#69f0ae", line_width=0.8, row=4, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="#616161", line_width=0.5, row=4, col=1)

    # ── Row 4 (optional): MACD ─────────────────────────────────────────────
    if has_macd:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["macd_line"],
                name="MACD Line",
                line=dict(color="#00bcd4", width=1.5),
            ),
            row=4, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["macd_signal"],
                name="Signal Line",
                line=dict(color="#ff9800", width=1.5),
            ),
            row=4, col=1,
        )
        hist_colors = [
            "#26a69a" if v >= 0 else "#ef5350"
            for v in df["macd_hist"].values
        ]
        fig.add_trace(
            go.Bar(
                x=df.index, y=df["macd_hist"],
                name="MACD Histogram",
                marker_color=hist_colors,
                opacity=0.6,
            ),
            row=4, col=1,
        )
        fig.add_hline(y=0, line_dash="dot", line_color="#616161", line_width=0.5, row=4, col=1)

    # ── Layout ──────────────────────────────────────────────────────────────
    stats_text = "  |  ".join(f"<b>{k}</b>: {v}" for k, v in stats.items())
    strategy_label = strategy_name.replace("_", " ").title()
    fig.update_layout(
        title=dict(
            text=f"{strategy_label}  —  {stats_text}",
            font=dict(size=13),
        ),
        template="plotly_dark",
        height=900 if n_rows <= 3 else 1100,
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
    )
    fig.update_yaxes(gridcolor="#1e2130")
    fig.update_xaxes(gridcolor="#1e2130")

    return fig


def render_chart_html(fig: "go.Figure") -> str:
    """Convert a Plotly Figure to a self-contained HTML string."""
    if not PLOTLY_AVAILABLE:
        raise RuntimeError("plotly is not installed – run: pip install plotly")
    return fig.to_html(include_plotlyjs=True, full_html=True)


def save_chart_html(fig: "go.Figure", backtest_id: str) -> str:
    """
    Save the chart to disk as ``charts/{backtest_id}.html``.

    Returns the absolute path to the saved file.
    """
    charts_dir = _ensure_charts_dir()
    filepath = os.path.join(charts_dir, f"{backtest_id}.html")
    fig.write_html(filepath, include_plotlyjs=True, full_html=True)
    logger.info("Chart saved → %s (%d KB)", filepath, os.path.getsize(filepath) // 1024)
    return filepath


def get_chart_path(backtest_id: str) -> Optional[str]:
    """Return the absolute path to a saved chart, or None if not found."""
    charts_dir = os.path.abspath(_CHARTS_DIR)
    filepath = os.path.join(charts_dir, f"{backtest_id}.html")
    if os.path.exists(filepath):
        return filepath
    return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _price_subtitle(strategy_name: str) -> str:
    """Return a descriptive subtitle for the price panel."""
    labels = {
        "EMA_CROSSOVER": "Price  |  EMA Crossover  |  Signals",
        "RSI_DIVERGENCE": "Price  |  RSI Divergence  |  Signals",
        "BOLLINGER_BANDS": "Price  |  Bollinger Bands  |  Signals",
        "MACD_SIGNAL": "Price  |  MACD Signal  |  Signals",
    }
    return labels.get(strategy_name, f"Price  |  {strategy_name}  |  Signals")
