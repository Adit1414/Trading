"""
app/core/config.py
──────────────────
Centralised settings loaded from environment variables / .env file.
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

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "Algo Kaisen"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # ── Binance ───────────────────────────────────────────────────────────────
    BINANCE_TESTNET_BASE_URL: str = "https://testnet.binance.vision"
    BINANCE_MAINNET_BASE_URL: str = "https://api.binance.com"
    BINANCE_USE_TESTNET_FOR_HISTORY: bool = False

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    BACKTEST_RATE_LIMIT: int = 10
    BACKTEST_RATE_LIMIT_WINDOW: int = 60

    # ── LRU Cache ─────────────────────────────────────────────────────────────
    HISTORICAL_CACHE_TTL: int = 3600
    HISTORICAL_CACHE_MAXSIZE: int = 256

    # ── Thread Pool ───────────────────────────────────────────────────────────
    BACKTEST_THREAD_POOL_SIZE: int = 4

    # ── Supabase / Auth ───────────────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # ── Database (async PostgreSQL / Supabase) ────────────────────────────────
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    # For Supabase: postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:5432/postgres
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _assemble_db_connection(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── Supabase Storage (for equity-curve files) ─────────────────────────────
    # Bucket name where heavy equity_curve arrays are stored as JSON
    STORAGE_BUCKET: str = "backtest-results"

    # ── CORS ──────────────────────────────────────────────────────────────────
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
        return (
            self.BINANCE_TESTNET_BASE_URL
            if self.BINANCE_USE_TESTNET_FOR_HISTORY
            else self.BINANCE_MAINNET_BASE_URL
        )

    @property
    def db_enabled(self) -> bool:
        """True when a DATABASE_URL is configured."""
        return bool(self.DATABASE_URL)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()