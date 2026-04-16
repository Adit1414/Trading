# Frontend to Backend Requirements Documentation

This document outlines the backend design requirements and API endpoints necessary to support the recently implemented **Settings Page** and **Live Trading Page** on the frontend.

## 1. Settings Page Requirements

The Settings page allows users to manage their account, security, preferences, and trading defaults.

### 1.1 Profile Management
- **Data required:** Full Name, Phone Number, Timezone, Bio, Avatar URL.
- **Current Frontend Implementation:** Uses `supabase.auth.updateUser` to store data in the user's metadata JSON.
- **Backend Need:** 
  - Ensure Supabase auth triggers sync this metadata to a dedicated `users` or `profiles` table in the database for easier querying.
  - Endpoint to handle Avatar image upload to cloud storage (e.g., Supabase Storage) and update the profile URL.

### 1.2 Security & Sessions
- **Password Updates:** Currently relies on Supabase Auth.
- **Two-Factor Authentication (2FA):** 
  - **Backend Need:** Endpoints to generate 2FA QR codes (TOTP), verify the initial code, and enforce 2FA verification during login via Supabase.
- **Active Sessions Management:**
  - **Data needed:** Device type (Browser/OS), IP location, Last active time.
  - **Backend Need:** Session tracking. Endpoints to `GET /api/sessions/active` and `DELETE /api/sessions/revoke_all` (or revoke specific ID).

### 1.3 Notifications Preferences
- **Data Model Needed:** A configuration object for notification settings.
  - **Events:** `tradeExec`, `botAlert`, `pnl`, `news`, `system`
  - **Channels:** `email` (boolean), `push` (boolean)
  - **App sounds:** `soundAlerts` (boolean)
- **Backend Need:** `GET` and `PUT` endpoints for `/api/users/preferences/notifications`. Need integration with email (e.g. SendGrid/Resend) and Push Notification services.

### 1.4 Trading Preferences
- **Data Model Needed:** Global default settings applied to new bots and manual trades.
  - Fields: `defaultCapital`, `riskPerTrade` (%), `defaultLeverage`, `defaultExchange` (e.g., binance, bybit), `slippageTolerance` (%), `paperMode` (boolean), `autoStop` (boolean).
- **Backend Need:** `GET` and `PUT` endpoints for `/api/users/preferences/trading`. The backend execution engine must respect these defaults (especially `paperMode`) when processing order requests.

### 1.5 Account Management ("Danger Zone")
- **Export Data:** 
  - **Backend Need:** Endpoint `GET /api/users/export-data` that aggregates user profile, bots, trade history, and settings into a downloadable JSON/CSV payload.
- **Delete Account:** 
  - **Backend Need:** `DELETE /api/users/account`. Must perform a cascading deletion or pseudonymization of user data, shut down active bots, close active positions, and delete auth credentials.

---

## 2. Live Trading Page Requirements

The Live Trading page simulates a high-performance exchange interface. It requires low-latency data and robust transactional endpoints.

### 2.1 Live Market Data (Pub/Sub or WebSockets)
The frontend relies heavily on real-time streaming data.
- **Backend Need:** A WebSocket server (or high-frequency polling infrastructure) serving:
  - **Price Tickers:** Current price, 24h High/Low/Volume, 24h Change %.
  - **Candlestick/Chart Data:** Historical and live OHLCV data for multiple timeframes (1m, 5m, 1h, etc.) to feed the sparklines/charts.
  - **Order Book Depth:** Real-time stream of `asks` and `bids` (price, size, total) up to N levels.
  - **Recent Public Trades:** Stream of recent trades executed on the exchange (price, size, time, side).

### 2.2 Wallet & Balances
- **Backend Need:** Endpoint `GET /api/wallet/balances` fetching real and paper trading balances for various assets (USDT, BTC, ETH, SOL, etc.). Must update via WebSocket when a trade executes to instantly reflect new available purchasing power.

### 2.3 Order Execution Engine
- **Endpoint Structure:** `POST /api/orders`
- **Payload fields:** `pair` (e.g., BTC/USDT), `side` (BUY/SELL), `type` (MARKET/LIMIT/STOP), `size`/`amount`, `limit_price` / `stop_price`, `execution_mode` (Live/Paper).
- **Backend Need:**
  - Route paper trades to a simulated matching engine.
  - Route live trades to actual exchange APIs (Binance, ByBit) using the user's stored API keys.
  - Handle order validation (insufficient funds, invalid increments).

### 2.4 Managing State: Positions, Orders, and History
- **Open Positions:**
  - **Backend Need:** `GET /api/positions` returning active margin/futures positions (`id`, `pair`, `side`, `size`, `entry_price`, `liquidation_price`, `unrealized_pnl`).
  - **Endpoint:** `POST /api/positions/{id}/close` (to market close the position).
- **Open Orders:**
  - **Backend Need:** `GET /api/orders?status=open` returning unfilled Limit and Stop orders.
  - **Endpoint:** `DELETE /api/orders/{id}` to cancel.
- **Trade History:**
  - **Backend Need:** `GET /api/trades/history` returning paginated, fully executed historical trades (including P&L).

### 2.5 Real-time Account Updates (WebSockets)
Just like market data, user-specific data must be pushed via a private WebSocket channel:
- Push notifications when an open Limit order is filled.
- Live updates to Unrealized P&L for open positions as market prices tick.
- Push layout alerts (e.g., Liquidation warnings or Margin Calls).
