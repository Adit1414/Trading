from __future__ import annotations

import ccxt.async_support as ccxt

from app.core.security import decrypt_api_key


def get_binance_client(
    api_key: str,
    secret: str,
    sandbox: bool = False,
    encrypted: bool = True,
) -> ccxt.binance:
    resolved_api_key = decrypt_api_key(api_key) if encrypted else api_key
    resolved_secret = decrypt_api_key(secret) if encrypted else secret
    exchange = ccxt.binance(
        {
            "apiKey": resolved_api_key,
            "secret": resolved_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot", "adjustForTimeDifference": True},
        }
    )
    exchange.set_sandbox_mode(sandbox)
    return exchange
