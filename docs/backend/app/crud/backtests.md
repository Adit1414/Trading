# `app/crud/backtests.py`

## Module Overview
The `backtests.py` CRUD (Create, Read, Update, Delete) module functions as the intermediate query translation layer for the `BacktestModel`. It abstracts raw SQLAlchemy engine syntax wrapping `select`, `insert`, and `delete` calls into strongly-typed asynchronous utility functions used safely inside backend API endpoints.

## Functionalities
- **`create_backtest(...)`**: Constructs a new row inserting execution configurations (`parameters`), outcome arrays (`metrics`), and potential external payload pointers (`result_file_url` into Supabase). Operates synchronously inserting into existing uncommitted transactional flushes guaranteeing consistent states.
- **`get_backtest()`**: Retrieves singular execution results mapping directly to explicit primary keys UUID IDs. Returns `None` seamlessly preventing failure halts.
- **`list_backtests_for_user()` / `list_all_backtests()`**: Fetch multiple summarized reports managing sorting parameters natively (newest first). Paginates inherently leveraging limit boundaries safeguarding DB loads.
- **`delete_backtest()`**: Modifies existing database states scrubbing target rows natively validating explicitly if acting ownership permissions map correctly against requests mitigating deletion abuse.

## Dependencies & OSS
- **SQLAlchemy (ext.asyncio)**: Utilizes native ORM constructs bridging definitions directly mapped off `app.db.models.BacktestModel`.

## Correlations
Operates synchronously supporting `api/v1/routes/backtest_db.py`, executing queries generated actively mapping user interface lists detailing historical configurations explicitly queried inside listing requests or creation events dynamically triggered by complete backtester executions.

## Execution Flow
1. Receives dependency validated `AsyncSession` allocations generated through standard FastAPI endpoints natively injecting contexts.
2. Formats explicit parameters converting variables perfectly matching the `BacktestModel` definitions preventing structural errors (e.g. converting `symbol.upper()`).
3. Executes async queries waiting until native DB resolution concludes translating outputs dynamically backwards unpacking items matching Python representations safely.
