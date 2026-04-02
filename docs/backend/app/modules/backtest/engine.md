# `app/modules/backtest/engine.py`

## Module Overview
The `engine.py` orchestrator module functions as the core executor handling comprehensive backtesting algorithms. Moving heavily away from blocking synchronous processing, it offloads vector-based iterations seamlessly utilizing thread pooling structures natively accelerating historical tick analysis robustly mapped within specific FastAPI workflows explicitly wrapping execution inside error checking models mapping standard responses robustly.

## Functionalities
- **Thread Pool Executors**: Maintains `ThreadPoolExecutor` bindings (`settings.BACKTEST_THREAD_POOL_SIZE`) shifting CPU-intensive routines cleanly isolating event-loop interruptions directly preventing ASGI API stalls internally.
- **`run_backtest()`**: The primary workflow orchestrator sequentially validating requested limits loading components sequentially (`get_historical_data`, `<strategy>.generate_signals`, `simulate_trades`). Automatically bounds checks preventing out-of-scale intervals crashing array indices inherently.
- **Data Integrations (`_bars_to_dataframe`)**: Marshalls pure scalar models returned by providers actively formatting them against dense Pandas Dataframe operations supporting complex downstream computations accurately.
- **Report Synthesizing**: Generates comprehensive responses binding simulation data (`BacktestRunResponse`) storing final records outwards persisting execution traces properly.

## Dependencies & OSS
- **Pandas**: Manages dense vectors converting properties correctly natively supporting mathematical iteration easily mapping internal constraints safely.
- **AsyncIO (`loop.run_in_executor`)**: Allows explicit Thread context boundaries moving blocking operations gracefully preventing HTTP endpoint timeouts correctly.

## Correlations
Operates dynamically interfacing explicitly with `/api/v1/routes/backtest.py` functioning inherently as the primary executor pipeline driving execution metrics routing arrays dynamically integrating `chart.py` Plotly renderings explicitly persisting results outwards inside `crud` models systematically.

## Execution Flow
1. Orchestrator executes retrieving `get_historical_data()` safely formatting outputs.
2. Formatted records inject towards dynamically loaded strategies executing thread-pooled `.generate_signals()`.
3. Signals execute threaded `simulate_trades()` natively synthesizing metric outcomes executing `synthesize()`.
4. Plotly HTML generations spin inside backgrounds successfully mapping output variables securely.
5. Pydantic records bind everything wrapping API returns successfully flushing persistent CRUD sequences internally cleanly.
