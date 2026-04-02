# `app/core/rate_limiter.py`

## Module Overview
The `rate_limiter.py` module restricts abuse against potentially demanding backend endpoints (like historical backtesting endpoints fetching huge JSON vectors), employing straightforward throttling measures based uniquely against individual usage patterns.

## Functionalities
- **`Limiter` Singleton**: An initialized singleton natively sourced spanning `slowapi` boundaries. It leverages customized remote identifying keys managing limits directly mapped behind proxy abstractions safely.
- **`BACKTEST_LIMIT` Constant**: An interpolated string defining explicit rates cleanly mapped against configuration boundaries natively setting parameters automatically derived off `# / minute` constants.

## Dependencies & OSS
- **SlowAPI**: Extends functionality around endpoint limits mapping specifically towards standard ASGI dependencies.

## Correlations
Operates closely towards routes managing computationally expensive paths (such as `api/v1/routes/backtest.py`), appending structural `@limiter.limit` decorators securely against execution threads.

## Execution Flow
1. Setup creates global initialized Limiter structures loading `key_func` abstractions mapping towards IP tracking dynamically (and later JWT claims mapping).
2. Incoming route accesses ping logic determining limit counters exceeding specific capacities.
3. Successful checks pass executing the route appropriately, exceeded blocks trigger standard ASGI 429 Too Many Request responses natively wrapping exception responses outward towards the edge APIs automatically.
