# `app/schemas/backtest.py`

## Module Overview
The `backtest.py` schema module defines the complex validation and serialization contracts operating natively during standard simulation logic workflows. It ensures incoming requests securely map functional validation limits matching target backtesting parameter schemas avoiding simulation engine crashes completely.

## Functionalities
- **Enums Integration**: Categorizes structurally safe constants matching `ContractType`, `StrategyName`, `Interval`, and `CandleSource` definitions preventing hard-coded typos naturally validating inputs successfully.
- **Strategy Schema Implementations**: Creates rigid validation forms mapping variables targeting individual distinct algorithms (like `MACDSignalParams`, `EMACrossoverParams`). Integrates native ranges using `ge` / `le` boundaries avoiding out-of-scale calculations completely.
- **`BacktestRunRequest`**: Models absolute execution bounds tracking target payloads identifying market constraints (slippage, initial cash equivalents, etc.) natively confirming validation operations (`start_date` before `end_date`).
- **Response Models**: Packs operational return properties cleanly isolating `BacktestRunResponse`, `BacktestStatistics`, and mapped output outputs tracking comprehensive arrays safely.

## Dependencies & OSS
- **Pydantic**: The core engine driving property translation validation. Maps standard configurations securely leveraging definitions mapping payloads dynamically matching REST constraints explicitly.

## Correlations
Operates as the primary validation gateway strictly utilized inside `/backtest/run` payload routing. Automatically injects validations supporting Swagger/OpenAPI structures natively building documentation and providing rigid runtime environments explicitly defined by engine capacities natively. 

## Execution Flow
1. Incoming API requests transmit JSON payload definitions.
2. Under FastAPI endpoint handling, Pydantic immediately asserts validations checking structure typing. 
3. `@model_validator` custom properties assert deeper relationship constraints natively (preventing fast periods scaling beyond logically calculated slow bounds explicitly).
4. Errors generate instantaneous HTTP 422 triggers seamlessly preventing invalid engine state invocations inherently.
