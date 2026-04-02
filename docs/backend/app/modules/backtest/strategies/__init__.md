# `app/modules/backtest/strategies/__init__.py`

## Module Overview
The `__init__.py` strategy module acts as the explicit central strategy registry. It cleanly exposes mapped dictionaries associating constant human-readable strategy definitions towards executing underlying Python class representations guaranteeing simple lookups across the system architecture.

## Functionalities
- **`STRATEGY_REGISTRY`**: A tightly coupled internal Python Dictionary mapping absolute explicit configuration properties targeting valid constants (like `"EMA_CROSSOVER"`) resolving towards class imports internally (`EMACrossoverStrategy`).
- **`get_strategy()`**: Global retrieval pipeline factory abstracting class instantiations fetching appropriate algorithmic properties cleanly validating missing lookups (raising `KeyError`) safely.
- **`list_strategies()`**: A dynamic UI metadata reflection tool iterating registered configurations surfacing dynamically minimum bar boundaries and descriptive payloads natively supporting frontend form constructions flawlessly.

## Dependencies & OSS
- native Python type hinting arrays (`typing`).

## Correlations
Acts globally as the entry gate providing initialized classes utilized concurrently inside `engine.py` processing signal outputs, and directly powering external GET routes providing available active strategy configurations towards the `API` layer effectively.

## Execution Flow
1. Interprets imports sequentially resolving algorithm inheritance graphs.
2. Prepares instances exposing `get_strategy()` resolving dictionary requests wrapping specific inputs instantiating algorithms mapping configs (`config`) directly.
