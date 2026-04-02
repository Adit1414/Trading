# `app/db/models.py`

## Module Overview
The `models.py` module is the foundation for the relational database schema within the application. Using standard SQLAlchemy ORM notation, it maps native Python classes to PostgreSQL table layouts defining columns, relationship bindings, foreign-key constraints, and cascade logic.

## Functionalities
- **`UserModel` (`users`)**: Represents authenticated operators interacting within the software ecosystem. It functions predominantly to associate trading features strictly to specific users.
- **`ApiCredentialModel` (`api_credentials`)**: Protects automated integration points by acting as a pointer strictly towards a heavily-managed Supabase Vault.
- **`StrategyModel` (`strategies`)**: Seeded records retaining metadata defining parameters (in `JSONB`) governing structural validation constraints applied to strategy executions and UI rendering forms.
- **`BotModel` (`bots`) & `BotStateModel` (`bot_state`)**: Details active strategies, maintaining a strict 1-to-1 relationship between persistent configuration and dynamic trading properties (like positional awareness and P&L limits).
- **`TradeLogModel` (`trade_logs`)**: Central ledger of individual executed trades.
- **`BacktestModel` (`backtests`)**: Catalogs historical backtesting requests incorporating metric JSON definitions and result files targeting Supabase Storage.

## Dependencies & OSS
- **SQLAlchemy (Async)**: Core architectural toolkit utilized for ORM representation, including column types (like `JSONB`, `UUID`, `TIMESTAMP`), foreign keystones, constraints, and cascading triggers.

## Correlations
Models are heavily utilized within `crud/` repository utilities and dynamically injected within `db/session.py` interactions. It essentially establishes the data contracts required for backend API persistence operations when parsing values back into endpoint endpoints conforming with schema (`schemas/db.py`) translations.

## Execution Flow
1. This module is purely declarative—when the ASGI application launches, an external system (such as Alembic or Supabase Edge definitions) synchronizes the engine tables with this specified format.
2. Through session contexts querying data mappings inside Crud instances, properties from these exact definitions are queried and natively unwrapped directly to associated Python `Mapped` variables.
