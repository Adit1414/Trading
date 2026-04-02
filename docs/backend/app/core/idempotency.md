# `app/core/idempotency.py`

## Module Overview
The `idempotency.py` module defines a critical FastAPI dependency ensuring mutating endpoints can be automatically retried safely over unstable networks. Using an `Idempotency-Key` tracking system stored in Redis, repeated identical client requests yield identically cached HTTP responses.

## Functionalities
- **`IdempotencyContext`**: A Python dataclass instantiated within FastAPI endpoint scope giving application developers a `store(body: dict, status_code: int)` callback functionality. Calls serialize request responses towards Redis ensuring later intercept validations execute perfectly.
- **`idempotency_dep`**: The primary dependency interceptor reading valid `UUID v4` keys sourced under the HTTP `Idempotency-Key` headers. When Redis detects keys matching incoming routes, it throws a localized `_CachedResponse` halting native route progress entirely, replaying cache outputs cleanly.
- **Graceful Degradation Mechanisms**: Should the Redis instance not exist locally (`settings.REDIS_URL` unavailable), it gracefully steps backwards functioning identically to generic no-idempotency requests, avoiding blocking local test executions.

## Dependencies & OSS
- **FastAPI**: Injects the workflow automatically mapping generic exception handlers stopping internal operations appropriately.
- **Redis.asyncio (aioredis)**: Supports backend operations writing JSON stringified bytes alongside TTL allocations handling idempotency lifetimes smoothly.
- **Python `re` (Regex)**: Leverages robust `_UUID_RE` patterns parsing out strictly compatible keys. 

## Correlations
Injected into `/bots` creations requests heavily protecting state modifications natively (like placing API configurations that shouldn't insert identically repeatedly). 

## Execution Flow
1. API receives `POST` mapping requests bundled natively alongside custom UUIDv4 keys defining `Idempotency-Key`.
2. The dependency fires intercepting operations mapping Redis parameters checking against `<prefix>:<uuid_key>`.
3. If absent (a standard HTTP flow), the context generates seamlessly injecting towards actual Endpoint logic, later generating cache responses utilizing `.store()`.
4. If present structurally, a specialized Exception acts throwing logic handling instantly routing a customized Pydantic 200 Return mimicking cache payloads (distinguishing explicitly first runs 201 vs retries 200).
