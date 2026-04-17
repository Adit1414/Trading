from __future__ import annotations

import ccxt.async_support as ccxt


def get_binance_client(api_key: str, secret: str, sandbox: bool = False) -> ccxt.binance:
    exchange = ccxt.binance(
        {
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot", "adjustForTimeDifference": True},
        }
    )
    exchange.set_sandbox_mode(sandbox)
    return exchange
