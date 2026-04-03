# Backend Core Module: `auth.py`

## 1. Module Overview
The `auth.py` file is responsible for handling FastAPIs JSON Web Token (JWT) authentication middleware logic using Supabase-issued tokens. It provides route dependencies to protect endpoints and ensures execution blocking parameters are valid for endpoints expecting authenticated requests. It verifies symmetric HS256 signatures derived from the global Supabase project secret.

## 2. Functionalities
*   `_jwt_secret()`: Attempts to securely load the `SUPABASE_JWT_SECRET` from system parameters, failing eagerly with an HTTP 503 if unconfigured.
*   `decode_token(token: str)`: Safely parses and decrypts a raw JSON token using PyJWT, validating expiration and structural invariants, while skipping strict signature verifications against ES256 to allow backwards compatibility gracefully. It expects to intercept a `sub` UUID claiming user identity.
*   `get_current_user(...)`: An explicit FastAPI Dependency wrapper designed to be injected into structural routing parameters (`Depends(get_current_user)`) that processes HTTP Bearer authorizations.

## 3. Dependencies & OSS
*   **PyJWT (`jwt`)**: Decodes and asserts expiration states of web tokens.
*   **FastAPI**: Inherits exceptions (`HTTPException`, `status`) and HTTP header definitions (`HTTPBearer`, `HTTPAuthorizationCredentials`, `Depends`, `Query`).

## 4. Correlations
*   Ties heavily into **`app/core/config.py`** to query `settings.SUPABASE_JWT_SECRET`.
*   Attached to endpoints in **`app/api/v1/routes/`** protecting mutating database actions (backtest runs, bot manipulations).
*   Integrates within **`app/api/v1/routes/bots.py`** for SSE (Server-Sent Event) handshakes parsing tokens through query parameters dynamically rather than static headers.

## 5. Execution Flow
1. An incoming client API request triggers the endpoint dependency `get_current_user()`.
2. The route extracts the `Bearer <token>` payload natively through FastAPI header parsing mechanism.
3. The raw token routes to `decode_token()`, fetching the environment configuration dynamically.
4. Tokens evaluated against expiration timestamps; failures emit HTTP 401 exceptions.
5. Success yields the returned `user_id` string injected directly into the parent router handling parameter logic.
