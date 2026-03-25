"""
app/core/rate_limiter.py
─────────────────────────
Shared slowapi Limiter instance.

Per HLD §5.2:
  POST /api/v1/backtest/run → 10 req/min per user (key = user IP until
  Module 1 JWT middleware is wired in; then swap key_func to user identity).

Usage in routes:
    @router.post("/run")
    @limiter.limit(BACKTEST_LIMIT)
    async def run_backtest(request: Request, ...):
        ...

Integration note for Module 1 (Auth):
    Replace `_key_func` with a function that extracts the Supabase user ID
    from the JWT token once the auth middleware is in place.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Key function – swap this to JWT user ID once Module 1 is integrated.
_key_func = get_remote_address

limiter = Limiter(key_func=_key_func)

# Convenience string used in route decorators
BACKTEST_LIMIT = f"{settings.BACKTEST_RATE_LIMIT}/minute"