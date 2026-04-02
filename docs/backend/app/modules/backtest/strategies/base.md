# `app/modules/backtest/strategies/base.py`

## Module Overview
The `base.py` module establishes the core abstract interfaces defining all algorithmic behaviors (defining `BaseStrategy`). It implements robust design constraints guaranteeing vectors generating algorithms perform reliably without polluting system architectures with ad-hoc signal outputs.

## Functionalities
- **Constants Definitions**: Defines foundational signal identifiers cleanly assigning values (`SIGNAL_BUY = 1`, `SIGNAL_SELL = -1`, `SIGNAL_HOLD = 0`).
- **`BaseStrategy` Interface**: Python abstract base class enforcing implementations mapping strict configuration routines initializing securely properties accurately via internal `_validate_config()`.
- **`generate_signals(df)`**: The abstract vectorization contract governing historical backtests natively asserting that generated algorithms inherently return structured Pandas Dataframes annotated safely with explicit integer columns avoiding algorithmic look-ahead biases completely.
- **`evaluate_tick(tick, position)`**: Distinct architectural implementations mapping pure event-based single-tick environments explicitly mimicking production Bot limits natively operating independently resolving discrete operational state transitions tracking internal history logic.

## Dependencies & OSS
- **Python `abc`**: Core abstract properties mapping required constraints logically checking class implementations exactly.
- **Pandas**: Assumes input properties scaling vector executions properly accurately tracking array logic implicitly safely properly securely successfully.

## Correlations
Every strategy relies explicitly structurally off this parent guaranteeing `engine.py` interactions scale unconditionally avoiding bespoke interfaces resolving executions safely accurately checking minimum configurations seamlessly.

## Execution Flow
1. Custom strategy instantiations invoke `.super()` mapping configurations dynamically validating bounds directly targeting custom exceptions natively.
2. Downstream invocations explicitly call specific overridden abstract configurations generating vectors or event loops mapping cleanly outputs natively identically accurately matching.
