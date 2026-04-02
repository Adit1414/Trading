# `app/core/config.py`

## Module Overview
The `config.py` module centralizes all environment variables and internal settings for the application. It acts as a single source of truth for runtime configurations, ensuring that external parameters are uniformly accessed, validated, and cached throughout the application lifecycle.

## Functionalities
- **`Settings` (Pydantic BaseSettings)**: A comprehensive data class governing configurations. It handles loading `.env` properties, instantiating defaults, and converting string representations to appropriate data types.
- **Property Validations**: Includes custom Pydantic validators (e.g., `_parse_cors`) structurally verifying JSON string arrays loaded from environments for CORS validation.
- **`binance_history_base_url`**: A property method to dynamically switch between mainnet and testnet API routes.
- **`get_settings()`**: A caching singleton function enforcing `@lru_cache`, ensuring that traversing settings configuration repeatedly poses almost 0 runtime impact.

## Dependencies & OSS
- **Pydantic & Pydantic-Settings**: For defining strongly-typed configuration settings and safely deserializing `.env` secrets into runtime variables.
- **FastAPI/Python Stdlib**: Uses builtin `functools.lru_cache` and standard `json`.

## Correlations
The `settings` instance is imported consistently across almost every codebase layer:
- **Core (`auth.py`)**: Fetches `SUPABASE_JWT_SECRET`.
- **Database (`session.py`)**: Fetches `DATABASE_URL`.
- **Bot Engine/Services**: Readies limits thread-pool allocations (`BACKTEST_THREAD_POOL_SIZE`) and K-line limits.
- **Main (`main.py`)**: Establishes API version strings, CORS boundaries, and environment execution modes.

## Execution Flow
1. Upon compilation/start, Python interprets `app/core/config.py`.
2. `get_settings()` is invoked explicitly to populate `settings`.
3. The `SettingsConfigDict` directs Pydantic to read local `.env` values locally. If matching fields are populated, it binds them; otherwise, default values are assigned.
4. Future references to `settings` return the pre-populated `lru_cache` instance, delivering typed objects globally without disk I/O.
