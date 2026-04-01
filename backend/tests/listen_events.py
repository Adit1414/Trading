# listen_events.py
import requests

def listen_to_sse():
    url = "http://localhost:8000/api/v1/bots/events"
    print(f"📡 Connecting to live stream at {url}...")
    
    try:
        # stream=True keeps the connection open
        with requests.get(url, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    # Decode from bytes to string and print
                    decoded_line = line.decode('utf-8')
                    print(f"📥 Received: {decoded_line}")
    except KeyboardInterrupt:
        print("\n🛑 Disconnected from stream.")

if __name__ == "__main__":
    listen_to_sse()