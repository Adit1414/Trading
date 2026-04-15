# Technical Report: Paper Trading Implementation Requirement

**To**: Backend Development Team  
**From**: Frontend Integration Team  
**Subject**: Specification for Paper Trading Lab Backend Support  

---

## 1. Executive Summary
The frontend has implemented a comprehensive **Paper Trading Lab** UI. To make this functional, the backend needs to transition from a simple `is_testnet` flag to a robust **Virtual Simulation Engine**. This report outlines the necessary data models, API endpoints, and logic requirements to support risk-free algorithmic simulation.

## 2. Current State Assessment
*   **Bots**: `BotModel` has an `environment` flag (`MAINNET` | `TESTNET`).
*   **Trades**: `TradeLogModel` records trades with an `environment` flag.
*   **Gap**: There is no persistence for **Virtual USDT Balance**. The UI currently mocks a $100,000.00 balance.
*   **Gap**: Starting a "Paper Bot" currently depends on having Testnet API keys. A true "Paper Mode" should allow simulation using live price feeds without requiring external Testnet credentials.

## 3. Proposed Backend Enhancements

### 3.1 Data Model Updates

#### New Table: `virtual_wallets`
Tracks the simulated funds available for the Paper Trading Lab.
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key |
| `user_id` | UUID | FK to `users.id` |
| `balance` | Numeric(20,8)| Current virtual USDT balance (Default: 100,000.00) |
| `currency` | String | Default 'USDT' |
| `updated_at`| Timestamp | |

#### Update: `bots` / `bot_state`
Include a new environment type: `SIMULATION`.
*   `MAINNET`: Real money, real exchange.
*   `TESTNET`: Testnet money, testnet exchange (requires keys).
*   **`SIMULATION` (New)**: Virtual money, internal ledger, live price feed (no keys needed).

### 3.2 Necessary API Endpoints

#### Wallet Management
*   `GET /api/v1/paper/balance`: Returns the user's current virtual balance.
*   `POST /api/v1/paper/reset`: Resets the virtual balance to the default ($100k) and clears active simulations.

#### Simulation Control
*   `GET /api/v1/paper/bots`: Returns only bots running in `SIMULATION` environment.
*   `POST /api/v1/paper/deploy`: Specialized endpoint to launch a simulation bot (pre-configures `environment="SIMULATION"`).

#### Trade Ledger
*   `GET /api/v1/paper/trades`: Returns trade history specifically for simulated trades.

### 3.3 Core Logic Requirements

1.  **Virtual Order Matching**: The backend `engine` must detect `SIMULATION` bots and "fill" orders locally based on the latest symbol price instead of sending orders to an exchange API.
2.  **Slippage & Commission Simulation**: To provide a realistic lab experience, the virtual match logic should apply configurable slippage and a simulated commission (e.g., 0.1%).
3.  **Balance Atomicity**: Buying in simulation should deduct from `virtual_wallets.balance`. Selling should add to it. These must be transactionally safe.

## 4. Frontend Integration Requirements
The `PaperTradingPage.jsx` currently expects the following data shapes (to be matched by backend schemas):

*   **KPIs**: Shared virtual balance, 24h PnL sum of paper bots, count of active paper bots.
*   **Active Bots**: List of bots with `pair`, `strategy`, `pnl`, `uptime`.
*   **Ledger**: List of trades with `pair`, `side`, `price`, `size`, `pnl`.

## 5. Next Steps
1.  **Database Migration**: Create the `virtual_wallets` table.
2.  **Engine Extension**: Implement a "Local Executor" in `app.modules.bots.engine` that handles `SIMULATION` orders.
3.  **API Implementation**: Build the `/paper/*` route group.

---
**Status**: Pending Backend Review  
**Priority**: High (Enables core product value proposition)
