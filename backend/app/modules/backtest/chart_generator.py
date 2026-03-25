"""
app/modules/backtest/chart_generator.py
─────────────────────────────────────────
Interactive Plotly chart generator.

Produces a fully self-contained HTML string with NO external CDN dependencies
(plotly.js is embedded inline) so the frontend can inject it into an <iframe> or
dangerouslySetInnerHTML and it will work offline.

Layout (3 stacked panels, shared x-axis):
  Panel 1 — Equity / P&L curve
      • Peak (%), Final (%), Max Drawdown shading  (like Image 1 top panel)
  Panel 2 — Price / indicator chart   (largest panel)
      • OHLC candlesticks
      • Strategy indicator lines (EMA fast/slow, BB bands, MACD, RSI)
      • Buy markers  (green triangle-up) at entry price
      • Sell markers (red  triangle-down) at exit price
  Panel 3 — Volume bars  (like Image 1 bottom panel)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def generate_chart(
    df:           pd.DataFrame,
    equity_curve: list,           # List[EquityPoint]
    raw_trades:   List[Dict[str, Any]],
    strategy_id:  str,
    symbol:       str,
    initial_cash: float,
) -> str:
    """
    Build an interactive Plotly chart and return it as a self-contained HTML string.

    Args:
        df:           DataFrame with OHLCV + signal + indicator columns.
        equity_curve: List of EquityPoint(timestamp, value).
        raw_trades:   Raw trade dicts from simulate_trades().
        strategy_id:  e.g. "EMA_CROSSOVER".
        symbol:       e.g. "BTCUSDT".
        initial_cash: Starting capital (for P&L % baseline).

    Returns:
        A fully self-contained HTML string ready to embed in the frontend.
    """

    # ── Layout: 3 rows ────────────────────────────────────────────────────────
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.20, 0.60, 0.20],
        subplot_titles=(
            "Portfolio P&L (%)",
            f"{symbol} — {strategy_id.replace('_', ' ').title()}",
            "Volume",
        ),
    )

    timestamps = df.index

    # ══════════════════════════════════════════════════════════════════════════
    # Panel 1 — Equity / P&L curve
    # ══════════════════════════════════════════════════════════════════════════
    eq_ts  = [p.timestamp for p in equity_curve]
    eq_pct = [(p.value / initial_cash - 1) * 100 for p in equity_curve]

    # Peak equity % line
    peak_pct = []
    peak_val = initial_cash
    for p in equity_curve:
        if p.value > peak_val:
            peak_val = p.value
        peak_pct.append((peak_val / initial_cash - 1) * 100)

    fig.add_trace(go.Scatter(
        x=eq_ts, y=peak_pct,
        name="Peak (%)", line=dict(color="#ffffff", width=1, dash="dot"),
        hovertemplate="%{y:.2f}%<extra>Peak</extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=eq_ts, y=eq_pct,
        name="Final (%)",
        line=dict(color="#3b82f6", width=2),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.12)",
        hovertemplate="%{y:.2f}%<extra>Equity</extra>",
    ), row=1, col=1)

    # Max drawdown shading (red fill between peak and equity where equity < peak)
    dd_fill_y = [min(e, p) for e, p in zip(eq_pct, peak_pct)]
    fig.add_trace(go.Scatter(
        x=eq_ts + eq_ts[::-1],
        y=peak_pct + dd_fill_y[::-1],
        fill="toself",
        fillcolor="rgba(239,68,68,0.18)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Drawdown",
        showlegend=True,
        hoverinfo="skip",
    ), row=1, col=1)

    # ══════════════════════════════════════════════════════════════════════════
    # Panel 2 — OHLC candlesticks
    # ══════════════════════════════════════════════════════════════════════════
    fig.add_trace(go.Candlestick(
        x=timestamps,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="OHLC",
        increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
        increasing_fillcolor="#22c55e",
        decreasing_fillcolor="#ef4444",
    ), row=2, col=1)

    # ── Indicator overlays ────────────────────────────────────────────────────
    _add_indicator_traces(fig, df, strategy_id)

    # ── Trade markers ─────────────────────────────────────────────────────────
    buy_dates  = [t["entry_date"] for t in raw_trades]
    buy_prices = [t["entry_price"] for t in raw_trades]
    sell_dates  = [t["exit_date"]  for t in raw_trades if t.get("exit_date")]
    sell_prices = [t["exit_price"] for t in raw_trades if t.get("exit_price")]

    if buy_dates:
        fig.add_trace(go.Scatter(
            x=buy_dates, y=buy_prices,
            mode="markers",
            marker=dict(symbol="triangle-up", color="#22c55e", size=12,
                        line=dict(color="#ffffff", width=1)),
            name="Buy",
            hovertemplate="BUY @ %{y:.4f}<extra></extra>",
        ), row=2, col=1)

    if sell_dates:
        fig.add_trace(go.Scatter(
            x=sell_dates, y=sell_prices,
            mode="markers",
            marker=dict(symbol="triangle-down", color="#ef4444", size=12,
                        line=dict(color="#ffffff", width=1)),
            name="Sell",
            hovertemplate="SELL @ %{y:.4f}<extra></extra>",
        ), row=2, col=1)

    # ── Shaded trade regions ──────────────────────────────────────────────────
    _add_trade_bands(fig, raw_trades, df)

    # ══════════════════════════════════════════════════════════════════════════
    # Panel 3 — Volume bars
    # ══════════════════════════════════════════════════════════════════════════
    colors = [
        "#22c55e" if c >= o else "#ef4444"
        for c, o in zip(df["close"], df["open"])
    ]
    fig.add_trace(go.Bar(
        x=timestamps,
        y=df["volume"],
        name="Volume",
        marker_color=colors,
        opacity=0.7,
        hovertemplate="%{y:,.0f}<extra>Volume</extra>",
    ), row=3, col=1)

    # ══════════════════════════════════════════════════════════════════════════
    # Layout styling (dark theme)
    # ══════════════════════════════════════════════════════════════════════════
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0a0f",
        plot_bgcolor="#0d0d18",
        font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
        margin=dict(l=60, r=20, t=50, b=20),
        legend=dict(
            orientation="v",
            x=0.01, y=0.99,
            bgcolor="rgba(13,13,24,0.8)",
            bordercolor="#1e293b",
            borderwidth=1,
            font=dict(size=11),
        ),
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        height=700,
    )

    # Axis styling
    for i in range(1, 4):
        fig.update_xaxes(
            gridcolor="#1e293b", zeroline=False,
            showspikes=True, spikecolor="#475569",
            spikemode="across", spikethickness=1,
            row=i, col=1,
        )
        fig.update_yaxes(
            gridcolor="#1e293b", zeroline=False,
            showspikes=True, spikecolor="#475569",
            row=i, col=1,
        )

    # P&L panel y-axis
    fig.update_yaxes(ticksuffix="%", row=1, col=1)

    # Hide x-axis labels on panels 1 and 2 (shared x)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)

    # ── Export as fully self-contained HTML ───────────────────────────────────
    html = fig.to_html(
        full_html=True,
        include_plotlyjs=True,     # embed plotly.js inline — no CDN needed
        config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            "displaylogo": False,
            "scrollZoom": True,
        },
    )
    return html


# ─── Indicator overlay helper ────────────────────────────────────────────────

_INDICATOR_COLORS = [
    "#f97316",  # orange
    "#a855f7",  # purple
    "#06b6d4",  # cyan
    "#eab308",  # yellow
    "#ec4899",  # pink
]


def _add_indicator_traces(
    fig:         go.Figure,
    df:          pd.DataFrame,
    strategy_id: str,
) -> None:
    """Add strategy-specific indicator lines to panel 2."""
    sid = strategy_id.upper()

    if sid == "EMA_CROSSOVER":
        for col, name, color in [
            ("ema_fast", "EMA Fast", _INDICATOR_COLORS[0]),
            ("ema_slow", "EMA Slow", _INDICATOR_COLORS[1]),
        ]:
            if col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col],
                    name=name, line=dict(color=color, width=1.5),
                    hovertemplate=f"{name}: %{{y:.4f}}<extra></extra>",
                ), row=2, col=1)

    elif sid == "BOLLINGER_BANDS":
        if "bb_upper" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["bb_upper"],
                name="BB Upper", line=dict(color=_INDICATOR_COLORS[0], width=1.5, dash="dot"),
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df["bb_mid"],
                name="BB Mid", line=dict(color=_INDICATOR_COLORS[1], width=1),
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df["bb_lower"],
                name="BB Lower", line=dict(color=_INDICATOR_COLORS[2], width=1.5, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(6,182,212,0.06)",
            ), row=2, col=1)

    elif sid == "MACD_SIGNAL":
        # MACD is displayed as an oscillator sub-panel (row 2 bottom area)
        # We overlay the lines on the main chart using a secondary y-axis is complex —
        # instead we just overlay them as normalised lines relative to price.
        # The full MACD sub-panel is added as an annotation.
        for col, name, color in [
            ("macd_line",   "MACD",   _INDICATOR_COLORS[0]),
            ("macd_signal", "Signal", _INDICATOR_COLORS[1]),
        ]:
            if col in df.columns:
                # Normalise MACD to price scale for visual overlay
                macd_range = df[col].max() - df[col].min()
                price_range = df["close"].max() - df["close"].min()
                if macd_range > 0:
                    scale = price_range / macd_range * 0.2
                    mid   = df["close"].mean()
                    fig.add_trace(go.Scatter(
                        x=df.index,
                        y=df[col] * scale + mid,
                        name=name,
                        line=dict(color=color, width=1.5),
                        hovertemplate=f"{name}: %{{customdata:.4f}}<extra></extra>",
                        customdata=df[col],
                    ), row=2, col=1)

    elif sid == "RSI_DIVERGENCE":
        # RSI is shown as annotation text on the P&L panel
        if "rsi" in df.columns:
            # Normalise RSI (0-100) to price range for overlay
            price_min  = df["low"].min()
            price_max  = df["high"].max()
            price_range = price_max - price_min
            rsi_norm   = df["rsi"] / 100 * price_range + price_min
            fig.add_trace(go.Scatter(
                x=df.index, y=rsi_norm,
                name="RSI (scaled)",
                line=dict(color=_INDICATOR_COLORS[3], width=1.5, dash="dash"),
                hovertemplate="RSI: %{customdata:.1f}<extra></extra>",
                customdata=df["rsi"],
            ), row=2, col=1)


def _add_trade_bands(
    fig:        go.Figure,
    raw_trades: List[Dict[str, Any]],
    df:         pd.DataFrame,
) -> None:
    """Add green/red shaded rectangles over the chart for each closed trade."""
    price_min = float(df["low"].min())
    price_max = float(df["high"].max())

    for t in raw_trades:
        if not t.get("exit_date"):
            continue
        pnl   = t.get("pnl", 0) or 0
        color = "rgba(34,197,94,0.10)" if pnl >= 0 else "rgba(239,68,68,0.10)"
        fig.add_vrect(
            x0=t["entry_date"], x1=t["exit_date"],
            fillcolor=color, opacity=1,
            layer="below", line_width=0,
            row=2, col=1,
        )
