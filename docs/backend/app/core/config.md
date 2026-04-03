# Backend Core Module: `config.py`

## 1. Module Overview
The `config.py` module establishes a centralized source of truth for repository application configurations, environment variables, and system parameters utilizing Pydantic constraints. It guarantees type-safe mapping preventing misconfigured boot-ups regarding external services API integrations (Binance, Supabase, Redis).

## 2. Functionalities
*   `Settings(BaseSettings)`: Main configuration class encompassing properties spanning multiple system domains:
    *   **App Logic**: Application tagging, nested API routing bases, debug flags.
    *   **Binance Logic**: Endpoint definitions spanning testnets versus main public webs. Overridden selectively via `BINANCE_USE_TESTNET_FOR_HISTORY`.
    *   **System Overload / Threading**: Specifies rate limiting windows (10 metrics per 60 secs) and defines concurrent pool capacities (`BACKTEST_THREAD_POOL_SIZE = 4`).
    *   **Market History Data**: LRU Cache bounding limits explicitly capping dictionary saturation.
    *   **Storage Drivers**: Interception variables for Redis URL and SQL connection links.
    *   **CORS**: Automatically parses arbitrary origin overrides directly intercepting explicit pre-flight domains for localhost react-clients.
*   `get_settings()`: Provides a structural cached singleton instantiating settings once locally per app lifespan.

## 3. Dependencies & OSS
*   **Pydantic / Pydantic Settings**: Manages environment mapping schema evaluations recursively.

## 4. Correlations
*   Universally accessed across all root applications and modules.
*   **`app/core/rate_limiter.py`**: Reads `BACKTEST_RATE_LIMIT`.
*   **`app/services/market_data/binance.py`**: Resolves endpoint allocations from derived properties.
*   **`app/main.py`**: Bootstraps app titles, lifecycle scopes, and custom middleware definitions using configurations defined.

## 5. Execution Flow
1. Process triggers import statement requesting `settings` properties globally.
2. `get_settings()` resolves via an `lru_cache`, evaluating local disk properties via un-committed `.env` overrides mapping natively mapped `SettingsConfigDict` rules.
3. If arrays or logic overrides dictate specific bounds (CORS properties via JSON decoding), decorators parse logic directly prior to field persistence.
4. Returns strongly typed instances safely injected downstream.
