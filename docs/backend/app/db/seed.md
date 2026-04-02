# Backend Database Module: `seed.py`

## 1. Module Overview
The `seed.py` executable script implements safe bootstrapping parameters inserting default trading logic strategies directly into the system database avoiding hard-coded logic mapping logic endpoints cleanly rendering JSON configurations into frontend form inputs dynamically.

## 2. Functionalities
*   `seed_strategies(...)`: Idempotent asynchronous function asserting database entries mapping the baseline logic for `EMA_CROSSOVER`, `MACD_SIGNAL`, `RSI_DIVERGENCE`, and `BOLLINGER_BANDS`. Uses UPSERT conditions safely bypassing primary key collision violations gracefully enabling multiple execution triggers natively without failing constraint checks.

## 3. Dependencies & OSS
*   **SQLAlchemy (PostgreSQL dialect)**: Utilizes dynamic constraints executing native DB specific commands including `insert().on_conflict_do_update()` bounding constraint keys correctly asserting table integrity correctly handling conflicts natively.
*   **asyncio**: Exposes async execution primitives orchestrating linear logic handling the loop sequence directly if triggered as a standalone __main__ module natively.

## 4. Correlations
*   Maps metadata dynamically parsed inside **`app/modules/backtest/strategies/`** enforcing dictionary representations securely mapping execution properties linearly across databases natively.
*   Triggers via Makefile aliases mapping `make seed` resolving natively executing the python instance autonomously without FastAPI booting.

## 5. Execution Flow
1. Script boots defining internal logger patterns dynamically formatting the execution tree cleanly.
2. Synchronizes active async properties grabbing `get_db()` execution contexts manually generating transactions.
3. Maps raw parameters iterating `app/modules/backtest/strategies/list_strategies()`.
4. Loops execution sequences applying `insert` and `on_conflict_do_update` conditionally mapped parsing logic updates overwriting native metadata modifications seamlessly ensuring state remains in-sync safely terminating connections cleanly natively parsing loop completions.
