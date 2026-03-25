"""
app/services/market_data/binance.py
─────────────────────────────────────
Binance REST API market data provider — cryptocurrency only (SRS §1.2).

Endpoint: GET /api/v3/klines
Docs:     https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data

Request parameters (Image 1):
  symbol    – String, required.  Trading pair, no special characters. e.g. "BTCUSDT"
  interval  – Enum,   required.  Candlestick timeframe. e.g. "15m", "1h", "1d"
  limit     – Int,    optional.  Candles per request. Default 500, Maximum 1000.
  startTime – Long,   optional.  Unix timestamp (ms) to start fetching from.
  endTime   – Long,   optional.  Unix timestamp (ms) to stop fetching at.
  timeZone  – String, optional.  Default "0" (UTC).

Response format (Image 2) — each element is an array:
  [0]  Open time          Long    Unix ms when the candle opened.
  [1]  Open               String  Opening price.
  [2]  High               String  Highest price.
  [3]  Low                String  Lowest price.
  [4]  Close              String  Closing price.
  [5]  Volume             String  Base asset volume.
  [6]  Close time         Long    Unix ms when the candle closed.  ← pagination cursor
  [7]  Quote asset volume String
  [8]  Number of trades   Int
  [9]  Taker buy base vol String
  [10] Taker buy quote vol String
  [11] Ignore             String

Pagination: we request 1000 bars per call (max) to minimise API round-trips.
  After each page the next startTime = raw[-1][6] + 1  (close time of last bar + 1 ms).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import List

import httpx

from app.core.config import settings
from app.services.market_data.base import OHLCV, MarketDataProvider

logger = logging.getLogger(__name__)

_KLINES_ENDPOINT       = "/api/v3/klines"
_EXCHANGE_INFO_ENDPOINT = "/api/v3/exchangeInfo"

# Use maximum bars per request to minimise API round-trips.
_FETCH_LIMIT   = 1000      # Binance maximum per request (Image 1)
_MAX_RETRIES   = 3
_BACKOFF_BASE  = 1.5       # seconds; wait = BACKOFF_BASE ** attempt


def _to_ms(dt: datetime) -> int:
    """Convert datetime → Unix milliseconds (Binance startTime / endTime format)."""
    return int(dt.timestamp() * 1000)


def _parse_row(row: list) -> OHLCV:
    """
    Parse a single Binance K-line array into an OHLCV dataclass.
    Index mapping per Image 2:
      [0] open_time_ms, [1] open, [2] high, [3] low, [4] close,
      [5] volume, [6] close_time_ms (used as pagination cursor)
    """
    open_time_ms: int = row[0]
    return OHLCV(
        # ISO-8601 UTC string using the candle's OPEN time (index 0)
        timestamp=datetime.fromtimestamp(
            open_time_ms / 1000, tz=timezone.utc
        ).isoformat(),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]),
    )


class BinanceMarketData(MarketDataProvider):
    """
    Concrete Binance implementation of MarketDataProvider.

    Uses public (unauthenticated) REST endpoints for historical K-line data —
    no API key required for backtesting (SRS §3.2).

    Integration with Module 3 (Streamer):
      Module 3's WebSocket Supervisor handles live ticks separately.
      This class covers only the REST / historical side (Module 2).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.binance_history_base_url

    async def fetch_klines(
        self,
        symbol:     str,
        interval:   str,
        start_date: date,
        end_date:   date,
    ) -> List[OHLCV]:
        """
        Fetch all K-lines for the given date range via paginated requests.

        Pagination (per Image 1 / Image 2):
          • Each request asks for `limit=1000` bars starting at `startTime`.
          • After each page, the next startTime = row[-1][6] + 1
            (close time of last bar + 1 ms) so there is no overlap or gap.
          • Loop exits when the page is shorter than 1000 (end of data)
            or when the next startTime would exceed endTime.

        Args:
            symbol:     Binance trading pair, e.g. "BTCUSDT".
            interval:   K-line interval string, e.g. "1d".
            start_date: Inclusive start date (UTC).
            end_date:   Inclusive end date (UTC).

        Returns:
            Time-ascending list of OHLCV objects.
        """
        # Convert date objects to millisecond timestamps (Image 1: startTime / endTime)
        start_ms = _to_ms(
            datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        )
        end_ms = _to_ms(
            datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
        )

        all_bars: List[OHLCV] = []
        current_start_ms = start_ms

        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            while current_start_ms <= end_ms:
                # Build request parameters per Image 1
                params = {
                    "symbol":    symbol.upper(),
                    "interval":  interval,
                    "startTime": current_start_ms,
                    "endTime":   end_ms,
                    "limit":     _FETCH_LIMIT,     # max 1000 per request
                    "timeZone":  "0",              # always UTC (Image 1 default)
                }

                raw: list = await self._get_with_retry(client, _KLINES_ENDPOINT, params)

                if not raw:
                    break  # No more data returned by Binance

                # Parse each row using correct index mapping (Image 2)
                bars = [_parse_row(row) for row in raw]
                all_bars.extend(bars)

                # Advance cursor: use close time (index 6) of last bar + 1 ms
                last_close_time_ms: int = raw[-1][6]   # Image 2 index [6]
                current_start_ms = last_close_time_ms + 1

                # Received fewer bars than requested → we have reached the end
                if len(raw) < _FETCH_LIMIT:
                    break

        logger.info(
            "Binance fetch complete: %s %s [%s → %s] → %d bars",
            symbol, interval, start_date, end_date, len(all_bars),
        )
        return all_bars

    async def validate_symbol(self, symbol: str) -> bool:
        """
        Check whether *symbol* is a valid Binance trading pair.
        Uses the public /api/v3/exchangeInfo endpoint.
        """
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
                resp = await client.get(
                    _EXCHANGE_INFO_ENDPOINT,
                    params={"symbol": symbol.upper()},
                )
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def _get_with_retry(
        client:   httpx.AsyncClient,
        endpoint: str,
        params:   dict,
    ) -> list:
        """
        HTTP GET with exponential backoff retry.

        Retries on:
          • 429 Too Many Requests (Binance rate limit)
          • 5xx server errors
          • Network / connection errors
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.get(endpoint, params=params)
                resp.raise_for_status()
                return resp.json()

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429 or (500 <= status < 600) or attempt < _MAX_RETRIES:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "Binance HTTP %d (attempt %d/%d) — retrying in %.1fs",
                        status, attempt, _MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

            except httpx.RequestError as exc:
                if attempt < _MAX_RETRIES:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "Network error (attempt %d/%d): %s — retrying in %.1fs",
                        attempt, _MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        return []