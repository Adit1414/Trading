# test_bots.py
import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1/bots"

def test_bot_deployment():
    # 1. Generate a single, unique ticket number for this test
    idem_key = str(uuid.uuid4())
    headers = {"Idempotency-Key": idem_key}
    
    payload = {
        "symbol": "BTC/USDT",
        "is_testnet": True,
        "strategy_id": "5fc1781c-9a24-4a6c-bb99-1a4d08faf3d9", # Will need a real UUID from your DB
        "parameters": {"fast_ema": 12, "slow_ema": 26},
        "name": "Test Script Bot"
    }

    print(f"🚀 ATTEMPT 1: Deploying bot with Key: {idem_key}")
    response1 = requests.post(BASE_URL, json=payload, headers=headers)
    print(f"Status: {response1.status_code}") # Should be 201 Created
    try:
        print(f"Response: {response1.json()}\n")
    except requests.exceptions.JSONDecodeError:
        print(f"Response (text): {response1.text}\n")
    
    print("🔁 ATTEMPT 2: Sending the EXACT SAME request...")
    response2 = requests.post(BASE_URL, json=payload, headers=headers)
    print(f"Status: {response2.status_code}") # Should be 200 OK (Cache Hit)
    print(f"Headers: X-Idempotency-Replayed = {response2.headers.get('X-Idempotency-Replayed')}")
    print("Notice how the database wasn't hit again!\n")

if __name__ == "__main__":
    # Note: Replace the strategy_id in the payload with an actual ID from your Supabase strategies table
    test_bot_deployment()