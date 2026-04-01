"""
app/core/config.py
──────────────────
Centralised settings loaded from environment variables / .env file.

Integration hooks for other modules:
  - Module 1 (Auth):    SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
  - Module 3 (Stream):  BINANCE_TESTNET_BASE_URL / BINANCE_MAINNET_BASE_URL
  - Module 4 (Bot):     DATABASE_URL (for state checkpointing)
  - Module 5 (Order):   reuses Binance URLs defined here
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Algo Kaisen"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # ── Binance ───────────────────────────────────────────────────────────────
    BINANCE_TESTNET_BASE_URL: str = "https://testnet.binance.vision"
    BINANCE_MAINNET_BASE_URL: str = "https://api.binance.com"
    # Testnet has limited K-line history; leave False to hit public mainnet endpoints.
    BINANCE_USE_TESTNET_FOR_HISTORY: bool = False

    # ── Rate Limiting (per HLD §5.2: 10 req/min for /backtest/run) ───────────
    BACKTEST_RATE_LIMIT: int = 10        # requests …
    BACKTEST_RATE_LIMIT_WINDOW: int = 60  # … per N seconds

    # ── LRU Cache for Historical Data ────────────────────────────────────────
    HISTORICAL_CACHE_TTL: int = 3600     # seconds
    HISTORICAL_CACHE_MAXSIZE: int = 256  # entries

    # ── Thread Pool (vectorised backtest off-loading per HLD §4.2) ───────────
    BACKTEST_THREAD_POOL_SIZE: int = 4

    # ── Supabase – Module 1 integration stub ─────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # ── Database – Module 4 integration stub ─────────────────────────────────
    DATABASE_URL: Optional[str] = None

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> List[str]:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v  # type: ignore[return-value]

    @property
    def binance_history_base_url(self) -> str:
        """Resolved Binance base URL for historical K-line fetching."""
        return (
            self.BINANCE_TESTNET_BASE_URL
            if self.BINANCE_USE_TESTNET_FOR_HISTORY
            else self.BINANCE_MAINNET_BASE_URL
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()