# `app/core/auth.py`

## Module Overview
The `auth.py` module serves as the authentication and authorization layer for the backend application. It implements a FastAPI dependency that verifies JSON Web Tokens (JWTs) issued by Supabase. This allows the backend to securely authenticate user requests without maintaining a separate credential store.

## Functionalities
- **`_jwt_secret()`**: A centralized helper function that securely retrieves the required `SUPABASE_JWT_SECRET` from environment configuration. It acts as a safety mechanism, raising an HTTP 503 error if the secret is unconfigured to prevent failing open.
- **`decode_token(token: str) -> str`**: Validates a provided token using PyrJWT against the Supabase secret. It natively handles token expiration and malformed structures, returning the `sub` claim which equates to the user's UUID.
- **`get_current_user(...)`**: An asynchronous FastAPI dependency designed to automatically parse the `Authorization` header, extract the Bearer token, and validate it using `decode_token`. It raises proper `HTTP 401 Unauthorized` errors when credentials are missing or invalid.

## Dependencies & OSS
- **FastAPI**: Used for its robust dependency injection system (`Depends`, `HTTPException`) and security utilities (`HTTPBearer`).
- **PyJWT**: Employed to parse, decode, and handle cryptographic validation of JWTs.

## Correlations
This module is a critical dependency used across protected API routes (e.g., in `api/v1/routes/...`). Other parts of the application inject `get_current_user` directly into their route definitions, effectively bridging Supabase front-end login actions with secure down-stream interactions (like bot generation or trading operations) mapped to that exact user UUID.

## Execution Flow
1. A client initiates an HTTP request with an `Authorization: Bearer <token>` header.
2. FastAPI triggers the `get_current_user` dependency automatically.
3. The dependency extracts the raw token from the header.
4. `decode_token` is invoked, which loads the configured JWT hash secret via `_jwt_secret()`.
5. The token's signature, structure, and expiration are verified using `PyJWT`.
6. Upon successful validation, the user UUID (from the `sub` claim) is extracted and passed to the caller route. If it fails, an HTTP 401 response rapidly terminates the request.
