"""
app/modules/bots/events.py
────────────────────────────
Redis Pub/Sub channel naming and JSON event helpers for bot telemetry.

Channel contract
────────────────
  channel:user_{user_id}:events  — per-user channel (when auth is live)
  channel:global:events          — fallback when no user_id is present (pre-auth)

Event envelope (what the frontend receives via SSE)
────────────────────────────────────────────────────
{
  "type":    "SUCCESS" | "CIRCUIT_BREAKER" | "HEARTBEAT" | "ERROR",
  "bot_id":  "<uuid>",          # omitted for HEARTBEAT
  "message": "<human string>"
}
"""
from __future__ import annotations

import json
from typing import Any, Optional


def channel_name(user_id: Optional[str] = None) -> str:
    """Return the Redis pub/sub channel name for a given user (or global fallback)."""
    if user_id:
        return f"channel:user_{user_id}:events"
    return "channel:global:events"


def make_event(
    event_type: str,
    message: str,
    bot_id: Optional[str] = None,
    **extra: Any,
) -> str:
    """
    Serialise an event to the SSE wire format:
      data: {"type": "...", "message": "...", ...}\n\n
    """
    payload: dict[str, Any] = {"type": event_type, "message": message}
    if bot_id is not None:
        payload["bot_id"] = bot_id
    payload.update(extra)
    return f"data: {json.dumps(payload)}\n\n"


HEARTBEAT = make_event("HEARTBEAT", "ping")
