# `app/modules/backtest/data_cache.py`

## Module Overview
The `data_cache.py` module constructs an integral Historical Data Cacher preventing arbitrary endpoint spamming against upstream market providers (e.g. Binance API). It maintains localized `TTL` rules mapping strict historical windows supporting identically repeated backtests flawlessly by utilizing in-memory structures safely without requiring complex downstream database storage for tick data.

## Functionalities
- **`TTLCache`**: Shared `cachetools` instance establishing maximum sizes tracking entries resolving expired items dynamically based against configured metrics (`settings.HISTORICAL_CACHE_MAXSIZE`).
- **`_make_cache_key()`**: A pure hashing mechanism transforming structured metadata boundaries (`market`, `symbol`, `interval`, `start_date`, `end_date`) explicitly converting parameters returning unified reproducible MD5 hashed keys securely mapping parameters uniquely.
- **`get_historical_data()`**: The primary asynchronous fetching interface shielding direct upstream provider logic (`fetch_klines`) locking concurrent threads explicitly ensuring parallel execution attempts matching identical queries uniquely bounce off caches sequentially preventing redundant fetching directly.

## Dependencies & OSS
- **Cachetools**: Instantiates reliable standard `TTLCache` architectures.
- **Asyncio**: Implements threaded data structures (`asyncio.Lock()`) avoiding race conditions securely fetching upstream JSON requests.

## Correlations
Operates supporting the central orchestrator (`engine.py`) heavily handling initial dataset ingestion sequences reliably limiting excessive REST hits seamlessly translating inputs outwards reliably.

## Execution Flow
1. Fetch request identifies target dates checking internal dictionaries resolving explicit keys mappings. 
2. A context `async with _cache_lock` asserts validation checking present cache mappings instantly. If keys sit actively, instant returns prevent API overheads natively.
3. Cache misses immediately fetch upstream API requests returning valid arrays structurally mapping downstream cache dictionary mapping returning successfully.
