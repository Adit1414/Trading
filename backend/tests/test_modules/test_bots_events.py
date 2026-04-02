import pytest
import json
from app.modules.bots.events import make_event, channel_name, HEARTBEAT

def test_channel_name():
    assert channel_name("user-123") == "sse:user:user-123"

def test_make_event():
    event_str = make_event("SUCCESS", "Bot started", "bot-id")
    event = json.loads(event_str)
    assert event["type"] == "SUCCESS"
    assert event["message"] == "Bot started"
    assert event["bot_id"] == "bot-id"

def test_heartbeat_is_valid():
    assert "HEARTBEAT" in HEARTBEAT
