# Backend Database Module: `models.py`

## 1. Module Overview
The `models.py` module defines the absolute schema structure defining system logic tables across the postgreSQL database via SQLAlchemy ORM Mappings. It strictly governs database relationship enforcement and column typing natively matching Pydantic output constraints globally.

## 2. Functionalities
*   **Users (`UserModel`)**: Future integration structure bridging Module 1 mappings parsing UUID references securely managing relationship domains per user.
*   **Strategies (`StrategyModel`)**: A read-only lookup table dictating fixed trading strategies natively implemented dynamically rendering the JSON structure into UI config bounds.
*   **Backtests (`BacktestModel`)**: Bounding logic mapping isolated historical runs linking directly mapped executions into parsed dictionary outputs storing chart html rendering endpoints.
*   **Bots (`BotModel`)**: Live system engine executors mapped against active status conditions routing `daily_pnl_lower_limits` safely mapping circuit breaker actions explicitly.
*   **Bot States (`BotStateModel`)**: The dynamic 1:1 linked representation tracking live real-time values including current portfolio holds tracking active un-realized bounds dynamically updated via ticker actions natively.

## 3. Dependencies & OSS
*   **SQLAlchemy**: Mapped types `Mapped`, `mapped_column`, `String`, `JSON`, `DateTime` forming declarative structures globally integrating dynamic ORM.
*   **UUID**: Defines primary keys implicitly avoiding integer collision patterns mapping easily against frontend routing metrics.

## 4. Correlations
*   Foundational logic core. Referenced extensively across **`app/crud/*`** executing row mutations.
*   Directly matched against **`app/schemas/db.py`** defining output responses explicitly overriding complex lazy-loading metrics safely parsing relationships manually.

## 5. Execution Flow
1. Upon `app/main.py` initializing or `alembic` running, `Base.metadata` generates DDL rules mapping cleanly mapped schemas parsing database migrations iteratively safely upgrading system columns dynamically ensuring schema enforcement.
