# Frontend to Backend Requirements Documentation

This document outlines the backend design requirements and API endpoints necessary to support the recently implemented **Settings Page** on the frontend.

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

